import json
from types import SimpleNamespace
from zipfile import ZipFile
from io import BytesIO

import pytest

from actions.git import Git, GitConfig, GitNoBranches, GitNoCommits
from actions.github import Github
from actions.server import Server


class DummyArgs(SimpleNamespace):
    pass


def test_git_make_remote_path_variants():
    cfg = GitConfig({'org': 'orgx', 'credentials': 'ssh'})
    g = Git(cfg.__dict__, DummyArgs(), None)
    class R: remote_path = 'p-s'
    assert g.make_remote_path(R) == 'git@github.com:orgx/p-s.git'

    cfg2 = GitConfig({'org': 'orgx', 'credentials': 'https'})
    g2 = Git(cfg2.__dict__, DummyArgs(), None)
    assert g2.make_remote_path(R) == 'https://github.com/orgx/p-s'


def test_git_get_default_branch_and_no_branches(monkeypatch, tmp_path):
    cfg = GitConfig({'org': 'o', 'credentials': 'ssh'})
    g = Git(cfg.__dict__, DummyArgs(), None)

    # Fake subprocess Popen pipeline
    class FakeProc:
        def __init__(self, data=b"main\n"):
            self._data = data
            self.stdout = BytesIO(self._data)

    def fake_popen(args, stdout=None, cwd=None, stdin=None):
        # First call returns branches, second returns cut; we emulate cut result directly
        if 'origin' in args:
            return FakeProc(b"  HEAD branch: main\n")
        return FakeProc(b"main\n")

    monkeypatch.setattr('subprocess.Popen', fake_popen)
    branch = g.get_default_branch(str(tmp_path))
    assert branch == 'main'

    # Return empty should raise
    def fake_empty(args, stdout=None, cwd=None, stdin=None):
        return FakeProc(b"")
    monkeypatch.setattr('subprocess.Popen', fake_empty)
    with pytest.raises(GitNoBranches):
        g.get_default_branch(str(tmp_path))


def test_git_get_commit_hash(monkeypatch, tmp_path):
    cfg = GitConfig({'org': 'o', 'credentials': 'ssh'})
    from actions.git import datetime
    args = DummyArgs()
    # Provide a date object with .date string and .suffix
    class D: date = '2024-10-01'; suffix = 'D1'
    g = Git(cfg.__dict__, args, D())

    def fake_capture(cmd, wd=None):
        return "commit abcdef0\n2024-09-30 14:00:00"

    monkeypatch.setattr('actions.git.cmd_exec_capture', fake_capture)
    h = g.get_commit_hash(str(tmp_path), 'main')
    assert h == 'abcdef0'

    def fake_empty(cmd, wd=None):
        return ""
    monkeypatch.setattr('actions.git.cmd_exec_capture', fake_empty)
    with pytest.raises(GitNoCommits):
        g.get_commit_hash(str(tmp_path), 'main')


def test_server_get_url_and_put_url(monkeypatch):
    # Simulate requests responses
    class Resp:
        def __init__(self, status=200, headers=None, text='{}', content=b''):
            self.status_code = status
            self._headers = headers or {'Content-Type': 'application/json'}
            self.text = text
            self.content = content
        @property
        def headers(self):
            return self._headers
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception('http error')

    def fake_get(url, headers=None):
        if url.endswith('/zip'):
            return Resp(200, {'Content-Type': 'application/zip'}, content=b'ZIP')
        return Resp(200, {'Content-Type': 'application/json'}, text=json.dumps({'ok': True}))

    def fake_put(url, data=None, headers=None):
        return Resp(200)

    import requests
    monkeypatch.setattr(requests, 'get', fake_get)
    monkeypatch.setattr(requests, 'put', fake_put)

    s = Server('api.example.com', 'token', verbose=False)
    assert s.make_url('path') == 'https://api.example.com/path'
    j = s.get_url('https://api.example.com/data', headers={})
    assert j['ok'] is True
    content = s.get_url('https://api.example.com/zip', headers={})
    assert content == b'ZIP'
    assert s.put_url('https://api.example.com/put', headers={}, data=b'1') is True


def test_github_artifacts_and_results(monkeypatch):
    # Craft an artifact listing and a zip containing grade-results.json
    artifacts = {
        'artifacts': [{
            'id': 1,
            'archive_download_url': 'https://api.github.com/a.zip',
            'workflow_run': {'id': 99}
        }]
    }

    jobs = {'jobs': [{'id': 101}]}

    # Zip with grade-results.json
    bio = BytesIO()
    with ZipFile(bio, 'w') as z:
        z.writestr('grade-results.json', json.dumps({'grade': '7'}))
    zip_bytes = bio.getvalue()

    def fake_get_url(url, headers=None):
        if url.endswith('/actions/artifacts'):
            return artifacts
        if url.endswith('/jobs'):
            return jobs
        if url.endswith('.zip') or url.endswith('a.zip'):
            return zip_bytes
        raise AssertionError(f"unexpected url {url}")

    # Patch Server.get_url for Github methods
    monkeypatch.setattr('actions.server.Server.get_url', lambda self, url, headers={}: fake_get_url(url, headers))

    from actions.github import GithubConfig
    args = DummyArgs(project='p', verbose=False)
    gh = Github(GithubConfig({'host_name':'api.github.com','access_token':'tok'}).__dict__, args, org='orgx')
    # First artifact
    art = gh.get_first_artifact_for_repo('alice')
    assert art['id'] == 1
    # Results extraction
    res = gh.get_artifact_results(art)
    assert res['grade'] == 7.0
    # Summary URL
    url = gh.get_action_run_summary_url('alice', art)
    assert 'actions/runs/99#summary-101' in url
