import os
from pathlib import Path

import pytest

from actions.config import Config, Args


def test_config_get_path_env_overrides(tmp_path, monkeypatch):
    cfgdir = tmp_path / "cfg"
    cfgdir.mkdir()
    monkeypatch.setenv("GRADE_CONFIG_DIR", str(cfgdir))
    p = Config.get_path()
    assert p == cfgdir / "config.toml"


def test_config_get_path_parent_traversal(tmp_path, monkeypatch):
    # Layout: tmp/a/b; place config.toml in a; chdir into b; it should find a/config.toml
    a = tmp_path / "a"
    b = a / "b"
    b.mkdir(parents=True)
    (a / "config.toml").write_text("# placeholder")
    monkeypatch.delenv("GRADE_CONFIG_DIR", raising=False)
    monkeypatch.chdir(b)
    p = Config.get_path()
    assert p == a / "config.toml"


def test_config_get_path_falls_back_home(tmp_path, monkeypatch):
    # If nothing in env and parents, falls back to ~/.config/grade/config.toml
    fake_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("GRADE_CONFIG_DIR", raising=False)
    # Ensure parent traversal stops at home
    wd = fake_home / "work/dir"
    wd.mkdir(parents=True)
    monkeypatch.chdir(wd)
    p = Config.get_path()
    assert p == fake_home / ".config/grade/config.toml"


def test_args_from_cmdline_defaults_project_from_cwd(tmp_path, monkeypatch):
    # Simulate: grade test with no -p; project derived from cwd name up to '-'
    d = tmp_path / "projx-someuser"
    d.mkdir()
    monkeypatch.chdir(d)
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")
    monkeypatch.setenv("TERM", "xterm")
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.setenv("LINES", "24")
    monkeypatch.setenv("PWD", str(d))
    monkeypatch.setenv("HOME", str(tmp_path))

    monkeypatch.setenv("PYTEST_RUNNING", "1")
    monkeypatch.setattr("sys.argv", ["grade", "test"])  # only action provided

    args = Args.from_cmdline()
    assert args.action == "test"
    assert args.project == "projx"
    assert args.verbose is False
    assert args.very_verbose is False


def test_args_parsing_flags_and_lists(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "grade",
            "class",
            "-p",
            "myproj",
            "-v",
            "-vv",
            "--github-action",
            "-n",
            "T01",
            "-s",
            "alice",
            "bob",
        ],
    )
    args = Args.from_cmdline()
    assert args.action == "class"
    assert args.project == "myproj"
    assert args.verbose is True
    assert args.very_verbose is True
    assert args.github_action is True
    assert args.test_name == "T01"
    assert args.students == ["alice", "bob"]

