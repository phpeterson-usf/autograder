import os
import signal
import subprocess
import sys

# default command timeout in seconds
TIMEOUT = 20

def cmd_exec(args, wd=None, shell=False, check=True, timeout=TIMEOUT):
    #return subprocess.run(args, capture_output=True, cwd=wd, shell=shell, check=check)
    try:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                             start_new_session=True, cwd=wd, shell=shell)
        #p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
        #                     preexec_fn=os.setsid, cwd=wd, shell=shell)
        p.stdout = None
        p.stderr = None
        p.stdout, p.stderr = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f'cmd_exec() Timeout for {args} ({timeout}s) expired', file=sys.stderr)
        if os.name == 'posix':
            print(f'cmd_exec() os.killpg()', file=sys.stderr)
            #os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
    return p

def cmd_exec_rc(args, wd=None):
    proc = cmd_exec(args, wd, check=False)
    return proc.returncode

def cmd_exec_capture(args, wd=None, path=None, shell=False, timeout=TIMEOUT):
    proc = cmd_exec(args, wd, shell, check=True, timeout=timeout)
    if (path):
        # capture output written to path
        with open(path, 'r') as f:
            return f.read()
    else:
        # capture output written to stdout or stderr
        output = proc.stdout if proc.stdout else proc.stderr
        if output:
            return output.decode('utf-8').rstrip('\n')
        else:
            return "cmd timeout"
