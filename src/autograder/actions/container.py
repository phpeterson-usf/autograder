"""
Container isolation for student code execution.

When enabled via [Container] in config.toml, every call routed through
cmd_exec runs inside a throwaway Docker container with no network, bounded
resources, and only the repo (rw), the project's tests dir (ro), and
Digital.jar (ro, for the Java image) bind-mounted in.
"""

import os
import subprocess

from .util import SafeConfig, fatal


class ContainerConfig(SafeConfig):
    def __init__(self, cfg):
        self.enabled = False
        self.engine = "docker"
        self.dockerfiles_path = ""  # blank = autodetect from package location
        self.safe_update(cfg)


class Container:
    """Per-repo container handle: builds the image on demand and wraps an
    argv list into a `docker run` invocation with the right mounts."""

    WORK_DIR = "/work"
    TESTS_DIR = "/tests"
    DIGITAL_PATH = "/opt/Digital.jar"

    def __init__(self, image, repo_path, project_tests_path, digital_path,
                 engine="docker", dockerfiles_path=""):
        self.image = image
        self.repo_path = os.path.abspath(repo_path)
        self.project_tests_path = os.path.abspath(project_tests_path)
        self.digital_path = os.path.abspath(digital_path) if digital_path else None
        self.engine = engine
        self.dockerfiles_path = self._resolve_dockerfiles_path(dockerfiles_path)
        self.tag = f"autograder-{image}:latest"
        self._built = False

    @staticmethod
    def _resolve_dockerfiles_path(configured):
        if configured:
            return os.path.expanduser(configured)
        # Walk up from this module's location looking for a sibling containers/ dir.
        # This works when running from a clone of the autograder repo.
        cur = os.path.dirname(os.path.abspath(__file__))
        while True:
            candidate = os.path.join(cur, "containers")
            if os.path.isdir(candidate):
                return candidate
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
        fatal("containers/ directory not found; set [Container] dockerfiles_path "
              "in config.toml to point at the autograder repo's containers/ dir")

    def _ensure_built(self):
        if self._built:
            return
        rc = subprocess.run(
            [self.engine, "image", "inspect", self.tag],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode
        if rc != 0:
            ctx = os.path.join(self.dockerfiles_path, self.image)
            if not os.path.isdir(ctx):
                fatal(f"No Dockerfile dir for image '{self.image}' at {ctx}")
            print(f"Building container image {self.tag} from {ctx} ...")
            rc = subprocess.run(
                [self.engine, "build", "-t", self.tag, ctx]
            ).returncode
            if rc != 0:
                fatal(f"Failed to build {self.tag}")
        self._built = True

    def _translate(self, s):
        # Replace host paths with their container-side equivalents.
        # Sort by host-path length descending so longer prefixes win.
        mappings = [
            (self.repo_path, self.WORK_DIR),
            (self.project_tests_path, self.TESTS_DIR),
        ]
        if self.digital_path:
            mappings.append((self.digital_path, self.DIGITAL_PATH))
        mappings.sort(key=lambda m: len(m[0]), reverse=True)
        for host, ctr in mappings:
            s = s.replace(host, ctr)
        return s

    def wrap(self, args):
        """Return the full `docker run ...` argv that executes `args` inside
        the container."""
        self._ensure_built()
        translated = [self._translate(a) for a in args]
        cmd = [
            self.engine, "run", "--rm", "--init",
            "--network=none",
            "--memory=512m", "--pids-limit=128", "--cpus=1",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "-v", f"{self.repo_path}:{self.WORK_DIR}",
            "-v", f"{self.project_tests_path}:{self.TESTS_DIR}:ro",
            "--workdir", self.WORK_DIR,
        ]
        if self.digital_path and os.path.exists(self.digital_path):
            cmd += ["-v", f"{self.digital_path}:{self.DIGITAL_PATH}:ro"]
        cmd += [self.tag, *translated]
        return cmd
