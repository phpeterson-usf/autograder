# Containers (spec)

This directory contains the Dockerfiles that isolate student code execution when an instructor runs `grade class` (or any other action that builds or runs student code). This file is the design spec.

## Goal

Protect the instructor's machine from arbitrary code in student repositories. Three execution paths run student-authored content as the invoking user:

1. `make -C <repo>` — a `Makefile` is arbitrary shell, with full access to `~/.ssh`, `~/.config/grade/config.toml` (Canvas/GitHub tokens), and everything else under the user's home.
2. The built program (`./<project>`) — same blast radius.
3. `git clone` of the student repo — symlinks, `.gitattributes` filters, etc.

Containerizing these calls confines a malicious or accidentally destructive student program to a throwaway filesystem with no network and no access to host secrets.

## Design

All three dangerous calls funnel through one function: `cmd_exec` in `src/autograder/actions/cmd.py`. The container layer lives entirely inside `cmd_exec`. Callers in `test.py`, `git.py`, etc. do not change. The test TOML format does not change.

```
cmd_exec(args, wd=...)
    │
    ├── containers disabled → subprocess.Popen(args, cwd=wd)
    │
    └── containers enabled  → subprocess.Popen(
                                 ["docker", "run", ...flags..., image,
                                  *args_translated],
                                 cwd=None)
```

When containers are enabled, `wd` becomes a bind-mount and any host paths in `args` (e.g. `$project_tests/...`, `$digital`) are translated to their container-side equivalents.

## Modes

Containers are opt-in via user config, default disabled. This keeps two paths invisible to each other:

- **Student path**: a student runs `grade test` in their own repo. Containers disabled. No Docker required.
- **Instructor path**: an instructor runs `grade class` or `grade test` against a cloned student repo. Containers enabled. Student code never touches the host filesystem outside the bind-mounted repo.

Students do not install Docker, do not build images, and do not need to know containers exist.

## Configuration

User-level (in `~/.config/grade/config.toml`):

```toml
[Container]
enabled = false   # instructors set to true
engine = "docker" # "docker" | "podman" | "colima"; defaults to "docker"
```

Per-project (in the test TOML, alongside the `[project]` table):

```toml
[project]
container = "go"   # name of the image: "go" | "java" | "riscv"
```

When `Container.enabled = false`, the `container` field is ignored. When `Container.enabled = true` and a project has no `container` field, the autograder errors out rather than silently falling back to host execution — explicit is better than a surprising default when isolation is the whole point.

## Directory layout

```
containers/
├── README.md          (this file)
├── go/
│   └── Dockerfile
├── java/
│   └── Dockerfile
└── riscv/
    └── Dockerfile
```

Each stack is one directory containing a `Dockerfile` and any small helper files. Binary artifacts (Debian base images, QEMU binaries, `Digital.jar`) are not checked into the repo — they are pulled by `docker build` from upstream, or bind-mounted from the host at runtime.

## The three images

1. **`go`** — Debian-slim + Go toolchain + `make`. For courses that build Go programs.
2. **`java`** — Debian-slim + JRE + `make`. `Digital.jar` is not baked in (non-redistributable); the instructor's `~/Digital/Digital.jar` is bind-mounted read-only at runtime, using the `$digital` substitution in `test.py`.
3. **`riscv`** — built with `FROM --platform=linux/riscv64 debian:slim` and native `gcc`/`make` packages. Docker (via `binfmt_misc` + `qemu-user-static`, which both Docker Desktop and Colima provide on macOS) transparently emulates the RV64 binary on the host's native architecture. Test TOMLs invoke `./prog` — there is no `qemu-` prefix in the test format. Emulation does not leak out of the container.

## Image lifecycle

Build-on-first-use, no registry. When `cmd_exec` is asked to run inside image `X`, it checks (`docker image inspect`) whether the tagged image exists locally; if not, it runs `docker build containers/X/`. Subsequent runs hit the local cache.

Rationale: the user base is small (course instructors); a registry adds ops (namespace ownership, push permissions, update cadence) for marginal gain.

## Bind mounts

Per `docker run` invocation:

| Host path                           | Container path     | Mode | Purpose                          |
|-------------------------------------|--------------------|------|----------------------------------|
| `<repo_path>`                       | `/work`            | rw   | `make` writes object files here  |
| `<tests_path>/<project>`            | `/tests`           | ro   | `$project_tests` resolves here   |
| `~/Digital/Digital.jar` (java only) | `/opt/Digital.jar` | ro   | `$digital` resolves here         |

Working directory inside the container is `/work`. `$project_tests`, `$project`, and `$digital` substitutions in the test TOML resolve to host paths; the container layer rewrites them to their `/work`, `/tests`, and `/opt/Digital.jar` equivalents at exec time.

Nothing under the instructor's `~` is mounted other than the explicit paths above.

## Runtime policy

Every `docker run` includes:

- `--rm` — fresh container per command; no cross-student state.
- `--network=none` — no test case requires network. Closes outbound exfiltration.
- `--init` — proper PID 1 so SIGTERM on timeout propagates cleanly.
- `--memory=512m --pids=128 --cpus=1` — caps fork bombs and runaway memory. Tunable per project via future `[project]` fields if a course needs more.
- `--read-only` on `/`, with `/work` writable via the bind-mount. Student `make` writes object files into `/work` (visible on host); nothing else on disk persists.

## Non-goals

- **No published images.** Dockerfiles are the source of truth; images are built locally.
- **No GUI applications.** Digital is invoked headlessly (`java -cp Digital.jar CLI ...`); no Xvfb in any image.
- **No remote execution on hardware.** RISC-V grading uses QEMU emulation in a container on the instructor's laptop, not the BeagleV-Ahead boards.
- **No isolation guarantees against a determined attacker.** Container escape vulnerabilities exist; this design raises the cost of malicious student code from "trivial" to "non-trivial," which is the practical bar for a course-grading workflow.
