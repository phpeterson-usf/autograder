import atexit
import os
import shutil
import signal
import subprocess
import sys
import time

# default command timeout in seconds
TIMEOUT = 20

class ProcResults(object):
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

global_cleanup_registered = False
global_cleanup_gpid = None

# Handler to be called on process exit (e.g., CTRL-C)
def cmd_cleanup():
    global global_cleanup_registered
    global global_cleanup_gpid

    if os.name ! 'posix':
        return

    if global_cleanup_gpid:
        #print(f'cmd_cleanup() killing process group {global_cleanup_gpid}', file=sys.stderr)
        try:
            os.killpg(global_cleanup_gpid, signal.SIGTERM)
        except ProcessLookupError:
            pass

def cmd_exec(args, wd=None, shell=False, check=True, timeout=TIMEOUT):
    presults = ProcResults(0, None, None)

    global global_cleanup_registered
    global global_cleanup_gpid

    # Only register cmd_cleanup() once 
    if not global_cleanup_registered:
        global_cleanup_registered = True    
        atexit.register(cmd_cleanup)

    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                             start_new_session=True, cwd=wd, shell=shell)

        #parent_gpid = os.getpgid(os.getpid())
        #print(f'cmd_exec() os.getpgid(os.getpid()) = {parent_gpid}', file=sys.stderr)

        global_cleanup_gpid = os.getpgid(proc.pid)
        
        #print(f'cmd_exec() os.getpgid(proc.pid) = {global_cleanup_gpid}', file=sys.stderr)

        presults.stdout, presults.stderr = proc.communicate(timeout=timeout)
        presults.returncode = proc.returncode

    except subprocess.TimeoutExpired:
        #print(f'cmd_exec() Timeout for {args} ({timeout}s) expired', file=sys.stderr)
        if os.name == 'posix':
            #print(f'cmd_exec() os.killpg()', file=sys.stderr)
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
            time.sleep(5)
            os.waitpid(-pgid, os.WNOHANG)
    
            
    return presults

def cmd_exec_rc(args, wd=None):
    presults = cmd_exec(args, wd=wd, check=False)
    return presults.returncode

def cmd_exec_capture(args, wd=None, path=None, shell=False, timeout=TIMEOUT):
    presults = cmd_exec(args, wd=wd, shell=shell, check=True, timeout=timeout)
    if (path):
        # capture output written to path
        with open(path, 'r') as f:
            return f.read()
    else:
        # capture output written to stdout or stderr
        output = presults.stdout if presults.stdout else presults.stderr

        #print("cmd_exec_capture() stderr:")
        #print(presults.stderr.decode('utf-8'))

        if output:
            return output.decode('utf-8').rstrip('\n')
        else:
            return "cmd timeout"
