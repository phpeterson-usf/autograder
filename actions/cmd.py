import subprocess

def cmd_exec(args, wd=None, shell=False, check=True):
    return subprocess.run(args, timeout=30, check=check, cwd=wd, capture_output=True, shell=shell)


def cmd_exec_rc(args, wd=None):
    proc = cmd_exec(args, wd)
    return proc.returncode


def cmd_exec_capture(args, wd=None, path=None, shell=False):
    proc = cmd_exec(args, wd, shell, check=True)
    if (path):
        # capture output written to path
        with open(path, 'r') as f:
            return f.read()
    else:
        # capture output written to stdout or stderr
        output = proc.stdout if proc.stdout else proc.stderr
        return output.decode('utf-8').rstrip('\n')
