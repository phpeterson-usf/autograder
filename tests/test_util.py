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


class _TypedConfig(U.SafeConfig):
    """Helper for the type-check tests below. Each field has a default
    chosen to exercise one of the comparisons inside _toml_types_compatible."""

    def __init__(self, cfg):
        self.s = "default"
        self.i = 1
        self.b = False
        self.lst = []
        self.nullable = None
        self.safe_update(cfg)


@pytest.mark.parametrize("key,value", [
    ("s", "other string"),
    ("i", 42),
    ("b", True),
    ("lst", [1, 2, 3]),
    ("nullable", "anything"),        # None default accepts any type
    ("nullable", 99),
    ("nullable", [1, 2]),
    ("nullable", True),
])
def test_safeconfig_compatible_types_accepted(key, value):
    cfg = _TypedConfig({key: value})
    assert getattr(cfg, key) == value


@pytest.mark.parametrize("key,value", [
    ("s", True),                     # bool for str (the user's actual bug)
    ("s", 1),                        # int for str
    ("s", []),                       # list for str
    ("i", True),                     # bool for int — strict separation
    ("i", "10"),                     # str for int
    ("b", 1),                        # int for bool — strict separation
    ("b", "true"),                   # str for bool
    ("lst", "not a list"),           # str for list
])
def test_safeconfig_mismatched_types_rejected(key, value):
    with pytest.raises(SystemExit):
        _TypedConfig({key: value})


def test_safeconfig_tomlkit_string_subclass_accepted():
    """tomlkit.items.String is a str subclass; isinstance check should
    accept it for a str-defaulted field."""
    import tomlkit
    doc = tomlkit.parse('s = "from-toml"\n')
    cfg = _TypedConfig({"s": doc["s"]})
    assert cfg.s == "from-toml"

