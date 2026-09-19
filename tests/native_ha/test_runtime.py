"""Opt-in checks using HA's real ServiceRegistry, event bus and state machine.

Run separately on Linux with Python >=3.14.2 and homeassistant==2026.8.3.
No tests.support imports or fake HA modules. A package shell bypasses SmartIR's
__init__.py (its distutils/startup issue is tracked separately in #1504).
These are direct entity/component boundary tests, not a full startup shim:
no integration setup, discovery, EntityComponent lifecycle, restore persistence,
native remote entity-service schema, Broadlink SDK or hardware is exercised.
"""

import asyncio
from base64 import b64encode
import importlib
from importlib.metadata import version
import logging
import os
from pathlib import Path
import shutil
import sys
from types import ModuleType, SimpleNamespace
import unittest
from uuid import uuid4

ENABLED = os.environ.get("SMARTIR_NATIVE_HA") == "1"
ROOT = Path(__file__).resolve().parents[2]
COMMAND = b64encode(b"\x26\x00\x04\x00\x00\x01\x0d\x05").decode("ascii")

if ENABLED:
    if sys.platform != "linux" or sys.version_info < (3, 14, 2):
        raise RuntimeError("Native HA tests require Linux and Python >=3.14.2")
    if version("homeassistant") != "2026.8.3":
        raise RuntimeError("Native HA tests require homeassistant==2026.8.3")

    import voluptuous as vol

    from homeassistant.core import HomeAssistant, State
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.helpers import frame, restore_state
    from homeassistant.helpers.event import async_track_state_change_event
    from homeassistant.util import dt as dt_util
    from homeassistant.util.unit_system import METRIC_SYSTEM

    SOURCE = ROOT / "custom_components" / "smartir"
    PACKAGE_NAME = "smartir_native_ha_test"
    package = ModuleType(PACKAGE_NAME)
    package.__path__ = [str(SOURCE)]
    package.COMPONENT_ABS_DIR = str(SOURCE)
    # Base64 does not invoke Helper. Startup/downloads/Pronto are out of scope.
    package.Helper = SimpleNamespace()
    sys.modules[PACKAGE_NAME] = package
    climate = importlib.import_module(f"{PACKAGE_NAME}.climate")


@unittest.skipUnless(
    ENABLED, "Set SMARTIR_NATIVE_HA=1; see tests/native_ha/README.md"
)
class NativeRuntimeSmoke(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Only test-owned files in the repository, never a system temp directory.
        self.config_dir = ROOT / f".smartir-native-ha-{uuid4().hex}"
        self.config_dir.mkdir()
        self.addCleanup(shutil.rmtree, self.config_dir)
        self.hass = HomeAssistant(str(self.config_dir))
        frame.async_setup(self.hass)
        self.hass.config.units = METRIC_SYSTEM
        self.addAsyncCleanup(self.hass.async_stop, force=True)
        self.entity = climate.SmartIRClimate(self.hass, {
            "name": "Native smoke", "device_code": 1,
            "controller_data": "remote.synthetic", "delay": 0,
        }, {
            "manufacturer": "Test", "supportedModels": ["Synthetic"],
            "supportedController": "Broadlink", "commandsEncoding": "Base64",
            "minTemperature": 18, "maxTemperature": 25, "precision": 1,
            "operationModes": ["cool"], "fanModes": ["auto"],
            "commands": {"off": COMMAND, "cool": {"auto": {"18": COMMAND}}},
        })
        self.entity.entity_id = "climate.native_smoke"
        # Direct entities are deliberate here; HA warns about no EntityComponent.
        with self.assertLogs("homeassistant.helpers.entity", logging.WARNING):
            self.entity.async_write_ha_state()

    def current_state(self):
        state = self.hass.states.get(self.entity.entity_id)
        self.assertIsNotNone(state)
        return state

    async def test_blocking_service_completion_precedes_real_state_write(self):
        started = asyncio.Event()
        release = asyncio.Event()
        received = []

        async def send(call):
            received.append(dict(call.data))
            started.set()
            await release.wait()

        self.hass.services.async_register("remote", "send_command", send)
        task = asyncio.create_task(self.entity.async_set_hvac_mode("cool"))
        try:
            await asyncio.wait_for(started.wait(), 5)
            self.assertFalse(task.done())
            self.assertEqual(self.current_state().state, "off")
            release.set()
            await asyncio.wait_for(task, 5)
            await self.hass.async_block_till_done()
        finally:
            release.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(received, [{
            "entity_id": "remote.synthetic", "command": ["b64:" + COMMAND],
            "delay_secs": 0,
        }])
        state = self.current_state()
        self.assertEqual(state.state, "cool")
        self.assertEqual(state.attributes["temperature"], 18)
        self.assertEqual(state.attributes["last_on_operation"], "cool")

    async def test_real_service_failure_preserves_state_and_error_identity(self):
        error = HomeAssistantError("synthetic service failure")

        async def send(call):
            await asyncio.sleep(0)
            raise error

        self.hass.services.async_register("remote", "send_command", send)
        before = self.current_state()
        with self.assertRaises(HomeAssistantError) as raised:
            await self.entity.async_set_hvac_mode("cool")
        self.assertIs(raised.exception, error)
        self.assertIs(self.current_state(), before)
        self.assertEqual(self.entity.hvac_mode, "off")
        self.assertIsNone(self.entity.last_on_operation)

    async def test_real_registry_schema_rejection_never_calls_handler(self):
        calls = []

        async def send(call):
            calls.append(call)

        def reject(data):
            raise vol.Invalid("synthetic registry schema rejection")

        self.hass.services.async_register(
            "remote", "send_command", send, schema=reject
        )
        before = self.current_state()
        with self.assertRaises(HomeAssistantError):
            await self.entity.async_set_hvac_mode("cool")
        self.assertEqual(calls, [])
        self.assertIs(self.current_state(), before)
        self.assertEqual(self.entity.hvac_mode, "off")

    async def test_real_service_cancellation_preserves_state_and_releases_lock(self):
        started = asyncio.Event()
        cancelled = asyncio.Event()
        calls = []

        async def send(call):
            calls.append(call)
            if len(calls) == 1:
                started.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    cancelled.set()
                    raise

        self.hass.services.async_register("remote", "send_command", send)
        before = self.current_state()
        task = asyncio.create_task(self.entity.async_set_hvac_mode("cool"))
        try:
            await asyncio.wait_for(started.wait(), 5)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(cancelled.is_set())
            self.assertIs(self.current_state(), before)
            self.assertEqual(self.entity.hvac_mode, "off")
            self.assertIsNone(self.entity.last_on_operation)
            self.assertFalse(self.entity._temp_lock.locked())
            await asyncio.wait_for(self.entity.async_set_hvac_mode("cool"), 5)
            self.assertEqual(len(calls), 2)
            self.assertEqual(self.current_state().state, "cool")
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_real_restore_cache_hydrates_settings_without_sending(self):
        calls = []

        async def send(call):
            calls.append(call)

        self.hass.services.async_register("remote", "send_command", send)
        restored = State(self.entity.entity_id, "off", {
            "temperature": 23, "fan_mode": "auto", "last_on_operation": "cool",
        })
        cache = restore_state.async_get(self.hass)
        cache.last_states[self.entity.entity_id] = restore_state.StoredState(
            restored, None, dt_util.utcnow()
        )
        self.assertIs(await self.entity.async_get_last_state(), restored)
        await self.entity.async_added_to_hass()
        self.assertEqual(self.entity.hvac_mode, "off")
        self.assertEqual(self.entity.target_temperature, 23)
        self.assertEqual(self.entity.fan_mode, "auto")
        self.assertEqual(self.entity.last_on_operation, "cool")
        self.assertEqual(calls, [])
        self.entity.async_write_ha_state()
        state = self.current_state()
        self.assertEqual(state.state, "off")
        self.assertEqual(state.attributes["temperature"], 23)
        self.assertEqual(state.attributes["last_on_operation"], "cool")

    async def test_real_state_events_schedule_sensor_callback_and_publish_state(self):
        remove = async_track_state_change_event(
            self.hass, "sensor.synthetic_temperature",
            self.entity._async_temp_sensor_changed,
        )
        self.addCleanup(remove)
        self.hass.states.async_set("sensor.synthetic_temperature", "22.5")
        await self.hass.async_block_till_done()
        self.assertEqual(self.entity.current_temperature, 22.5)
        self.assertEqual(self.current_state().attributes["current_temperature"], 22.5)
        self.hass.states.async_remove("sensor.synthetic_temperature")
        await self.hass.async_block_till_done()
        self.assertEqual(self.entity.current_temperature, 22.5)
        self.assertEqual(self.current_state().state, "off")
