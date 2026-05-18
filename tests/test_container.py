"""Unit tests for the Container abstraction in actions/container.py.

These cover pure-Python logic — path translation and Dockerfile-platform
parsing — so they don't need a Docker daemon. Lifecycle methods (start,
close, wrap) that shell out to `docker` are not tested here; mocking the
subprocess layer adds brittleness without much value over manual smoke
testing against a real engine.
"""

import pytest

from autograder.actions.container import Container


def _make_container(tmp_path, image="go", repo_subdir="repo",
                    tests_subdir="tests", digital=False):
    """Construct a Container against a tmp_path layout. dockerfiles_path is
    set explicitly so Container does not walk the real filesystem looking
    for a containers/ sibling directory."""
    repo = tmp_path / repo_subdir
    repo.mkdir(parents=True, exist_ok=True)
    tests = tmp_path / tests_subdir
    tests.mkdir(parents=True, exist_ok=True)
    digital_path = None
    if digital:
        digital_path = str(tmp_path / "Digital.jar")
        (tmp_path / "Digital.jar").write_text("# placeholder")
    return Container(
        image=image,
        repo_path=str(repo),
        project_tests_path=str(tests),
        digital_path=digital_path,
        dockerfiles_path=str(tmp_path),
    )


# ---------- _translate ----------

def test_translate_repo_path_to_work(tmp_path):
    c = _make_container(tmp_path)
    assert c._translate(f"{c.repo_path}/main.go") == "/work/main.go"


def test_translate_tests_path_to_tests(tmp_path):
    c = _make_container(tmp_path)
    assert c._translate(f"{c.project_tests_path}/case01.txt") == "/tests/case01.txt"


def test_translate_digital_path_to_opt(tmp_path):
    c = _make_container(tmp_path, digital=True)
    assert c._translate(c.digital_path) == "/opt/Digital.jar"


def test_translate_relative_arg_passes_through(tmp_path):
    c = _make_container(tmp_path)
    assert c._translate("./prog") == "./prog"
    assert c._translate("arg1") == "arg1"


def test_translate_unrelated_absolute_arg_passes_through(tmp_path):
    c = _make_container(tmp_path)
    # A host path that is not under any of the mounted prefixes should not
    # be translated.
    assert c._translate("/usr/bin/env") == "/usr/bin/env"


def test_translate_longest_prefix_wins(tmp_path):
    """When project_tests_path is nested under repo_path, the longer
    prefix must be checked first so the inner mount label wins. Otherwise
    /repo/tests/x would be rewritten as /work/tests/x by the repo_path
    rule before the tests_path rule got a chance."""
    repo = tmp_path / "repo"
    repo.mkdir()
    tests = repo / "nested_tests"
    tests.mkdir()
    c = Container(
        image="go",
        repo_path=str(repo),
        project_tests_path=str(tests),
        digital_path=None,
        dockerfiles_path=str(tmp_path),
    )
    assert c._translate(f"{tests}/foo") == "/tests/foo"
    # And paths still under repo_path but outside tests_path still go to /work
    assert c._translate(f"{repo}/main.go") == "/work/main.go"


# ---------- _read_platform ----------

def _write_dockerfile(tmp_path, image, body):
    (tmp_path / image).mkdir()
    (tmp_path / image / "Dockerfile").write_text(body)


def test_read_platform_with_directive(tmp_path):
    _write_dockerfile(tmp_path, "riscv",
                      "FROM --platform=linux/riscv64 debian:trixie-slim\n"
                      "WORKDIR /work\n")
    c = _make_container(tmp_path, image="riscv")
    assert c._platform == "linux/riscv64"


def test_read_platform_without_directive(tmp_path):
    _write_dockerfile(tmp_path, "go",
                      "FROM debian:trixie-slim\n"
                      "WORKDIR /work\n")
    c = _make_container(tmp_path, image="go")
    assert c._platform is None


def test_read_platform_dockerfile_missing(tmp_path):
    # No <image>/Dockerfile exists at all. Container construction should
    # still succeed; platform is just None.
    c = _make_container(tmp_path, image="ghost")
    assert c._platform is None


def test_read_platform_only_first_from_matters(tmp_path):
    """A multi-stage Dockerfile may have several FROM lines. The parser
    should look only at the first one (it controls the runtime image)."""
    _write_dockerfile(tmp_path, "multi",
                      "FROM --platform=linux/amd64 builder:latest AS build\n"
                      "FROM --platform=linux/riscv64 debian:trixie-slim\n")
    c = _make_container(tmp_path, image="multi")
    assert c._platform == "linux/amd64"
