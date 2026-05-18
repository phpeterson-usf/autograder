"""
util.py is the "junk drawer" of code which is shared by multiple modules
"""

import sys
import tomlkit

class OutputLimitExceeded(Exception):
    pass

class SafeConfig(object):
    def safe_update(self, src):
        # Only copy values from src when the key is in dest
        # Prevents namespace pollution from TOML config files
        dest = self.__dict__
        for k, v in src.items():
            if k not in dest:
                fatal(f'safe_update ignoring key: {k}')
            default = dest[k]
            if not _toml_types_compatible(default, v):
                expected = type(default).__name__
                got = type(v).__name__
                fatal(f"config key '{k}' expected {expected} but got "
                      f"{got}: {v!r}")
            dest[k] = v


def _toml_types_compatible(default, v):
    """Check whether `v` is an acceptable replacement for `default`. Used by
    SafeConfig.safe_update to catch type errors in TOML config (e.g. a
    boolean where a string is expected) before they manifest deeper in the
    call stack."""
    # A None default means "no opinion" — the field is nullable.
    if default is None:
        return True
    # bool is a subclass of int in Python; we want strict separation so
    # `enabled = 1` does not silently satisfy a bool field, and `timeout = true`
    # does not silently satisfy an int field.
    if isinstance(default, bool) != isinstance(v, bool):
        return False
    # isinstance (not `type(x) is type(y)`) so tomlkit's String/Integer/etc.
    # subclasses of the built-in types still match.
    return isinstance(v, type(default))


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
