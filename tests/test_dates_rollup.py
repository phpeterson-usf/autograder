import json
import sys
from pathlib import Path

from autograder.actions.dates import Dates
from autograder.actions.rollup import rollup


def write_dates_toml(base: Path, project: str):
    p = base / 'dates.toml'
    p.write_text(
        f"""
[{project}]
[[{project}.dates]]
suffix = 'D1'
date = '2024-09-30'
percentage = 0.5

[[{project}.dates]]
suffix = 'D2'
date = '2024-10-15'
percentage = 1.0
"""
    )
    return p


def test_dates_from_path_and_select(tmp_path, monkeypatch):
    project = 'projx'
    write_dates_toml(tmp_path, project)
    class A:
        def __init__(self, project):
            self.project = project
            self.verbose = False
    d = Dates.from_path(str(tmp_path), A(project))
    # Simulate select index 1 (second date) by patching class inside function scope
    class FakeMenu:
        def __init__(self, opts):
            self.opts = opts
        def show(self):
            return 1
    monkeypatch.setitem(sys.modules, 'simple_term_menu', type('M', (), {'TerminalMenu': FakeMenu}))
    sel = d.select_date()
    assert sel.suffix == 'D2'


def test_rollup_accumulates_scores(tmp_path, monkeypatch):
    project = 'projx'
    write_dates_toml(tmp_path, project)
    class A:
        def __init__(self, project):
            self.project = project
            self.verbose = False
    d = Dates.from_path(str(tmp_path), A(project))

    # Create two JSON files for D1 and D2
    d1 = [
        {'student': 'alice', 'score': 6, 'comment': 'c1'},
        {'student': 'bob', 'score': 4, 'comment': 'c1'},
    ]
    d2 = [
        {'student': 'alice', 'score': 10, 'comment': 'c2'},
        {'student': 'bob', 'score': 4, 'comment': 'c2'},
    ]
    (tmp_path / f'{project}-D1.json').write_text(json.dumps(d1))
    (tmp_path / f'{project}-D2.json').write_text(json.dumps(d2))
    monkeypatch.chdir(tmp_path)

    class Cfg: pass
    class Args:
        def __init__(self, project):
            self.project = project
    rollup(Cfg, Args(project), d.dates)

    out = json.loads((tmp_path / f'{project}-rollup.json').read_text())
    # alice: start 0 -> D1: 0+(6-0)*0.5=3 -> D2: 3+(10-3)*1.0=10
    alice = next(x for x in out if x['student']=='alice')
    assert int(alice['score']) == 10
    # bob: D1 0+(4-0)*0.5=2 -> D2 unchanged score keeps rolled at 2
    bob = next(x for x in out if x['student']=='bob')
    assert int(bob['score']) == 2
