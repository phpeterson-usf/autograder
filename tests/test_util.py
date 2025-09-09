import io
import pathlib
import sys
import textwrap
import types
import pytest

from autograder.actions import util as U


def test_project_from_cwd_parses_with_suffix(tmp_path):
    d = tmp_path / "project1-someuser"
    d.mkdir()
    assert U.project_from_cwd(d) == "project1"


def test_project_from_cwd_parses_without_suffix(tmp_path):
    d = tmp_path / "project1"
    d.mkdir()
    assert U.project_from_cwd(d) == "project1"


def test_load_toml_file_not_found_returns_empty(tmp_path):
    p = tmp_path / "missing.toml"
    assert U.load_toml(p) == {}


def test_load_toml_parse_error_exits(tmp_path, monkeypatch):
    p = tmp_path / "bad.toml"
    p.write_text("not=valid=toml")
    with pytest.raises(SystemExit):
        U.load_toml(p)


def test_format_pass_fail_alignment_and_failed():
    r = {"test": "01", "rubric": 5, "score": 5}
    s = U.format_pass_fail(r)
    assert s.startswith("01(5/5)")
    assert not U.failed(r)

    r2 = {"test": "01", "rubric": 5, "score": 0}
    assert U.failed(r2)


def test_safeconfig_unknown_key_exits(monkeypatch):
    class C(U.SafeConfig):
        def __init__(self, cfg):
            self.a = 1
            self.safe_update(cfg)

    with pytest.raises(SystemExit):
        C({"a": 2, "b": 3})

