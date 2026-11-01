"""Extract the real monolithic-server helper; never import/start the app or Redis."""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path
import unittest
from unittest.mock import Mock

SERVER = Path(__file__).resolve().parents[1] / "server.py"


def release_helper(client):
    tree = ast.parse(SERVER.read_text())
    node = next(node for node in tree.body
                if isinstance(node, ast.AsyncFunctionDef)
                and node.name == "_release_startup_maintenance_lock")
    logger = Mock()
    namespace = {"_redis_client": client, "_redis_text": lambda value: value,
                 "logger": logger}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SERVER), "exec"), namespace)
    return namespace[node.name], logger


class ScriptedRedis:
    def __init__(self, value=None, *, failure=None):
        self.value = value
        self.failure = failure
        self.calls = []

    async def get(self, key):
        # Reproduce expiry/reacquisition after old owner observes its token.
        self.calls.append(("GET", key))
        self.value = "new-owner"
        return "old-owner"

    async def delete(self, key):
        self.calls.append(("DELETE", key))
        self.value = None
        return 1

    async def eval(self, script, number_keys, key, token):
        self.calls.append(("EVAL", script, number_keys, key, token))
        if self.failure is not None:
            raise self.failure
        # The real Redis script semantics are independently exercised in a
        # scoped actual-Redis qualification. This double models one atomic call.
        if self.value == token:
            self.value = None
            return 1
        return 0


class StartupMaintenanceLockRelease(unittest.TestCase):
    def test_reacquired_owner_is_not_deleted_and_no_separate_commands(self):
        client = ScriptedRedis("new-owner")
        release, logger = release_helper(client)
        asyncio.run(release("fixture:lock", "old-owner"))
        self.assertEqual(client.value, "new-owner")
        self.assertEqual([call[0] for call in client.calls], ["EVAL"])
        logger.warning.assert_not_called()

    def test_owned_lock_uses_exact_one_key_and_opaque_token_argument(self):
        token = "owner:'opaque/Δ-token"
        client = ScriptedRedis(token)
        release, logger = release_helper(client)
        self.assertIsNone(asyncio.run(release("fixture:lock", token)))
        self.assertIsNone(client.value)
        self.assertEqual(len(client.calls), 1)
        _, script, number_keys, key, actual_token = client.calls[0]
        self.assertEqual((number_keys, key, actual_token), (1, "fixture:lock", token))
        self.assertNotIn(token, script)
        self.assertIn("redis.call('GET', KEYS[1]) == ARGV[1]", script)
        self.assertIn("redis.call('DEL', KEYS[1])", script)
        logger.warning.assert_not_called()

    def test_absent_lock_is_noop(self):
        client = ScriptedRedis()
        release, logger = release_helper(client)
        self.assertIsNone(asyncio.run(release("fixture:lock", "old-owner")))
        self.assertIsNone(client.value)
        self.assertEqual([call[0] for call in client.calls], ["EVAL"])
        logger.warning.assert_not_called()

    def test_redis_failure_logs_and_never_falls_back_to_delete(self):
        client = ScriptedRedis("new-owner", failure=RuntimeError("fixture ACL denial"))
        release, logger = release_helper(client)
        self.assertIsNone(asyncio.run(release("fixture:lock", "old-owner")))
        self.assertEqual(client.value, "new-owner")
        self.assertEqual([call[0] for call in client.calls], ["EVAL"])
        logger.warning.assert_called_once_with(
            "Failed to release startup maintenance lock cleanly.", exc_info=True)

    def test_cancellation_propagates_without_nonatomic_fallback(self):
        client = ScriptedRedis("new-owner", failure=asyncio.CancelledError())
        release, logger = release_helper(client)
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(release("fixture:lock", "old-owner"))
        self.assertEqual(client.value, "new-owner")
        self.assertEqual([call[0] for call in client.calls], ["EVAL"])
        logger.warning.assert_not_called()
