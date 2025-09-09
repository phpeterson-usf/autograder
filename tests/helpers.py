from pathlib import Path


def write_mini_repo(base: Path, program_name: str = "projx") -> Path:
    repo = base / "repo"
    repo.mkdir()
    # Simple POSIX shell script that echoes args or writes an output file
    prog = repo / program_name
    prog.write_text(
        """#!/bin/sh
set -eu
if [ "$#" -eq 0 ]; then
  echo ok
  exit 0
fi
if [ "$#" -eq 1 ]; then
  echo "$1"
  exit 0
fi
if [ "$#" -eq 2 ] && [ "$1" = "-o" ]; then
  printf "%s" "04out" > "$2"
  exit 0
fi
exit 0
"""
    )
    prog.chmod(0o755)

    # Minimal Makefile building a no-op
    (repo / "Makefile").write_text(
        """
all:
	@echo built
"""
    )

    return repo


def write_tests_repo(base: Path, project: str = "projx") -> Path:
    tests = base / "tests_repo" / project
    tests.mkdir(parents=True)
    (tests / f"{project}.toml").write_text(
        """
[project]
build = 'make'
strip_output = ''

[[tests]]
name = "01"
input = ["./$project"]
expected = "ok"
rubric = 2

[[tests]]
name = "02"
input = ["./$project", "hello"]
expected = "hello"
rubric = 3

[[tests]]
name = "04"
output = "04.txt"
input = ["./$project", "-o", "04.txt"]
expected = "04out"
rubric = 5
"""
    )
    return tests.parent
