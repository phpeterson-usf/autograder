import subprocess
from actions.util import print_red


def cmd_exec(args, wd=None, shell=False, check=True):
    return subprocess.run(args, timeout=15, check=check, cwd=wd, capture_output=True, shell=shell)


def cmd_exec_rc(args, wd=None):
    proc = cmd_exec(args, wd)
    return proc.returncode


def cmd_exec_capture(args, wd=None, path=None, shell=False):
    try:
        proc = cmd_exec(args, wd, shell, check=False)
    except (
        subprocess.CalledProcessError, 
        subprocess.TimeoutExpired,
        FileNotFoundError, 
        PermissionError
    ) as e:
        print_red(str(e), '\n')
        return ''

    if (path):
        # capture output written to path
        with open(path, 'r') as f:
            return f.read()
    else:
        try:
            # capture output written to stdout
            output = proc.stdout.decode('utf-8')
            return output.rstrip('\n')
        except UnicodeDecodeError as e:
            print('Output contains non-printable characters')
            return ''
