from pathlib import Path
import os
import pytest

from autograder.actions.config import Args
from autograder.actions.test import Test, TestCase
from tests.helpers import write_mini_repo, write_tests_repo


def make_args(project: str):
    return Args({
        'action': 'test',
        'by_date': False,
        'exec_cmd': None,
        'github_action': False,
        'test_name': None,
        'project': project,
        'students': None,
        'verbose': False,
        'very_verbose': False,
    })


def test_test_runner_end_to_end(tmp_path, monkeypatch):
    project = "projx"
    repo = write_mini_repo(tmp_path, program_name=project)
    tests_repo = write_tests_repo(tmp_path, project=project)

    args = make_args(project)

    # Point Test to our synthetic tests repo
    from autograder.actions.test import TestConfig
    tcfg = TestConfig({'tests_path': str(tests_repo)})
    tester = Test(tcfg.__dict__, args)

    # Build should succeed and produce no error
    assert tester.build(repo) is None

    # Run tests; expect 2 + 3 + 5 = 10
    # Wrap repo-like object
    class Repo:
        def __init__(self, local_path, student=None):
            self.local_path = str(local_path)
            self.student = student

    result = tester.test(Repo(repo))
    assert result['score'] == 10
    assert len(result['results']) == 3
    assert tester.total_rubric() == 10


def test_build_invokes_make_with_wd_not_dash_C(tmp_path, monkeypatch):
    """Regression test: previously build() ran ['make', '-C', repo_path],
    which inside a container (workdir /work, /work bind-mounted from the
    abspath of repo_path) caused make to look for a non-existent
    subdirectory. The fix is to pass wd=repo_path and drop -C; this test
    pins that contract so it doesn't regress."""
    project = "projx"
    repo = write_mini_repo(tmp_path, program_name=project)
    tests_repo = write_tests_repo(tmp_path, project=project)

    args = make_args(project)

    from autograder.actions.test import TestConfig
    tcfg = TestConfig({'tests_path': str(tests_repo)})
    tester = Test(tcfg.__dict__, args)

    calls = []

    def fake_cmd_exec_rc(args, wd=None, **kwargs):
        calls.append((list(args), wd, kwargs))
        return 0

    monkeypatch.setattr(
        'autograder.actions.test.cmd_exec_rc', fake_cmd_exec_rc
    )

    assert tester.build(str(repo)) is None

    assert len(calls) == 1, f"expected exactly one cmd_exec_rc call, got {calls}"
    args_list, wd, _ = calls[0]
    assert args_list == ['make']
    assert wd == str(repo)
    assert '-C' not in args_list


def test_testcase_substitutions_and_match(tmp_path):
    from autograder.actions.test import ProjectConfig
    project_cfg = ProjectConfig({'build': 'none'})
    args = make_args('projx')
    tc_cfg = {
        'name': '01',
        'input': ["./$project", "$project_tests/in.txt", "$digital/dig.jar", "$name"],
        'expected': "ok",
        'rubric': 1,
    }
    tc = TestCase(tc_cfg, project_cfg, args)
    tc.init_expected('/path/to/tests/projx')
    tc.init_cmd_line('/home/user/Digital.jar', '/path/to/tests/projx')
    # Verify substitutions occurred
    cl = ' '.join(tc.cmd_line)
    assert './projx' in cl
    assert '/path/to/tests/projx/in.txt' in cl
    assert '/home/user/Digital.jar' in cl
    assert '01' in cl
