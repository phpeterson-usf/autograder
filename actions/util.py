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
    name = tc_result['test']
    rubric = tc_result['rubric']
    base = f'{name}({rubric})'
    if failed(tc_result):
        return base + '- '
    return base + '+ '


def load_toml(path):
    try:
        with open(path) as f:
            data = f.read()
            return tomlkit.parse(data)
    except FileNotFoundError as fnf:
        fatal(f'File not found: {path}. Suggest "git pull" in tests repo')
    except Exception as e:
        fatal(f'Failed to parse {path}: ' + str(e))

def make_repo_path(project, student):
    return f'{project}-{student}'
