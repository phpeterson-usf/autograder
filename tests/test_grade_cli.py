import json
from pathlib import Path

import pytest

import autograder.actions as actions
from autograder.actions.config import Args, Config


def test_grade_action_test_end_to_end(tmp_path, monkeypatch):
    # Arrange synthetic repo and tests
    from tests.helpers import write_mini_repo, write_tests_repo
    project = 'projx'
    repo = write_mini_repo(tmp_path, program_name=project)
    tests_repo = write_tests_repo(tmp_path, project=project)

    # Build Args and Config
    args = Args({
        'action': 'test', 'by_date': False, 'exec_cmd': None,
        'github_action': False, 'test_name': None, 'project': project,
        'students': None, 'verbose': False, 'very_verbose': False,
    })

    from autograder.actions.config import Config
    # Minimal config doc for components used in grade.py
    cfg_doc = {
        'Canvas': type('X', (), {})(),
        'CanvasMapper': type('X', (), {})(),
        'Git': {'org': 'o', 'credentials': 'ssh'},
        'Github': {'host_name': 'api.github.com', 'access_token': 'tok'},
        'Test': {'tests_path': str(tests_repo)},
        'Config': {'students': []},
    }
    cfg = Config(cfg_doc)

    # Monkeypatch Config.from_path and Args.from_cmdline to supply our objects
    monkeypatch.setattr('autograder.actions.config.Config.from_path', staticmethod(lambda p: cfg))
    monkeypatch.setattr('autograder.actions.config.Config.get_path', staticmethod(lambda: Path('dummy')))
    monkeypatch.setattr('autograder.actions.config.Args.from_cmdline', staticmethod(lambda: args))

    # Run main() and assert it prints final score and returns 0
    import importlib
    import autograder.actions.cmd as CMD
    from autograder import grade as grade_mod
    # Patch print_justified to avoid padding
    monkeypatch.setattr('autograder.actions.util.print_justified', lambda s, n: None)
    # Ensure CWD is the repo root for action 'test'
    monkeypatch.chdir(repo)
    # Execute main
    # Run without asserting return value (grade.main returns None for 'test')
    grade_mod.main()


def test_grade_action_class_json_and_histogram(tmp_path, monkeypatch, capsys):
    project = 'projx'
    args = Args({
        'action': 'class', 'by_date': False, 'exec_cmd': None,
        'github_action': False, 'test_name': None, 'project': project,
        'students': ['alice', 'bob'], 'verbose': False, 'very_verbose': False,
    })

    # Return fixed test results per repo
    class FakeTest:
        def __init__(self, *_):
            # Provide attribute used by grade.main
            self.project_cfg = type('PC', (), {'subdir': None})()
        def test(self, repo):
            return {'student': repo.student, 'score': 5, 'comment': 'ok', 'results': []}
        def print_histogram(self, class_results):
            print("Score frequency (n = {})".format(len(class_results)))
        def total_rubric(self):
            return 10

    cfg_doc = {
        'Canvas': type('X', (), {})(),
        'CanvasMapper': type('X', (), {})(),
        'Git': {'org': 'o', 'credentials': 'ssh'},
        'Github': {'host_name':'api.github.com','access_token':'tok'},
        'Test': {'tests_path': str(tmp_path)},
        'Config': {'students': ['alice', 'bob']},
    }
    cfg = Config(cfg_doc)

    monkeypatch.setattr('autograder.actions.config.Config.from_path', staticmethod(lambda p: cfg))
    monkeypatch.setattr('autograder.actions.config.Config.get_path', staticmethod(lambda: Path('dummy')))
    monkeypatch.setattr('autograder.actions.config.Args.from_cmdline', staticmethod(lambda: args))
    monkeypatch.setattr('autograder.actions.test.Test', FakeTest)
    monkeypatch.chdir(tmp_path)

    from autograder import grade as grade_mod
    # Avoid padded printing
    monkeypatch.setattr('autograder.actions.util.print_justified', lambda s, n: None)
    # Run without asserting return value (grade.main returns None for 'class')
    grade_mod.main()
    # Verify JSON file exists
    data = json.loads((tmp_path / f'{project}.json').read_text())
    assert {r['student'] for r in data} == {'alice', 'bob'}
    captured = capsys.readouterr().out
    assert 'Score frequency (n = 2)' in captured
