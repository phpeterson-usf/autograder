import sys
import pytest

from actions import cmd as CMD


def py_cmd(*lines):
    # Build a portable python command that prints given lines
    code = ";".join([f"print({line!r})" for line in lines])
    return [sys.executable, "-c", code]


def py_exit(code):
    return [sys.executable, "-c", f"import sys; sys.exit({code})"]


def py_sleep(seconds):
    return [sys.executable, "-c", f"import time; time.sleep({seconds})"]


def test_cmd_exec_rc_zero_and_nonzero():
    assert CMD.cmd_exec_rc(py_exit(0), timeout=5) == 0
    assert CMD.cmd_exec_rc(py_exit(1), timeout=5) == 1


def test_cmd_exec_capture_stdout():
    out = CMD.cmd_exec_capture(py_cmd("hello world"), timeout=5)
    assert out == "hello world"


def test_cmd_exec_timeout():
    # Use a very small timeout; loop may wait up to 1s due to select
    with pytest.raises(Exception):
        CMD.cmd_exec(py_sleep(3), timeout=0.1)


def test_cmd_exec_output_limit_exceeded():
    # Generate > 2000 bytes quickly and set a small output_limit
    big = "x" * 5000
    with pytest.raises(CMD.OutputLimitExceeded):
        CMD.cmd_exec(py_cmd(big), timeout=5, output_limit=1000)

