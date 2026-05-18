"""
Container isolation for student code execution.

When enabled via [Container] in config.toml, every call routed through
cmd_exec runs inside a Docker container with bounded resources and only
the repo (rw), the project's tests dir (ro), and Digital.jar (ro, for
the Java image) bind-mounted in.

One container is kept alive per repo: Test.test() calls start() before
the build / test cases and close() after them. Each cmd_exec call
inside that window goes through `docker exec`, which is ~100ms instead
of the 3-4s of a fresh `docker run`. The Go module cache, GOCACHE, and
any other build state survive across test cases within the same repo.
"""

import atexit
import os
import subprocess

from .util import SafeConfig, fatal


# Module-level registry of long-lived containers, so an interpreter exit
# (Ctrl-C, exception escape from Test.test) does not leak running
# containers. Each entry is (container_id, engine).
_active_containers = []


def _cleanup_active_containers():
    while _active_containers:
        cid, engine = _active_containers.pop()
        try:
            subprocess.run(
                [engine, "stop", "-t", "1", cid],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


atexit.register(_cleanup_active_containers)


class ContainerConfig(SafeConfig):
    def __init__(self, cfg):
        self.enabled = False
        self.engine = "docker"
        self.dockerfiles_path = ""  # blank = autodetect from package location
        self.network = False        # allow outbound network from the container
        self.safe_update(cfg)


class Container:
    """Per-repo container handle. Lifecycle:

        c = Container(...)
        c.start()                       # docker run -d ... sleep infinity
        argv = c.wrap(['make', '-C', repo_path])
        # → ['docker', 'exec', <id>, 'make', '-C', '/work']
        ...
        c.close()                       # docker stop <id>
    """

    WORK_DIR = "/work"
    TESTS_DIR = "/tests"
    DIGITAL_PATH = "/opt/Digital.jar"

    def __init__(self, image, repo_path, project_tests_path, digital_path,
                 engine="docker", dockerfiles_path="", network=False):
        self.image = image
        self.repo_path = os.path.abspath(repo_path)
        self.project_tests_path = os.path.abspath(project_tests_path)
        self.digital_path = os.path.abspath(digital_path) if digital_path else None
        self.engine = engine
        self.dockerfiles_path = self._resolve_dockerfiles_path(dockerfiles_path)
        self.network = network
        self.tag = f"autograder-{image}:latest"
        self._built = False
        self._container_id = None

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

    def start(self):
        """Start a long-lived container for this repo. Idempotent."""
        if self._container_id is not None:
            return
        self._ensure_built()
        cmd = [
            self.engine, "run", "-d", "--rm", "--init",
            "--memory=512m", "--pids-limit=128", "--cpus=1",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "-v", f"{self.repo_path}:{self.WORK_DIR}",
            "-v", f"{self.project_tests_path}:{self.TESTS_DIR}:ro",
            "--workdir", self.WORK_DIR,
        ]
        if not self.network:
            cmd += ["--network=none"]
        if self.digital_path and os.path.exists(self.digital_path):
            cmd += ["-v", f"{self.digital_path}:{self.DIGITAL_PATH}:ro"]
        cmd += [self.tag, "sleep", "infinity"]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            fatal(f"Failed to start container ({self.tag}): "
                  f"{result.stderr.strip()}")
        self._container_id = result.stdout.strip()
        _active_containers.append((self._container_id, self.engine))

    def close(self):
        """Stop the long-lived container. Idempotent. The --rm flag means
        docker removes it automatically once stopped."""
        if self._container_id is None:
            return
        cid = self._container_id
        self._container_id = None
        try:
            _active_containers.remove((cid, self.engine))
        except ValueError:
            pass
        subprocess.run(
            [self.engine, "stop", "-t", "1", cid],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def wrap(self, args):
        """Return a `docker exec ...` argv that runs `args` inside the
        already-started container, with host paths translated to their
        container-side equivalents."""
        if self._container_id is None:
            fatal("Container.wrap() called before start()")
        translated = [self._translate(a) for a in args]
        return [self.engine, "exec", self._container_id, *translated]
