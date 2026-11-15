"""Darwin owned-child containment, armed before any ML import.

Only the controller owns the lifeline's write end. A small forked guardian keeps
the worker's private process group alive and watches EOF independently of the
worker's GIL/native calls. It never enumerates or signals another process group.
Importing this module does not import psutil, create a process or inspect models.
"""
import fcntl
import os
import select
import shutil
import signal
import stat
import sys
import time


AVAILABLE_FLOOR = 805306368


def observe_resources(available_floor=AVAILABLE_FLOOR):
    """Fresh shared-memory admission; disk free is telemetry, not a new cap."""
    if type(available_floor) is not int or available_floor < AVAILABLE_FLOOR:
        raise ValueError("The existing shared available-memory floor is required")
    import psutil
    memory = psutil.virtual_memory()
    if type(memory.available) is not int or memory.available < available_floor:
        raise RuntimeError("SHARED_AVAILABLE_MEMORY_FLOOR_NOT_MET")
    return {"available_memory_bytes": memory.available,
            "total_memory_bytes": memory.total,
            "available_memory_floor_bytes": available_floor,
            "disk_free_bytes": shutil.disk_usage(os.getcwd()).free,
            "model_memory_fit": "UNPERFORMED"}


def _terminate_owned_group(group):
    # The guardian itself keeps this exact group from disappearing/reuse.
    if group != os.getpgrp():
        raise RuntimeError("REFUSE_TO_SIGNAL_ANOTHER_PROCESS_GROUP")
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    os.killpg(group, signal.SIGTERM)
    time.sleep(3)
    os.killpg(group, signal.SIGKILL)
    os._exit(127)  # Defensive fallback if the signal was not delivered.


def _watch(lifeline_fd, ready_fd, worker_pid, group, available_floor):
    """Runs only in the pre-ML guardian; all faults contain the owned group."""
    ready_open = True
    try:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        import psutil
        worker = psutil.Process(worker_pid)  # Exact owned PID, never enumeration.
        created = worker.create_time()
        observe_resources(available_floor)
        os.write(ready_fd, b"R")
        os.close(ready_fd)
        ready_open = False
        while True:
            readable, _, _ = select.select([lifeline_fd], [], [], 0.5)
            if readable:
                # EOF is parent death; data is an invalid lifeline protocol.
                os.read(lifeline_fd, 1)
                break
            observe_resources(available_floor)
            if (worker.create_time() != created
                    or os.getpgid(worker_pid) != group):
                break
            # Retain per-process resource sampling without touching journals.
            worker.memory_info()
            worker.cpu_times()
    except BaseException:
        pass  # Unknown observation/read failures must stop, never abandon work.
    finally:
        try:
            if ready_open:
                os.close(ready_fd)
        finally:
            _terminate_owned_group(group)


def arm(lifeline_fd, expected_parent_pid, available_floor=AVAILABLE_FLOOR):
    """Arm one independent guardian and consume the worker's read descriptor.

    A five-second *readiness handshake* limits guardian setup only; it does not
    impose a model-work deadline. The controller still owns normal cleanup.
    """
    if sys.platform != "darwin":
        raise RuntimeError("DARWIN_CONTAINMENT_REQUIRES_DARWIN")
    pid = os.getpid()
    if (type(lifeline_fd) is not int or lifeline_fd < 0
            or type(expected_parent_pid) is not int or expected_parent_pid <= 1
            or os.getppid() != expected_parent_pid
            or os.getpgid(pid) != pid or os.getsid(pid) != pid):
        raise RuntimeError("OWNED_PRIVATE_SESSION_AND_PARENT_REQUIRED")
    if (not stat.S_ISFIFO(os.fstat(lifeline_fd).st_mode)
            or fcntl.fcntl(lifeline_fd, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDONLY):
        raise RuntimeError("READ_ONLY_PARENT_LIFELINE_REQUIRED")
    observe_resources(available_floor)
    ready_read, ready_write = os.pipe()
    try:
        guardian = os.fork()  # Before ML imports, model threads or native work.
        if guardian == 0:
            os.close(ready_read)
            _watch(lifeline_fd, ready_write, pid, pid, available_floor)
            os._exit(127)
        os.close(ready_write)
        ready_write = None
        readable, _, _ = select.select([ready_read], [], [], 5)
        if (not readable or os.read(ready_read, 1) != b"R"
                or os.getppid() != expected_parent_pid):
            raise RuntimeError("DARWIN_GUARDIAN_NOT_READY")
        return guardian
    finally:
        os.close(ready_read)
        if ready_write is not None:
            os.close(ready_write)
        os.close(lifeline_fd)
