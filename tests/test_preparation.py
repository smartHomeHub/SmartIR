"""Side-effect-free preparation and complete-sequence preflight regressions."""

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from tests import test_climate as fixtures
from tests.support import ServiceValidationError, settings
from tests.test_climate import Services, controller


PRONTO = "0000 006D 0001 0000 0010 0010"


class Preparation(unittest.IsolatedAsyncioTestCase):
    def make_controller(self, kind, encoding):
        self.hass = SimpleNamespace(services=Services(), async_add_executor_job=AsyncMock())
        return controller.get_controller(self.hass, kind, encoding, "target", 0)

    async def test_preparing_supported_formats_has_no_side_effects(self):
        cases = [
            ("Broadlink", "Base64", "AQI=", {"entity_id": "target", "command": ["b64:AQI="], "delay_secs": 0}),
            ("Broadlink", "Hex", "0102", {"entity_id": "target", "command": ["b64:AQI="], "delay_secs": 0}),
            ("Xiaomi", "Pronto", PRONTO, {"entity_id": "target", "command": "pronto:" + PRONTO}),
            ("Xiaomi", "Raw", "opaque", {"entity_id": "target", "command": "raw:opaque"}),
            ("MQTT", "Raw", '{"ir": "opaque"}', {"topic": "target", "payload": '{"ir": "opaque"}'}),
            ("LOOKin", "Pronto", PRONTO, "http://target/commands/ir/prontohex/" + PRONTO),
            ("LOOKin", "Raw", "opaque", "http://target/commands/ir/raw/opaque"),
            ("ESPHome", "Raw", "[100, -100]", {"command": [100, -100]}),
            ("ESPHome", "Raw", "[]", {"command": []}),
            ("ESPHome", "Raw", '["100", -100.5]', {"command": ["100", -100.5]}),
            ("ESPHome", "Raw", '"opaque"', {"command": "opaque"}),
        ]
        for kind, encoding, command, expected in cases:
            with self.subTest(kind=kind, encoding=encoding, command=command):
                instance = self.make_controller(kind, encoding)
                self.assertEqual(instance.prepare(command), expected)
                self.assertEqual(self.hass.services.calls, [])
                self.hass.async_add_executor_job.assert_not_called()

    async def test_broadlink_pronto_uses_actual_conversion_helpers(self):
        instance = self.make_controller("Broadlink", "Pronto")
        # Two 421-microsecond pulses convert to two Broadlink timing bytes.
        self.assertEqual(instance.prepare(PRONTO), {
            "entity_id": "target", "command": ["b64:JgACAA0NDQUAAAAA"], "delay_secs": 0,
        })
        self.assertEqual(self.hass.services.calls, [])

    async def test_base64_preserves_native_permissive_formats(self):
        instance = self.make_controller("Broadlink", "Base64")
        for command in ("AQI=", "AQI", "AQI=\n", "AQ I="):
            with self.subTest(command=command):
                self.assertEqual(instance.prepare(command)["command"], ["b64:" + command])

    async def test_passthrough_pronto_does_not_require_broadlink_raw_dialect(self):
        command = "5000 0000 0000 0001 0000 000C"
        xiaomi = self.make_controller("Xiaomi", "Pronto")
        self.assertEqual(xiaomi.prepare(command)["command"], "pronto:" + command)
        lookin = self.make_controller("LOOKin", "Pronto")
        self.assertEqual(lookin.prepare(command), "http://target/commands/ir/prontohex/" + command)

    async def test_invalid_local_formats_raise_validation_errors_without_calls(self):
        cases = [
            ("Broadlink", "Base64", "a"),
            ("Broadlink", "Base64", "!!!!"),
            ("Broadlink", "Base64", "\u2603"),
            ("Broadlink", "Base64", []),
            ("Broadlink", "Base64", ["AQI=", "a"]),
            ("Broadlink", "Hex", "not-hex"),
            ("Broadlink", "Hex", "123"),
            ("Broadlink", "Pronto", "not-pronto"),
            ("Broadlink", "Pronto", "0000"),
            ("Broadlink", "Pronto", "0000 0000 0001 0000 0010 0010"),
            ("Broadlink", "Pronto", "0000 006D 0002 0000 0010 0010"),
            ("Xiaomi", "Pronto", "0000"),
            ("Xiaomi", "Raw", ["opaque"]),
            ("LOOKin", "Pronto", "0000"),
            ("LOOKin", "Raw", ["opaque"]),
            ("MQTT", "Raw", ["opaque"]),
            ("MQTT", "Raw", {"command": "opaque"}),
            ("ESPHome", "Raw", "not-json"),
        ]
        for kind, encoding, command in cases:
            with self.subTest(kind=kind, encoding=encoding, command=command):
                instance = self.make_controller(kind, encoding)
                with self.assertRaises(ServiceValidationError):
                    await instance.send(command)
                self.assertEqual(self.hass.services.calls, [])
                self.hass.async_add_executor_job.assert_not_called()

    async def test_invalid_settings_never_send_valid_preamble(self):
        cases = [
            ("Broadlink", "Hex", "0102", "not-hex"),
            ("Broadlink", "Base64", "AQI=", "a"),
            ("Broadlink", "Pronto", PRONTO, "0000"),
            ("Xiaomi", "Pronto", PRONTO, "0000"),
            ("LOOKin", "Pronto", PRONTO, "0000"),
            ("ESPHome", "Raw", "[1, -2]", "not-json"),
            ("ESPHome", "Raw", "[1, -2]", "[1,]"),
        ]
        for kind, encoding, preamble, invalid in cases:
            with self.subTest(kind=kind, encoding=encoding, invalid=invalid):
                fixture = fixtures.ClimateTransactions()
                entity = fixture.make_entity(preamble=True)
                entity._controller = controller.get_controller(
                    fixture.hass, kind, encoding, "target", 0)
                entity._commands["on"] = preamble
                entity._commands["cool"]["auto"]["18"] = invalid
                before = settings(entity)
                with self.assertRaises(ServiceValidationError):
                    await entity.async_turn_on()
                self.assertEqual(fixture.hass.services.calls, [])
                self.assertEqual(fixture.hass.writes, [])
                self.assertEqual(settings(entity), before)

    async def test_invalid_preamble_never_sends_valid_settings(self):
        fixture = fixtures.ClimateTransactions()
        entity = fixture.make_entity(preamble=True)
        entity._controller = controller.get_controller(
            fixture.hass, "Broadlink", "Hex", "target", 0)
        entity._commands["on"] = "not-hex"
        entity._commands["cool"]["auto"]["18"] = "0102"
        with self.assertRaises(ServiceValidationError):
            await entity.async_turn_on()
        self.assertEqual(fixture.hass.services.calls, [])

    async def test_exact_prepared_payloads_are_sent_without_reconversion(self):
        fixture = fixtures.ClimateTransactions()
        entity = fixture.make_entity(preamble=True)
        gate = fixture.gate()
        instance = entity._controller
        payloads = []
        original_prepare = instance.prepare

        def prepare(command):
            payload = original_prepare(command)
            payloads.append(payload)
            return payload

        with patch.object(instance, "prepare", side_effect=prepare) as preparation:
            task = asyncio.create_task(entity.async_turn_on())
            try:
                first = await asyncio.wait_for(fixture.hass.services.started.get(), 1)
                self.assertEqual(preparation.call_count, 2)
                self.assertIs(first.data, payloads[0])
                # Neither profile edits nor later preparation can change this request.
                entity._commands["cool"]["auto"]["18"] = "a"
                gate.set_result(None)
                await asyncio.wait_for(task, 1)
                self.assertIs(fixture.hass.services.calls[1].data, payloads[1])
                self.assertEqual(preparation.call_count, 2)
                self.assertEqual(entity.hvac_mode, "cool")
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_preparation_does_not_mutate_input_lists(self):
        instance = self.make_controller("Broadlink", "Hex")
        command = ["0102", "0304"]
        payload = instance.prepare(command)
        command[0] = "not-hex"
        self.assertEqual(payload["command"], ["b64:AQI=", "b64:AwQ="])

    async def test_prepared_json_is_not_shared_between_requests(self):
        instance = self.make_controller("ESPHome", "Raw")
        first = instance.prepare('{"timings": [1, -2]}')
        second = instance.prepare('{"timings": [1, -2]}')
        first["command"]["timings"][0] = 99
        self.assertEqual(second, {"command": {"timings": [1, -2]}})

    async def test_mqtt_preparation_preserves_scalar_and_snapshots_mutable_payload(self):
        instance = self.make_controller("MQTT", "Raw")
        for command in (None, "", 42, b"opaque"):
            with self.subTest(command=command):
                self.assertEqual(instance.prepare(command)["payload"], command)
        command = bytearray(b"opaque")
        payload = instance.prepare(command)
        command[0] = ord("x")
        self.assertEqual(payload["payload"], bytearray(b"opaque"))

    async def test_direct_send_prepares_once_and_surfaces_handler_errors(self):
        instance = self.make_controller("Broadlink", "Hex")
        error = OSError("handler failure")
        self.hass.services.outcomes.append(error)
        with patch.object(instance, "prepare", wraps=instance.prepare) as prepare:
            with self.assertRaises(OSError) as result:
                await instance.send("0102")
        self.assertIs(result.exception, error)
        prepare.assert_called_once_with("0102")
        self.assertEqual(self.hass.services.calls[0].data["command"], ["b64:AQI="])
