import sys
import tomlkit

def fatal(s):
    print_red(s, '\n')
    sys.exit(-1)


def print_green(s, e=''):
    print('\033[92m' + s + '\033[0m', end=e, flush=True)


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
    if failed(tc_result):
        return tc_result['test'] + '- '
    return tc_result['test'] + '+ '


def load_toml(path):
    try:
        with open(path) as f:
            data = f.read()
            return tomlkit.parse(data)
    except Exception as e:
        fatal(f'{path}: {e}')


def make_repo_path(project, student):
    return f'{project}-{student}'
