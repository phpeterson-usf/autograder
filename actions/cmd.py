import subprocess

def cmd_exec(args, wd=None, shell=False):
    return subprocess.run(args, timeout=5, check=True, cwd=wd, capture_output=True, shell=shell)


def cmd_exec_rc(args, wd=None):
    proc = cmd_exec(args, wd)
    return proc.returncode


def cmd_exec_capture(args, wd=None, path=None, shell=False):
    try:
        proc = cmd_exec(args, wd, shell)
    except subprocess.CalledProcessError as e:
        return str(e)

    if (path):
        # capture output written to path
        f = open(path, 'r')
        output = f.read()
        f.close()
    else:
        try:
            # capture output written to stdout
            output = proc.stdout.decode('utf-8')
            return output.rstrip('\n')
        except UnicodeDecodeError as e:
            print('Output contains non-printable characters')
            return ''
