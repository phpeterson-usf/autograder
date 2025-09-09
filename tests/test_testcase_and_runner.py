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
