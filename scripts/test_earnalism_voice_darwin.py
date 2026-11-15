"""Fake-only Darwin containment tests; no fork, kill, model or real resource call."""
import os
import stat
import types
import unittest
from unittest import mock

from scripts import earnalism_voice as voice
from scripts.earnalism_voice_runtime import darwin


class DarwinContracts(unittest.TestCase):
    def setUp(self):
        self.psutil = mock.Mock()
        self.psutil.virtual_memory.return_value = types.SimpleNamespace(
            available=darwin.AVAILABLE_FLOOR + 1, total=16 * 1024**3)
        self.patchers = [
            mock.patch.dict("sys.modules", {"psutil": self.psutil}),
            mock.patch.object(darwin.sys, "platform", "darwin"),
            mock.patch.object(darwin.os, "getpid", return_value=100),
            mock.patch.object(darwin.os, "getppid", return_value=90),
            mock.patch.object(darwin.os, "getpgid", return_value=100),
            mock.patch.object(darwin.os, "getsid", return_value=100),
            mock.patch.object(darwin.os, "getpgrp", return_value=100),
            mock.patch.object(darwin.os, "fstat", return_value=types.SimpleNamespace(st_mode=stat.S_IFIFO)),
            mock.patch.object(darwin.fcntl, "fcntl", return_value=os.O_RDONLY),
            mock.patch.object(darwin.os, "pipe", return_value=(5, 6)),
            mock.patch.object(darwin.os, "fork", return_value=101),
            mock.patch.object(darwin.os, "close"),
            mock.patch.object(darwin.os, "read", return_value=b"R"),
            mock.patch.object(darwin.os, "write"),
            mock.patch.object(darwin.os, "killpg"),
            mock.patch.object(darwin.os, "_exit"),
            mock.patch.object(darwin.signal, "signal"),
            mock.patch.object(darwin.select, "select", return_value=([5], [], [])),
            mock.patch.object(darwin.time, "sleep"),
            mock.patch.object(darwin.shutil, "disk_usage", return_value=types.SimpleNamespace(free=500)),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_fresh_admission_keeps_existing_floor_and_disk_is_telemetry(self):
        observation = darwin.observe_resources()
        self.assertEqual(observation["disk_free_bytes"], 500)
        self.assertEqual(observation["model_memory_fit"], "UNPERFORMED")
        self.psutil.virtual_memory.return_value.available = darwin.AVAILABLE_FLOOR
        darwin.observe_resources()
        self.psutil.virtual_memory.return_value.available -= 1
        with self.assertRaisesRegex(RuntimeError, "MEMORY_FLOOR"):
            darwin.observe_resources()
        with self.assertRaises(ValueError):
            darwin.observe_resources(darwin.AVAILABLE_FLOOR - 1)

    def test_arm_requires_platform_parent_private_session_and_read_only_fifo(self):
        for target, attribute, bad in [
                (darwin.sys, "platform", "linux"),
                (darwin.os, "getppid", lambda: 1),
                (darwin.os, "getpgid", lambda pid: 90),
                (darwin.os, "getsid", lambda pid: 90),
                (darwin.os, "fstat", lambda fd: types.SimpleNamespace(st_mode=stat.S_IFREG)),
                (darwin.fcntl, "fcntl", lambda *args: os.O_WRONLY)]:
            with self.subTest(attribute=attribute), mock.patch.object(target, attribute, bad):
                with self.assertRaises(RuntimeError):
                    darwin.arm(4, 90)
        darwin.os.fork.assert_not_called()

    def test_low_memory_never_forks(self):
        self.psutil.virtual_memory.return_value.available = 1
        with self.assertRaises(RuntimeError):
            darwin.arm(4, 90)
        darwin.os.fork.assert_not_called()

    def test_ready_guardian_and_all_worker_read_fds_close(self):
        self.assertEqual(darwin.arm(4, 90), 101)
        self.assertEqual(darwin.os.close.call_args_list,
                         [mock.call(6), mock.call(5), mock.call(4)])
        darwin.os.killpg.assert_not_called()

    def test_fork_failure_closes_fds_without_any_model_work(self):
        darwin.os.fork.side_effect = OSError("fake fork failure")
        with self.assertRaises(OSError):
            darwin.arm(4, 90)
        self.assertEqual(darwin.os.close.call_args_list,
                         [mock.call(5), mock.call(6), mock.call(4)])

    def test_missing_ack_or_changed_parent_blocks_before_model(self):
        for response in [([], [], []), ([5], [], [])]:
            darwin.select.select.return_value = response
            darwin.os.read.return_value = b""
            with self.assertRaisesRegex(RuntimeError, "NOT_READY"):
                darwin.arm(4, 90)
        darwin.select.select.return_value = ([5], [], [])
        darwin.os.read.return_value = b"R"
        darwin.os.getppid.side_effect = [90, 1]
        with self.assertRaisesRegex(RuntimeError, "NOT_READY"):
            darwin.arm(4, 90)

    def test_guardian_eof_during_native_work_contains_only_private_group(self):
        darwin.select.select.return_value = ([4], [], [])
        darwin.os.read.return_value = b""
        darwin._watch(4, 6, 100, 100, darwin.AVAILABLE_FLOOR)
        self.psutil.Process.assert_called_once_with(100)
        self.assertEqual(darwin.os.killpg.call_args_list,
                         [mock.call(100, darwin.signal.SIGTERM),
                          mock.call(100, darwin.signal.SIGKILL)])
        darwin.time.sleep.assert_called_once_with(3)

    def test_guardian_pressure_unknown_read_and_owned_pid_failure_all_contain(self):
        for kind in ["pressure", "read", "process"]:
            with self.subTest(kind=kind):
                self.psutil.virtual_memory.return_value.available = darwin.AVAILABLE_FLOOR + 1
                self.psutil.Process.side_effect = None
                darwin.os.read.side_effect = None
                darwin.os.killpg.reset_mock()
                darwin.select.select.return_value = ([], [], [])
                if kind == "pressure":
                    self.psutil.virtual_memory.side_effect = [
                        types.SimpleNamespace(available=darwin.AVAILABLE_FLOOR + 1, total=100),
                        types.SimpleNamespace(available=0, total=100)]
                elif kind == "read":
                    self.psutil.virtual_memory.side_effect = None
                    darwin.select.select.return_value = ([4], [], [])
                    darwin.os.read.side_effect = OSError("fake read fault")
                else:
                    self.psutil.virtual_memory.side_effect = None
                    self.psutil.Process.side_effect = RuntimeError("fake owned PID vanished")
                darwin._watch(4, 6, 100, 100, darwin.AVAILABLE_FLOOR)
                self.assertEqual([call.args[0] for call in darwin.os.killpg.call_args_list], [100, 100])

    def test_guardian_samples_only_owned_pid_and_stops_on_session_change(self):
        worker = self.psutil.Process.return_value
        worker.create_time.return_value = 1.5
        darwin.select.select.side_effect = [([], [], []), ([], [], [])]
        darwin.os.getpgid.side_effect = [100, 200]
        darwin._watch(4, 6, 100, 100, darwin.AVAILABLE_FLOOR)
        worker.memory_info.assert_called_once_with()
        worker.cpu_times.assert_called_once_with()
        self.psutil.Process.assert_called_once_with(100)

    def test_refuses_any_other_group(self):
        with self.assertRaisesRegex(RuntimeError, "ANOTHER_PROCESS_GROUP"):
            darwin._terminate_owned_group(999)
        darwin.os.killpg.assert_not_called()


class ContainmentRouting(unittest.TestCase):
    def setUp(self):
        self.libc = mock.Mock()
        self.libc.prctl.return_value = 0
        self.ctypes = mock.Mock()
        self.ctypes.CDLL.return_value = self.libc
        self.patchers = [
            mock.patch.dict("sys.modules", {"ctypes": self.ctypes}),
            mock.patch.object(voice.sys, "platform", "linux"),
            mock.patch.object(voice.os, "getppid", side_effect=[90, 90]),
            mock.patch.object(voice.time, "time", return_value=100),
            mock.patch.object(voice.signal, "signal"),
            mock.patch.object(voice.signal, "setitimer"),
            mock.patch.object(voice, "_darwin_helper"),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_legacy_linux_keeps_real_parent_death_abi_and_original_alarm(self):
        voice._arm_child_containment(160)
        self.ctypes.CDLL.assert_called_once_with(None, use_errno=True)
        self.libc.prctl.assert_called_once_with(1, voice.signal.SIGKILL)
        voice.signal.signal.assert_called_once_with(voice.signal.SIGALRM, voice.signal.SIG_DFL)
        voice.signal.setitimer.assert_called_once_with(voice.signal.ITIMER_REAL, 60)
        voice._darwin_helper.assert_not_called()

    def test_linux_orphan_prctl_failure_or_parent_change_never_arm_alarm(self):
        for parents, status in [([1], 0), ([90, 90], -1), ([90, 91], 0)]:
            with self.subTest(parents=parents, status=status):
                voice.os.getppid.side_effect = parents
                self.libc.prctl.return_value = status
                with self.assertRaisesRegex(voice.VoiceBlocked, "parent-death"):
                    voice._arm_child_containment(160)
        voice.signal.signal.assert_not_called()
        voice.signal.setitimer.assert_not_called()
        voice._darwin_helper.assert_not_called()

    def test_linux_expired_original_deadline_remains_blocked(self):
        with self.assertRaisesRegex(voice.VoiceBlocked, "deadline exhausted"):
            voice._arm_child_containment(100)
        self.libc.prctl.assert_called_once_with(1, voice.signal.SIGKILL)
        voice.signal.setitimer.assert_not_called()

    def test_darwin_without_local_cpu_scope_cannot_use_platform_extension(self):
        with mock.patch.object(voice.sys, "platform", "darwin"):
            with self.assertRaisesRegex(voice.VoiceBlocked, "supported Linux"):
                voice._arm_child_containment(160)
        voice._darwin_helper.assert_not_called()
        self.ctypes.CDLL.assert_not_called()
        voice.signal.setitimer.assert_not_called()

    def test_local_cpu_cannot_spoof_linux_or_borrow_allocation_deadline(self):
        with self.assertRaisesRegex(voice.VoiceBlocked, "supported Linux"):
            voice._arm_child_containment(None, lifeline_fd=4, expected_parent_pid=90, local_cpu=True)
        with mock.patch.object(voice.sys, "platform", "darwin"):
            with self.assertRaisesRegex(voice.VoiceBlocked, "borrow an allocation"):
                voice._arm_child_containment(160, lifeline_fd=4, expected_parent_pid=90, local_cpu=True)
        voice._darwin_helper.assert_not_called()
        self.ctypes.CDLL.assert_not_called()
        voice.signal.setitimer.assert_not_called()

    def test_explicit_darwin_local_cpu_delegates_exact_lifeline(self):
        helper = voice._darwin_helper.return_value
        helper.arm.return_value = 101
        with mock.patch.object(voice.sys, "platform", "darwin"):
            self.assertEqual(voice._arm_child_containment(None, lifeline_fd=4,
                expected_parent_pid=90, local_cpu=True), 101)
        helper.arm.assert_called_once_with(4, 90)
        self.ctypes.CDLL.assert_not_called()
        voice.signal.setitimer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
