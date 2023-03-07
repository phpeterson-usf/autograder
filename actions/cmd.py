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
# read buffer size
READ_BUFFER_SIZE = 1024


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

        os.set_blocking(proc.stdout.fileno(), False)
        #os.set_blocking(proc.stderr.fileno(), False)
        global_cleanup_gpid = os.getpgid(proc.pid)
        timer = time.time() + timeout
        
        buf = io.StringIO()
        total_bytes = 0;

        while True:
            if proc.poll() is not None:
                break
            if time.time() > timer:
                raise subprocess.TimeoutExpired(args, timeout)
            if total_bytes > output_limit:
                break

            cur_bytes = proc.stdout.read(READ_BUFFER_SIZE)

            print(cur_bytes)
            
            # If no data available, delay for 1/2 second
            if cur_bytes is None:
                time.sleep(0.5)
                cur_data = '';
            else:
                cur_data = cur_bytes.decode('utf-8')
                print(cur_data)
            
            if cur_data != '':
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
