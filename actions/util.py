"""
util.py is the "junk drawer" of code which is shared by multiple modules
"""

import sys
import tomlkit

class OutputLimitExceeded(Exception):
    pass

class Config(object):
    def safe_update(self, src):
        # Only copy values from src when the key is in dest
        # Prevents namespace pollution from TOML config files
        dest = self.__dict__
        for k, v in src.items():
            if k in dest:
                dest[k] = v
            else:
                fatal(f'safe_update ignoring key: {k}')


def fatal(s):
    print_red(s, '\n')
    sys.exit(-1)


def warn(s):
    print_yellow(s, '\n')


def print_green(s, e=''):
    print('\033[92m' + s + '\033[0m', end=e, flush=True)


def print_yellow(s, e=''):
    print('\033[93m' + s + '\033[0m', end=e, flush=True)


def print_red(s, e=''):
    print('\033[91m' + s + '\033[0m', end=e, flush=True)


def print_justified(s, longest):
    print(s, end='')
    for i in range (longest - len(s)):
        print(' ', end='')


def failed(tc_result):
    if tc_result['score'] == 0:
        return True
    return False


def format_pass_fail(tc_result):
    name = tc_result['test']
    rubric = tc_result['rubric']
    score = tc_result['score']

    # Pad formatted string out to same length as full credit
    # so that individual test cases and the total are column-aligned
    max_len = len(f'{name}({rubric}/{rubric}) ')
    this_fmt = f'{name}({score}/{rubric}) '
    padding = max_len - len(this_fmt)
    for i in range(padding):
        this_fmt += ' '

    return this_fmt


def load_toml(path):
    try:
        with open(path) as f:
            data = f.read()
            return tomlkit.parse(data)
    except FileNotFoundError as fnf:
        return {}  # handled in callers
    except Exception as e:
        fatal(f'Failed to parse {path}: ' + str(e))


def make_repo_path(project, student):
    return f'{project}-{student}'


def project_from_cwd(cwd):
    # if the current directory is named like a given project (project-username),
    # use that as the project name
    # eg. if cwd is '/path/to/project1-phpeterson', return 'project1'
    # otherwise, use the current directory name
    # eg. if cwd is '/path/to/project1', use 'project1'
    i = cwd.name.find('-')
    return cwd.name if i == -1 else cwd.name[:i]


def init_repo_result(student):
    # Shared between test.py and github.py
    # Write this as a plain dict rather than a class so it's JSON serializable
    return {
            'comment'  : '',
            'results'  : [],
            'score'    : 0,
            'student'  : student
    }


def init_tc_result(rubric, test_name):
    # Shared between test.py and github.py
    # Write this as a plain dict rather than a class so it's JSON serializable
    return {
        'rubric': rubric,
        'score' : 0,
        'test'  : test_name,
    }
