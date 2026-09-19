"""Execute the pinned upstream send method, not a reimplementation.

Set SMARTIR_BROADLINK_SOURCE to a separately acquired, hash-verified HA 2026.8.3
remote.py. No automatic downloads. Only async_send_command is compiled, because
unrelated learning methods need Python 3.14 syntax. Schema validation, code
extraction, Broadlink's exception class and the device are explicit substitutes.
Actual SmartIR climate/controller modules use tests.support's HA substitutes.
This is a native-method regression, not a native HA integration/startup test.
See tests/native_ha/README.md for both independent opt-in test commands.
"""

import asyncio
from base64 import b64encode
from collections import defaultdict
from collections.abc import Iterable
from itertools import product
import logging
import os
from pathlib import Path
import textwrap
from types import MethodType, SimpleNamespace
from typing import Any
import unittest
from unittest.mock import AsyncMock, Mock

from tests.native_ha.pinned_source import verify_source

PACKET = b"\x26\x00\x04\x00\x00\x01\x0d\x05"
COMMAND = b64encode(PACKET).decode("ascii")
LOGGER = logging.getLogger("smartir.tests.pinned_broadlink")


class BroadlinkException(Exception):
    """Boundary stand-in, not an installed Broadlink SDK."""


def load_send_method(path):
    source = verify_source(Path(path).read_bytes())
    start = source.index("    async def async_send_command(")
    end = source.index(
        "\n    @override\n    async def async_learn_command(", start
    )
    namespace = {
        "asyncio": asyncio, "Iterable": Iterable, "Any": Any, "product": product,
        "ATTR_COMMAND": "command", "ATTR_DEVICE": "device",
        "ATTR_NUM_REPEATS": "num_repeats", "ATTR_DELAY_SECS": "delay_secs",
        "RM_DOMAIN": "remote", "SERVICE_SEND_COMMAND": "send_command",
        "SERVICE_SEND_SCHEMA": lambda data: data, "_LOGGER": LOGGER,
        "BroadlinkException": BroadlinkException, "FLAG_SAVE_DELAY": 15,
    }
    exec(compile(textwrap.dedent(source[start:end]), str(path), "exec"), namespace)
    return namespace["async_send_command"]


class NativeBroadlinkMethod(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("SMARTIR_BROADLINK_SOURCE")
        if path is None:
            raise unittest.SkipTest(
                "Set SMARTIR_BROADLINK_SOURCE to explicitly acquired HA 2026.8.3 "
                "remote.py; see tests/native_ha/README.md"
            )
        cls.send_method = staticmethod(load_send_method(path))

    def setUp(self):
        # Do not subclass ClimateTransactions and duplicate all its tests.
        from tests import test_climate
        from tests.support import settings

        self.settings = settings
        fixture = test_climate.ClimateTransactions(methodName="runTest")
        self.entity = fixture.make_entity()
        self.hass = fixture.hass
        self.entity._commands["cool"]["auto"]["18"] = COMMAND
        self.before = settings(self.entity)
        self.remote = SimpleNamespace(
            _device=SimpleNamespace(
                api=SimpleNamespace(send_data=Mock()), async_request=AsyncMock()
            ),
            _attr_is_on=True, _storage_loaded=True,
            _async_load_storage=AsyncMock(),
            _extract_codes=Mock(return_value=[[PACKET]]),
            _flags=defaultdict(int), _get_flags=Mock(return_value={}),
            _flag_storage=SimpleNamespace(async_delay_save=Mock()),
            entity_id="remote.test",
        )
        self.remote.async_send_command = MethodType(self.send_method, self.remote)

        async def dispatch(domain, service, data, *, blocking=False):
            self.assertEqual((domain, service), ("remote", "send_command"))
            self.assertTrue(blocking)
            self.assertEqual(data["entity_id"], "remote.test")
            self.assertEqual(data["command"], ["b64:" + COMMAND])
            return await self.remote.async_send_command(
                data["command"], num_repeats=1, delay_secs=data["delay_secs"]
            )

        self.hass.services.async_call = AsyncMock(side_effect=dispatch)

    def assert_committed(self):
        self.assertEqual(self.entity.hvac_mode, "cool")
        self.assertEqual(self.entity.last_on_operation, "cool")
        self.assertEqual(self.hass.writes, [self.settings(self.entity)])

    async def test_off_remote_returns_normally_and_smartir_commits(self):
        self.remote._attr_is_on = False
        with self.assertLogs(LOGGER, level="WARNING") as logs:
            await self.entity.async_set_hvac_mode("cool")
        self.assertIn("entity is turned off", logs.output[0])
        self.remote._device.async_request.assert_not_awaited()
        self.remote._extract_codes.assert_not_called()
        self.remote._flag_storage.async_delay_save.assert_not_called()
        self.assert_committed()

    async def test_native_broadlink_error_is_swallowed_and_smartir_commits(self):
        self.remote._device.async_request.side_effect = BroadlinkException("rejected")
        with self.assertLogs(LOGGER, level="ERROR") as logs:
            await self.entity.async_set_hvac_mode("cool")
        self.assertIn("rejected", logs.output[0])
        self.remote._device.async_request.assert_awaited_once()
        self.remote._flag_storage.async_delay_save.assert_not_called()
        self.assert_committed()

    async def test_native_os_error_is_swallowed_and_smartir_commits(self):
        self.remote._device.async_request.side_effect = OSError("unreachable")
        with self.assertLogs(LOGGER, level="ERROR") as logs:
            await self.entity.async_set_hvac_mode("cool")
        self.assertIn("unreachable", logs.output[0])
        self.remote._device.async_request.assert_awaited_once()
        self.remote._flag_storage.async_delay_save.assert_not_called()
        self.assert_committed()

    async def test_extraction_error_surfaces_and_preserves_smartir_state(self):
        from tests.support import HomeAssistantError

        error = ValueError("Invalid code from native extraction")
        self.remote._extract_codes.side_effect = error
        with self.assertLogs(LOGGER, level="ERROR"):
            with self.assertRaises(HomeAssistantError) as raised:
                await self.entity.async_set_hvac_mode("cool")
        self.assertIs(raised.exception.__cause__, error)
        self.assertEqual(self.settings(self.entity), self.before)
        self.assertEqual(self.hass.writes, [])
        self.remote._device.async_request.assert_not_awaited()
        self.remote._flag_storage.async_delay_save.assert_not_called()

    async def test_success_waits_for_native_request_before_commit(self):
        started = asyncio.Event()
        release = asyncio.Event()

        async def request(*args):
            started.set()
            await release.wait()

        self.remote._device.async_request.side_effect = request
        task = asyncio.create_task(self.entity.async_set_hvac_mode("cool"))
        try:
            await asyncio.wait_for(started.wait(), 1)
            self.assertFalse(task.done())
            self.assertEqual(self.settings(self.entity), self.before)
            self.assertEqual(self.hass.writes, [])
            release.set()
            await asyncio.wait_for(task, 1)
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.remote._extract_codes.assert_called_once_with(
            ["b64:" + COMMAND], None
        )
        self.remote._device.async_request.assert_awaited_once_with(
            self.remote._device.api.send_data, PACKET
        )
        self.remote._flag_storage.async_delay_save.assert_called_once_with(
            self.remote._get_flags, 15
        )
        self.assert_committed()
