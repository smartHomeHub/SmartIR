"""Actual-source transaction regressions with synthetic codes and fake services."""

import asyncio
from base64 import b64decode, b64encode
import unittest
from collections import deque
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import requests

from tests.support import (
    HomeAssistantError, ServiceValidationError, load_source, settings,
)

climate, controller = load_source()


def encoded(label):
    """Synthetic bytes, never a captured appliance command."""
    return b64encode(label.encode()).decode()


class Services:
    """Separate service submission from handler completion and surfaced errors."""

    def __init__(self):
        self.calls = []
        self.started = asyncio.Queue()
        self.outcomes = deque()
        self.pending = []

    async def async_call(self, domain, service, data, blocking=False):
        call = SimpleNamespace(domain=domain, service=service, data=data,
                               blocking=blocking, completed=False)
        self.calls.append(call)
        self.started.put_nowait(call)
        outcome = self.outcomes.popleft() if self.outcomes else None

        async def run():
            if isinstance(outcome, asyncio.Future):
                await outcome
            elif isinstance(outcome, Exception):
                raise outcome
            call.completed = True

        if blocking:
            await run()
        else:
            self.pending.append(asyncio.create_task(run()))


def device_data(swing=False, preamble=False):
    commands = {"off": encoded("off-code")}
    for mode in ("cool", "heat"):
        commands[mode] = {}
        for fan in ("auto", "high"):
            if swing:
                commands[mode][fan] = {
                    position: {str(temp): encoded(f"{mode}-{fan}-{position}-{temp}")
                               for temp in range(18, 26)}
                    for position in ("off", "auto")
                }
            else:
                commands[mode][fan] = {
                    str(temp): encoded(f"{mode}-{fan}-{temp}") for temp in range(18, 26)
                }
    if preamble:
        commands["on"] = encoded("on-code")
    return {
        "manufacturer": "Test", "supportedModels": ["Synthetic"],
        "supportedController": "Broadlink", "commandsEncoding": "Base64",
        "minTemperature": 18, "maxTemperature": 25, "precision": 1,
        "operationModes": ["cool", "heat"], "fanModes": ["auto", "high"],
        "swingModes": ["off", "auto"] if swing else None, "commands": commands,
    }


class ClimateTransactions(unittest.IsolatedAsyncioTestCase):
    def make_entity(self, *, swing=False, preamble=False, **config):
        self.hass = SimpleNamespace(
            services=Services(), writes=[], last_state=None, listeners={},
            states=SimpleNamespace(get=lambda entity_id: None),
            config=SimpleNamespace(units=SimpleNamespace(temperature_unit="C")),
        )
        self.entity = climate.SmartIRClimate(self.hass, {
            "name": "Test", "device_code": 1, "controller_data": "remote.test",
            "delay": 0, **config,
        }, device_data(swing, preamble))
        return self.entity

    def gate(self):
        future = asyncio.get_running_loop().create_future()
        self.hass.services.outcomes.append(future)
        return future

    async def start(self, request):
        task = asyncio.create_task(request)
        self.addAsyncCleanup(self.cancel_task, task)
        await asyncio.wait_for(self.hass.services.started.get(), 1)
        return task

    async def cancel_task(self, task):
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def asyncTearDown(self):
        if hasattr(self, "hass"):
            for task in self.hass.services.pending:
                await self.cancel_task(task)

    def codes(self):
        return [["b64:" + b64decode(code[4:]).decode() for code in call.data["command"]]
                for call in self.hass.services.calls]

    async def test_waits_for_handler_completion_before_state_commit(self):
        entity = self.make_entity()
        before = settings(entity)
        gate = self.gate()
        task = await self.start(entity.async_set_hvac_mode("cool"))
        self.assertFalse(task.done())
        self.assertEqual(settings(entity), before)
        self.assertEqual(self.hass.writes, [])
        self.assertEqual(self.codes(), [["b64:cool-auto-18"]])
        self.assertTrue(self.hass.services.calls[0].blocking)
        gate.set_result(None)
        await task
        self.assertEqual(entity.hvac_mode, "cool")
        self.assertEqual(entity.last_on_operation, "cool")
        self.assertEqual(self.hass.writes, [settings(entity)])

    async def test_immediate_failures_preserve_every_setting(self):
        entity = self.make_entity(swing=True)
        await entity.async_set_hvac_mode("cool")
        entity._on_by_remote = True
        before = settings(entity)
        writes = len(self.hass.writes)
        for method, args in (
            (entity.async_set_hvac_mode, {"hvac_mode": "heat"}),
            (entity.async_set_temperature, {"temperature": 22, "hvac_mode": "heat"}),
            (entity.async_set_fan_mode, {"fan_mode": "high"}),
            (entity.async_set_swing_mode, {"swing_mode": "auto"}),
            (entity.async_turn_off, {}),
        ):
            with self.subTest(method=method.__name__):
                self.hass.services.outcomes.append(RuntimeError("transport failed"))
                with self.assertRaises(HomeAssistantError) as result:
                    await method(**args)
                self.assertIsInstance(result.exception.__cause__, RuntimeError)
                self.assertEqual(settings(entity), before)
                self.assertEqual(len(self.hass.writes), writes)

    async def test_deferred_failure_releases_lock_for_next_request(self):
        entity = self.make_entity()
        gate = self.gate()
        first = await self.start(entity.async_set_hvac_mode("heat"))
        second = asyncio.create_task(entity.async_set_hvac_mode("cool"))
        self.addAsyncCleanup(self.cancel_task, second)
        gate.set_exception(RuntimeError("deferred transport failure"))
        with self.assertRaises(HomeAssistantError):
            await first
        await asyncio.wait_for(second, 1)
        self.assertEqual(self.codes(), [["b64:heat-auto-18"], ["b64:cool-auto-18"]])
        self.assertEqual(entity.last_on_operation, "cool")
        self.assertEqual(self.hass.writes, [settings(entity)])

    async def test_ha_error_is_not_hidden_or_replaced(self):
        entity = self.make_entity()
        error = HomeAssistantError("remote unavailable")
        self.hass.services.outcomes.append(error)
        with self.assertRaises(HomeAssistantError) as result:
            await entity.async_turn_on()
        self.assertIs(result.exception, error)
        self.assertEqual(entity.hvac_mode, "off")

    async def test_request_after_failed_change_uses_committed_settings(self):
        entity = self.make_entity()
        await entity.async_set_hvac_mode("cool")
        self.hass.services.started.get_nowait()
        gate = self.gate()
        failed = await self.start(entity.async_set_temperature(
            temperature=22, hvac_mode="heat"))
        queued = asyncio.create_task(entity.async_set_fan_mode("high"))
        self.addAsyncCleanup(self.cancel_task, queued)
        await asyncio.sleep(0)
        gate.set_exception(RuntimeError("heat settings failed"))
        with self.assertRaises(HomeAssistantError):
            await failed
        await asyncio.wait_for(queued, 1)
        self.assertEqual(self.codes(), [
            ["b64:cool-auto-18"], ["b64:heat-auto-22"], ["b64:cool-high-18"],
        ])
        self.assertEqual(settings(entity), ("cool", 18, "high", None, "cool", False))

    async def test_concurrent_mode_temperature_fan_and_swing_keep_request_order(self):
        entity = self.make_entity(swing=True)
        gate = self.gate()
        first = await self.start(entity.async_set_hvac_mode("cool"))
        tasks = [first]
        for request in (
            entity.async_set_temperature(temperature=22, hvac_mode="heat"),
            entity.async_set_fan_mode("high"),
            entity.async_set_temperature(temperature=23),
            entity.async_set_swing_mode("auto"),
        ):
            task = asyncio.create_task(request)
            self.addAsyncCleanup(self.cancel_task, task)
            tasks.append(task)
            await asyncio.sleep(0)
        self.assertEqual(entity.hvac_mode, "off")
        self.assertEqual(len(self.hass.services.calls), 1)
        gate.set_result(None)
        await asyncio.wait_for(asyncio.gather(*tasks), 1)
        self.assertEqual(self.codes(), [
            ["b64:cool-auto-off-18"], ["b64:heat-auto-off-22"],
            ["b64:heat-high-off-22"], ["b64:heat-high-off-23"],
            ["b64:heat-high-auto-23"],
        ])
        self.assertEqual([state[:4] for state in self.hass.writes], [
            ("cool", 18, "auto", "off"), ("heat", 22, "auto", "off"),
            ("heat", 22, "high", "off"), ("heat", 23, "high", "off"),
            ("heat", 23, "high", "auto"),
        ])

    async def test_off_settings_are_remembered_without_sending(self):
        entity = self.make_entity(swing=True)
        await entity.async_set_temperature(temperature=22)
        await entity.async_set_fan_mode("high")
        await entity.async_set_swing_mode("auto")
        self.assertEqual(self.codes(), [])
        self.assertEqual(settings(entity), ("off", 22, "high", "auto", None, False))
        await entity.async_turn_on()
        self.assertEqual(self.codes(), [["b64:cool-high-auto-22"]])

    async def test_combined_off_and_temperature_sends_only_off(self):
        entity = self.make_entity(preamble=True)
        await entity.async_set_temperature(temperature=22, hvac_mode="off")
        self.assertEqual(self.codes(), [["b64:off-code"]])
        self.assertEqual(entity.target_temperature, 22)
        self.assertIsNone(entity.last_on_operation)

    async def test_turn_on_uses_last_successful_queued_mode_and_repeats(self):
        entity = self.make_entity()
        gate = self.gate()
        first = await self.start(entity.async_set_hvac_mode("heat"))
        second = asyncio.create_task(entity.async_turn_on())
        self.addAsyncCleanup(self.cancel_task, second)
        await asyncio.sleep(0)
        gate.set_result(None)
        await asyncio.wait_for(asyncio.gather(first, second), 1)
        self.assertEqual(self.codes(), [["b64:heat-auto-18"], ["b64:heat-auto-18"]])
        await entity.async_turn_off()
        self.assertEqual(entity.last_on_operation, "heat")

    async def test_preamble_and_lists_await_completion_in_order(self):
        entity = self.make_entity(preamble=True)
        entity._commands["on"] = [encoded("on-one"), encoded("on-two")]
        entity._commands["cool"]["auto"]["18"] = [encoded("setting-one"), encoded("setting-two")]
        first_gate, second_gate = self.gate(), self.gate()
        task = await self.start(entity.async_turn_on())
        self.assertEqual(self.codes(), [["b64:on-one", "b64:on-two"]])
        self.assertEqual(self.hass.writes, [])
        first_gate.set_result(None)
        await asyncio.wait_for(self.hass.services.started.get(), 1)
        self.assertTrue(self.hass.services.calls[0].completed)
        self.assertFalse(task.done())
        self.assertEqual(self.hass.writes, [])
        second_gate.set_result(None)
        await task
        self.assertEqual(self.codes()[1], ["b64:setting-one", "b64:setting-two"])
        self.assertEqual(len(self.hass.writes), 1)

    async def test_partial_preamble_failure_retains_committed_state(self):
        entity = self.make_entity(preamble=True)
        before = settings(entity)
        self.hass.services.outcomes.extend([None, RuntimeError("settings failed")])
        with self.assertRaises(HomeAssistantError):
            await entity.async_set_temperature(temperature=22, hvac_mode="heat")
        self.assertTrue(self.hass.services.calls[0].completed)
        self.assertFalse(self.hass.services.calls[1].completed)
        self.assertEqual(settings(entity), before)
        self.assertEqual(self.hass.writes, [])

    async def test_failed_preamble_does_not_send_settings(self):
        entity = self.make_entity(preamble=True)
        self.hass.services.outcomes.append(RuntimeError("preamble failed"))
        with self.assertRaises(HomeAssistantError):
            await entity.async_turn_on()
        self.assertEqual(self.codes(), [["b64:on-code"]])
        self.assertEqual(self.hass.writes, [])

    async def test_preamble_keeps_configured_delay(self):
        entity = self.make_entity(preamble=True, delay=0.125)
        with patch.object(climate.asyncio, "sleep", new_callable=AsyncMock) as sleep:
            await entity.async_turn_on()
        sleep.assert_awaited_once_with(0.125)
        self.assertEqual(self.codes(), [["b64:on-code"], ["b64:cool-auto-18"]])

    async def test_missing_and_invalid_commands_fail_before_preamble(self):
        entity = self.make_entity(preamble=True)
        before = settings(entity)
        for leaf in (None, "", [], ["valid", None], {}, 42):
            with self.subTest(leaf=leaf):
                entity._commands["cool"]["auto"]["18"] = leaf
                with self.assertRaises(ServiceValidationError):
                    await entity.async_turn_on()
        for branch in ({}, None, "not-a-lookup"):
            with self.subTest(branch=branch):
                entity._commands["cool"] = branch
                with self.assertRaises(ServiceValidationError):
                    await entity.async_turn_on()
        self.assertEqual(self.codes(), [])
        self.assertEqual(settings(entity), before)
        self.assertEqual(self.hass.writes, [])

    async def test_invalid_preamble_and_off_code_fail_without_sending(self):
        entity = self.make_entity(preamble=True)
        entity._commands["on"] = None
        with self.assertRaises(ServiceValidationError):
            await entity.async_turn_on()
        del entity._commands["off"]
        with self.assertRaises(ServiceValidationError):
            await entity.async_turn_off()
        self.assertEqual(self.codes(), [])

    async def test_invalid_requested_settings_are_reported(self):
        entity = self.make_entity()
        before = settings(entity)
        for method, args in (
            (entity.async_set_hvac_mode, {"hvac_mode": "invalid"}),
            (entity.async_set_fan_mode, {"fan_mode": "invalid"}),
            (entity.async_set_swing_mode, {"swing_mode": "invalid"}),
            (entity.async_set_temperature, {"temperature": 26}),
            (entity.async_set_temperature, {"temperature": float("nan")}),
        ):
            with self.subTest(method=method.__name__):
                with self.assertRaises(ServiceValidationError):
                    await method(**args)
        self.assertEqual(self.codes(), [])
        self.assertEqual(settings(entity), before)

    async def test_cancellation_retains_state_and_releases_lock(self):
        entity = self.make_entity()
        self.gate()
        task = await self.start(entity.async_turn_on())
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(entity.hvac_mode, "off")
        self.assertEqual(self.hass.writes, [])
        await asyncio.wait_for(entity.async_set_hvac_mode("heat"), 1)
        self.assertEqual(entity.hvac_mode, "heat")

    async def test_restore_preserves_settings_without_transmission(self):
        entity = self.make_entity(swing=True)
        self.hass.last_state = SimpleNamespace(state="off", attributes={
            "temperature": 23, "fan_mode": "high", "swing_mode": "auto",
            "last_on_operation": "heat",
        })
        await entity.async_added_to_hass()
        self.assertEqual(settings(entity), ("off", 23, "high", "auto", "heat", False))
        self.assertEqual(self.codes(), [])
        await entity.async_turn_on()
        self.assertEqual(self.codes(), [["b64:heat-high-auto-23"]])

    async def test_restore_active_state_does_not_send(self):
        entity = self.make_entity()
        self.hass.last_state = SimpleNamespace(state="heat", attributes={
            "temperature": 23, "fan_mode": "high", "last_on_operation": "heat",
        })
        await entity.async_added_to_hass()
        self.assertEqual(settings(entity), ("heat", 23, "high", None, "heat", False))
        self.assertEqual(self.codes(), [])

    async def test_off_does_not_require_a_restored_temperature(self):
        entity = self.make_entity()
        self.hass.last_state = SimpleNamespace(state="heat", attributes={
            "temperature": None, "fan_mode": "auto", "last_on_operation": "heat",
        })
        await entity.async_added_to_hass()
        await entity.async_turn_off()
        self.assertEqual(self.codes(), [["b64:off-code"]])
        with self.assertRaises(ServiceValidationError):
            await entity.async_turn_on()
        self.assertEqual(entity.hvac_mode, "off")

    async def test_temperature_rounding_is_unchanged(self):
        for precision, requested, expected in ((1, 21.6, 22), (0.1, 21.64, 21.6)):
            with self.subTest(precision=precision):
                entity = self.make_entity()
                entity._precision = precision
                entity._commands["cool"]["auto"][str(expected)] = encoded("rounded-code")
                await entity.async_set_temperature(temperature=requested, hvac_mode="cool")
                self.assertEqual(entity.target_temperature, expected)
                self.assertEqual(self.codes(), [["b64:rounded-code"]])

    async def test_power_on_restore_policy_remains_unchanged(self):
        for restore, expected in ((False, "on"), (True, "heat")):
            with self.subTest(restore=restore):
                entity = self.make_entity(power_sensor_restore_state=restore)
                entity._last_on_operation = "heat"
                await entity._async_power_sensor_changed(SimpleNamespace(data={
                    "entity_id": "binary_sensor.test",
                    "old_state": SimpleNamespace(state="off"),
                    "new_state": SimpleNamespace(state="on"),
                }))
                self.assertEqual(entity.hvac_mode, expected)
                self.assertTrue(entity._on_by_remote)
                self.assertEqual(self.codes(), [])

    async def test_power_observation_is_applied_after_inflight_command(self):
        entity = self.make_entity(power_sensor="binary_sensor.test")
        await entity.async_added_to_hass()
        gate = self.gate()
        send = await self.start(entity.async_turn_on())
        observed = asyncio.create_task(self.hass.listeners["binary_sensor.test"](
            SimpleNamespace(data={
                "entity_id": "binary_sensor.test",
                "old_state": SimpleNamespace(state="on"),
                "new_state": SimpleNamespace(state="off"),
            })))
        self.addAsyncCleanup(self.cancel_task, observed)
        await asyncio.sleep(0)
        self.assertEqual(self.hass.writes, [])
        gate.set_result(None)
        await asyncio.wait_for(asyncio.gather(send, observed), 1)
        self.assertEqual([state[0] for state in self.hass.writes], ["cool", "off"])
        self.assertEqual(entity.last_on_operation, "cool")

    async def test_temperature_and_humidity_sensors_do_not_publish_proposed_settings(self):
        entity = self.make_entity(temperature_sensor="sensor.temp",
                                  humidity_sensor="sensor.humidity")
        await entity.async_added_to_hass()
        gate = self.gate()
        task = await self.start(entity.async_turn_on())
        for sensor, value in (("sensor.temp", "21.5"), ("sensor.humidity", "45")):
            await self.hass.listeners[sensor](
                SimpleNamespace(data={"new_state": SimpleNamespace(state=value)}))
        self.assertEqual(entity.current_temperature, 21.5)
        self.assertEqual(entity.current_humidity, 45)
        self.assertTrue(all(state[0] == "off" for state in self.hass.writes))
        gate.set_result(None)
        await task

    async def test_lookin_http_failure_does_not_commit_climate_settings(self):
        entity = self.make_entity()
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("HTTP 500")
        self.hass.async_add_executor_job = AsyncMock(return_value=response)
        entity._controller = controller.get_controller(
            self.hass, "LOOKin", "Raw", "test.local", 0)
        before = settings(entity)
        with self.assertRaises(HomeAssistantError) as result:
            await entity.async_set_hvac_mode("heat")
        self.assertIsInstance(result.exception.__cause__, requests.HTTPError)
        self.assertEqual(settings(entity), before)
        self.assertEqual(self.hass.writes, [])


class Controllers(unittest.IsolatedAsyncioTestCase):
    async def test_service_controllers_preserve_payload_and_wait_for_errors(self):
        cases = [
            ("Broadlink", "Base64", ["b25l", "dHdv"], "remote", "send_command",
             {"entity_id": "target", "command": ["b64:b25l", "b64:dHdv"], "delay_secs": 0.5}),
            ("Broadlink", "Hex", "0102", "remote", "send_command",
             {"entity_id": "target", "command": ["b64:AQI="], "delay_secs": 0.5}),
            ("Xiaomi", "Raw", "raw-code", "remote", "send_command",
             {"entity_id": "target", "command": "raw:raw-code"}),
            ("MQTT", "Raw", "raw-code", "mqtt", "publish",
             {"topic": "target", "payload": "raw-code"}),
            ("ESPHome", "Raw", "[1, -2]", "esphome", "target",
             {"command": [1, -2]}),
        ]
        for kind, encoding, command, domain, service, payload in cases:
            for fails in (False, True):
                with self.subTest(controller=kind, encoding=encoding, fails=fails):
                    services = Services()
                    gate = asyncio.get_running_loop().create_future()
                    services.outcomes.append(gate)
                    instance = controller.get_controller(
                        SimpleNamespace(services=services), kind, encoding, "target", 0.5)
                    task = asyncio.create_task(instance.send(command))
                    try:
                        call = await asyncio.wait_for(services.started.get(), 1)
                        self.assertEqual((call.domain, call.service, call.data),
                                         (domain, service, payload))
                        self.assertTrue(call.blocking)
                        self.assertFalse(task.done())
                        if fails:
                            error = HomeAssistantError("deferred failure")
                            gate.set_exception(error)
                            with self.assertRaises(HomeAssistantError) as result:
                                await task
                            self.assertIs(result.exception, error)
                        else:
                            gate.set_result(None)
                            await task
                            self.assertTrue(call.completed)
                    finally:
                        task.cancel()
                        for pending in services.pending:
                            pending.cancel()
                        await asyncio.gather(task, *services.pending, return_exceptions=True)

    async def test_lookin_checks_http_status_and_preserves_url(self):
        for failure in (None, requests.HTTPError("HTTP 500")):
            with self.subTest(failure=failure):
                response = Mock()
                response.raise_for_status.side_effect = failure
                hass = SimpleNamespace(async_add_executor_job=AsyncMock(return_value=response))
                instance = controller.get_controller(hass, "LOOKin", "Pronto", "test.local", 0.5)
                command = "0000 006D 0001 0000 0010 0010"
                if failure:
                    with self.assertRaises(requests.HTTPError):
                        await instance.send(command)
                else:
                    await instance.send(command)
                hass.async_add_executor_job.assert_awaited_once_with(
                    requests.get, f"http://test.local/commands/ir/prontohex/{command}")
                response.raise_for_status.assert_called_once_with()
