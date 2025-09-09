import os
import sys
import types
import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    # Block requests.get/put by default to keep tests offline
    try:
        import requests
    except Exception:
        return

    def _block(*args, **kwargs):
        raise RuntimeError("Network access blocked in tests")

    monkeypatch.setattr(requests, "get", _block, raising=True)
    monkeypatch.setattr(requests, "put", _block, raising=True)


@pytest.fixture
def fake_cwd(tmp_path, monkeypatch):
    # Provide a temporary current working directory
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def import_util():
    # Helper to import actions.util fresh
    import importlib
    return importlib.import_module("actions.util")

