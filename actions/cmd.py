import atexit
import io
import os
import shutil
import signal
import subprocess
import sys
import time

from actions.util import OutputLimitExceeded

# default command timeout in seconds
TIMEOUT = 20
# default output limit in bytes
OUTPUT_LIMIT = 10000

# Wrapper to return values from cmd_exec
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

    # Only kill process group on POSIX systems
    if os.name != 'posix':
        return

    if global_cleanup_gpid:
        try:
            os.killpg(global_cleanup_gpid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def cmd_exec(args, wd=None, shell=False, check=True, timeout=TIMEOUT,
             output_limit=OUTPUT_LIMIT):
    presults = ProcResults(0, None, None)

    global global_cleanup_registered
    global global_cleanup_gpid

    # Only register cmd_cleanup() once 
    if not global_cleanup_registered:
        global_cleanup_registered = True    
        atexit.register(cmd_cleanup)

    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                             start_new_session=True, cwd=wd, shell=shell)

        global_cleanup_gpid = os.getpgid(proc.pid)
        
        buf = io.StringIO()
        total_bytes = 0;

        while (proc.poll() == None) & (total_bytes < output_limit):
            cur_data = proc.stdout.read().decode('utf-8')
            total_bytes += len(cur_data)
            buf.write(cur_data)
    
        presults.stdout = buf
        presults.stderr = None
        presults.returncode = proc.returncode

    except subprocess.TimeoutExpired:
        if os.name == 'posix':
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
            # Delay to allow processes to exit
            time.sleep(3)
            # This can only wait for the parent of the process group
            os.waitpid(-pgid, os.WNOHANG)
        raise

    # Raise exception if output_limit exceeded        
    if total_bytes > output_limit:
        raise OutputLimitExceeded
                
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

        if output is not None:
            #return output.decode('utf-8').rstrip('\n')
            return output.getvalue().rstrip('\n')
