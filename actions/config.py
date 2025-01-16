import argparse
import json
import os
from pathlib import Path
import pprint
import tomlkit

from actions.test import TestConfig
from actions.canvas import CanvasConfig, CanvasMapperConfig
from actions.git import GitConfig
from actions.github import GithubConfig
from actions.util import *


class Args:
    def __init__(self, d):
        self.__dict__.update(d)

    @staticmethod
    def from_cmdline():
        p = argparse.ArgumentParser()
        p.add_argument('action', type=str, choices=[
            'class', 'clone', 'exec', 'pull', 'test', 'upload'
        ])
        p.add_argument('-d', '--date', help='Checkout repo as of YYYY-MM-DD at 00:00:00',
            default=None)
        p.add_argument('-e', '--exec_cmd', help='Command to execute in each repo',
            default=None)
        p.add_argument('-g', '--github-action', action='store_true', help='test by downloading Github Action result',
            default=False)
        p.add_argument('-n', '--test-name', help='Run test case with this name',
            default=None)
        p.add_argument('-p', '--project', help='Project name',
            default=project_from_cwd(Path.cwd()))
        p.add_argument('-s', '--students', help='List of GitHub usernames', nargs='+',
            default=None)
        p.add_argument('-v', '--verbose', action='store_true', help='Print actual and expected output when they don\'t match',
            default=False)
        p.add_argument('-vv', '--very-verbose', action='store_true', help='Print actual and expected output whether they match or not',
            default=False)

        d = vars(p.parse_args())

        # Create the Args object
        return json.loads(json.dumps(d), object_hook=Args)


class ConfigConfig(Config):
    def __init__(self, cfg):
        self.students = []
        self.safe_update(cfg)

"""
__init__(self, doc)
  self.canvas = doc.get('Canvas')

 doc['Canvas'] = CanvasConfig({})
"""

class Config:


    def __init__(self, doc):
        self.canvas_cfg = doc['Canvas']
        self.canvas_mapper_cfg = doc['CanvasMapper']
        self.git_cfg = doc['Git']
        self.github_cfg = doc['Github']
        self.test_cfg = doc['Test']
        self.config_cfg = ConfigConfig(doc['Config'])


    @staticmethod
    def get_path(verbose):
        fname = 'config.toml'
        if os.environ.get('GRADE_CONFIG_DIR'):
            # First choice: config file in dir named by env var
            dirname = Path(os.environ['GRADE_CONFIG_DIR']).expanduser()
        else:
            # Second choice: traverse parent dirs looking for config file
            found = False
            dirname = Path(os.getcwd()).absolute()
            while not found:
                p = dirname / fname
                if p.exists():
                    found = True
                else:
                    dirname = dirname.parent
                    if dirname == Path('~').expanduser():
                        break
            if not found:
                # Last choice: config file will be read (and created) in ~/.config
                dirname = Path.home() / '.config' / 'grade'
        path = dirname / fname
        if verbose:
            print(f'config file: {path}')
        return path


    # Helper function for write_empty_actions() to minimize
    # the amount of code in the eval() string
    @staticmethod
    def make_commented_table(d):
        tbl = tomlkit.table()
        for k,v in d.items():
            if type(v) == str:
                line = f'{k} = "{v}"'
            elif type(v) == int:
                line = f'{k} = {v}'
            elif type(v) == list and not v:
                line = f'{k} = []'
            else:
                # If we need booleans, handle python True vs TOML true
                raise TypeError(f'Not handled: {type(v)} for key: {k}')
            tbl.add(tomlkit.comment(line))

        return tbl


    # Make a commented-out tomlkit config for given actions using tuples
    # of the table name and default config for that section
    @staticmethod
    def write_default_tables(path, tpls):
        doc = tomlkit.document()
        for t in tpls:
            doc[t[0]] = Config.make_commented_table(t[1].__dict__)
        toml_data = tomlkit.dumps(doc)
        with open(path, 'w') as f:
            f.write(toml_data)


    # Read the config file, creating it if needed
    @staticmethod
    def from_path(path):
        # Create config.toml silently
        if not path.exists():
            # This is gross but I wasn't sure how to fix parent() not supported by PosixPath
            Path.mkdir(Path(os.path.dirname(path)), parents=True, exist_ok=True)
            tpls = [
                ('Canvas', CanvasConfig({})),
                ('CanvasMapper', CanvasMapperConfig({})),
                ('Config', ConfigConfig({})),
                ('Git', GitConfig({})),
                ('Github', GithubConfig({})),
                ('Test', TestConfig({})),
            ]
            Config.write_default_tables(path, tpls)

        # Any config in the TOML file overrides defaults
        doc = load_toml(path)
        if not doc:
            # This shouldn't happen since we just created the file
            fatal(f'failed to load {path}')

        # Create the Config object
        return Config(doc)
