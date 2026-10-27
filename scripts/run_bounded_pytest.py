"""Run mandatory isolated pytest with traces and a fail-closed process deadline."""
from __future__ import annotations
import argparse
import os
import signal
import subprocess
import sys


def run_tests(arguments, *, timeout_seconds=480, trace_seconds=120, output=None):
    if timeout_seconds <= 0 or trace_seconds <= 0 or trace_seconds >= timeout_seconds:
        raise ValueError("positive trace interval below the test deadline is required")
    bootstrap = (
        "import faulthandler,runpy,sys;"
        f"faulthandler.dump_traceback_later({trace_seconds!r},repeat=True);"
        "sys.argv=['pytest']+sys.argv[1:];runpy.run_module('pytest',run_name='__main__')"
    )
    process = subprocess.Popen(
        [sys.executable, "-u", "-c", bootstrap, *arguments], start_new_session=True,
        stdout=output, stderr=output,
    )
    try:
        return process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        print("Mandatory isolated tests exceeded their deadline; gate FAIL, no PASS inferred.", file=sys.stderr, flush=True)
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        return 124
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=float, default=480)
    parser.add_argument("--trace-seconds", type=float, default=120)
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    arguments = args.pytest_args
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    if not arguments:
        parser.error("explicit mandatory test paths are required")
    return run_tests(arguments, timeout_seconds=args.timeout_seconds, trace_seconds=args.trace_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
