import argparse
import json
from pathlib import Path
import pprint
import tomlkit

from actions.test import Test
from actions.canvas import Canvas, CanvasMapper
from actions.git import Git
from actions.util import load_toml


class Args:
    def __init__(self, d):
        self.__dict__.update(d)

    @staticmethod
    def from_cmdline():
        p = argparse.ArgumentParser()
        p.add_argument('action', type=str, choices=[
            'class', 'clone', 'complete', 'exec', 'pull', 'test', 'upload'
        ])
        p.add_argument('-d', '--date', help='Checkout repo as of YYYY-MM-DD at 00:00:00',
            default=None)
        p.add_argument('-e', '--exec_cmd', help='Command to execute in each repo',
            default=None)
        p.add_argument('-n', '--test-name', help='Run test case with this name',
            default=None)
        p.add_argument('-p', '--project', help='Project name',
            default=None)
        p.add_argument('-s', '--students', help='List of GitHub usernames', nargs='+',
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

    dirname = Path.home() / '.config' / 'grade'
    path = dirname / 'config.toml'


    def __init__(self, d):
        self.__dict__.update(d)


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
                raise TypeError(f'Not handled: {type(v)}')
            tbl.add(tomlkit.comment(line))

        return tbl


    # Make a commented-out tomlkit config for given actions using eval()
    # to iterate over the list of actions with default configuration
    @staticmethod
    def write_empty_actions(path, actions):
        doc = tomlkit.document()
        for act in actions:
            doc[act] = eval(f'Config.make_commented_table({act}.default_cfg)')
        toml_data = tomlkit.dumps(doc)
        with open(path, 'w') as f:
            f.write(toml_data)


    # Read the config file, creating it if needed
    @staticmethod
    def from_file():
        actions = ['Canvas', 'CanvasMapper', 'Config', 'Git',  'Test']

        # Create config.toml silently
        if not Config.path.exists():
            Path.mkdir(Config.dirname, parents=True, exist_ok=True)
            Config.write_empty_actions(Config.path, actions)

        # Initialize with default cfg for each action module
        d = {}
        for act in actions:
            d[act] = eval(f'{act}.default_cfg')

        # Any config in the TOML file overrides defaults
        doc = load_toml(Config.path)
        if not doc:
            # This shouldn't happen since we just created the file
            fatal(f'failed to load {Config.path}')
        for act in actions:
            if doc.get(act):
                d[act].update(doc[act])

        # Create the Config object
        return json.loads(json.dumps(d), object_hook=Config)
