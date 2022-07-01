import argparse
import json
import pathlib
import pprint
import tomlkit

from actions.test import Test
from actions.canvas import Canvas, CanvasMapper
from actions.git import Git
from actions.util import load_toml, config_path


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
            raise TypeError(f'Not handled: {type(v)}')
        tbl.add(tomlkit.comment(line))

    return tbl


class Args:
    def __init__(self, d):
        self.__dict__.update(d)

    @staticmethod
    def from_cmdline():
        p = argparse.ArgumentParser()
        p.add_argument('action', type=str, choices=[
            'class', 'clone', 'config', 'exec', 'pull', 'test', 'upload'
        ])
        p.add_argument('-d', '--date', help='Checkout repo as of YYYY-MM-DD at 00:00:00',
            default=None)
        p.add_argument('-e', '--exec_cmd', help='Command to execute in each repo',
            default=None)
        p.add_argument('-i', '--instructor', action='store_true', help='Write full config for instructors',
            default=False)
        p.add_argument('-n', '--test-name', help='Run test case with this name',
            default=None)
        p.add_argument('-p', '--project', help='Project name',
            default=None)
        p.add_argument('-v', '--verbose', action='store_true', help='Print actual and expected output when they don\'t match',
            default=False)
        p.add_argument('-vv', '--very-verbose', action='store_true', help='Print actual and expected output whether they match or not',
            default=False)

        d = vars(p.parse_args())

        # Create the Args object
        return json.loads(json.dumps(d), object_hook=Args)


class Config:
    default_cfg = {
        'students': [],
    }
    
    path = config_path()

    def __init__(self, d):
        self.__dict__.update(d)


    # Every time initialization
    @staticmethod
    def from_file():
        actions = ['Canvas', 'CanvasMapper', 'Config', 'Git',  'Test']

        # Initialize with default cfg for each action module
        d = {}
        for act in actions:
            d[act] = eval(f'{act}.default_cfg')

        # Any config in the TOML file overrides defaults
        doc = load_toml(Config.path)
        for act in actions:
            d[act].update(doc[act])

        # Create the Config object
        return json.loads(json.dumps(d), object_hook=Config)


    # Make a commented-out tomlkit config for given actions
    @staticmethod
    def write_empty_actions(path, actions):
        doc = tomlkit.document()
        for act in actions:
            doc[act] = eval(f'make_commented_table({act}.default_cfg)')
        toml_data = tomlkit.dumps(doc)
        with open(path, 'w') as f:
            f.write(toml_data)


    # One-time config in response to "grade config"
    @staticmethod
    def write_empty_config(for_instructor):
        actions = ['Test']  # Empty config for students
        if for_instructor:
            # Add empty config for instructors
            actions += ['Canvas', 'CanvasMapper', 'Config', 'Git']

        if not Config.path.exists():
            # config.toml not found
            Config.write_empty_actions(Config.path, actions)
        else:
            # Non-destructive
            print('File already exists: ', Config.path)
