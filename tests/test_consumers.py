"""Actual consumer methods plus real controller.send compatibility regressions.

These are not transactional-platform tests. Fan/light mutate before awaiting;
all three platforms log and swallow ordinary send errors. Those legacy
boundaries are deliberately asserted rather than silently promising rollback.
No HA runtime, network, hardware or real IR codes are used.
"""

import asyncio
import unittest
from base64 import b64encode
from types import SimpleNamespace

from tests.consumer_support import Fan, Light, MediaPlayer, Services, snapshot
from tests.support import HomeAssistantError


def code(name):
    return b64encode(f"synthetic:{name}".encode()).decode("ascii")


class ConsumerRegressions(unittest.IsolatedAsyncioTestCase):
    def make_entity(self, platform):
        self.hass = SimpleNamespace(services=Services(), writes=[])
        data = {
            "manufacturer": "Test", "supportedModels": ["Synthetic"],
            "supportedController": "Broadlink", "commandsEncoding": "Base64",
        }
        if platform == "fan":
            data.update(speed=["low", "medium", "high"], commands={
                "off": code("off"),
                "default": {speed: code(speed) for speed in ("low", "medium", "high")},
            })
            entity_class = Fan
        elif platform == "light":
            data.update(brightness=[0, 100, 200, 255],
                        colorTemperature=[2000, 3000, 4000, 5000],
                        commands={name: code(name) for name in
                                  ("on", "off", "brighten", "dim", "colder", "warmer")})
            entity_class = Light
        else:
            data["commands"] = {name: code(name) for name in ("on", "off", "volumeUp")}
            data["commands"]["sources"] = {
                f"Channel {digit}": code(digit) for digit in "0123456789"
            }
            entity_class = MediaPlayer
        self.entity = entity_class(self.hass, {
            "name": "Test", "device_code": 1, "controller_data": "remote.test",
            "delay": 0,
        }, data)
        return self.entity

    def gate(self):
        future = asyncio.get_running_loop().create_future()
        self.hass.services.outcomes.append(future)
        return future

    async def cancel_task(self, task):
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    def spawn(self, request):
        task = asyncio.create_task(request)
        self.addAsyncCleanup(self.cancel_task, task)
        return task

    async def next_call(self):
        return await asyncio.wait_for(self.hass.services.started.get(), 1)

    async def start(self, request):
        task = self.spawn(request)
        await self.next_call()
        return task

    async def finish(self, task):
        await asyncio.wait_for(task, 1)

    async def asyncTearDown(self):
        if hasattr(self, "hass"):
            for task in self.hass.services.pending:
                await self.cancel_task(task)

    def assert_payloads(self, *names):
        self.assertEqual(
            [(call.domain, call.service, call.data, call.blocking)
             for call in self.hass.services.calls],
            [("remote", "send_command",
              {"entity_id": "remote.test", "command": ["b64:" + code(name)],
               "delay_secs": 0}, True) for name in names],
        )

    async def test_fan_success_waits_to_publish_but_mutates_speed_early(self):
        entity = self.make_entity("fan")
        gate = self.gate()
        task = await self.start(entity.async_set_percentage(100))
        self.assertFalse(task.done())
        self.assertEqual(snapshot(entity), ("high", "high", False))
        self.assertEqual(self.hass.writes, [])
        self.assert_payloads("high")
        gate.set_result(None)
        await self.finish(task)
        self.assertEqual(self.hass.writes, [snapshot(entity)])
        self.assertTrue(self.hass.services.calls[0].completed)

    async def test_fan_service_error_is_logged_and_legacy_state_is_published(self):
        entity = self.make_entity("fan")
        gate = self.gate()
        error = HomeAssistantError("fan unavailable")
        with self.assertLogs("smartir_consumer_test.fan", level="ERROR") as logs:
            task = await self.start(entity.async_set_percentage(100))
            gate.set_exception(error)
            await self.finish(task)
        self.assertIn("fan unavailable", "\n".join(logs.output))
        self.assertIs(self.hass.services.calls[0].error, error)
        self.assertEqual(self.hass.writes, [("high", "high", False)])

    async def test_fan_cancellation_propagates_and_releases_lock(self):
        entity = self.make_entity("fan")
        self.gate()
        task = await self.start(entity.async_set_percentage(100))
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.hass.writes, [])
        self.assertEqual(entity._speed, "high")
        self.assertFalse(entity._temp_lock.locked())
        await self.finish(self.spawn(entity.async_turn_off()))
        self.assert_payloads("high", "off")
        self.assertTrue(self.hass.services.calls[0].cancelled)

    async def test_fan_concurrent_sends_do_not_overlap(self):
        entity = self.make_entity("fan")
        gate = self.gate()
        first = await self.start(entity.async_set_percentage(34))
        second = self.spawn(entity.async_turn_off())
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        self.assert_payloads("medium")
        gate.set_result(None)
        await self.finish(asyncio.gather(first, second))
        self.assert_payloads("medium", "off")
        self.assertEqual(self.hass.services.max_active, 1)

    async def test_light_power_color_and_repeated_brightness_payload_order(self):
        entity = self.make_entity("light")
        entity._power = "off"
        entity._brightness = 0
        gates = [self.gate() for _ in range(5)]
        task = self.spawn(entity.async_turn_on(color_temp_kelvin=3000, brightness=200))
        expected = ("on", "warmer", "warmer", "brighten", "brighten")
        for index, gate in enumerate(gates):
            await self.next_call()
            self.assertFalse(task.done())
            self.assertEqual(self.hass.writes, [])
            self.assert_payloads(*expected[:index + 1])
            gate.set_result(None)
        await self.finish(task)
        self.assertEqual(self.hass.writes, [("on", 200, 3000)])
        self.assertEqual(self.hass.services.max_active, 1)
        self.assertTrue(all(call.completed for call in self.hass.services.calls))

    async def test_light_turn_off_waits_to_publish_but_mutates_power_early(self):
        entity = self.make_entity("light")
        gate = self.gate()
        task = await self.start(entity.async_turn_off())
        self.assertFalse(entity.is_on)
        self.assertFalse(task.done())
        self.assertEqual(self.hass.writes, [])
        gate.set_result(None)
        await self.finish(task)
        self.assert_payloads("off")
        self.assertEqual(self.hass.writes, [snapshot(entity)])

    async def test_light_deferred_error_stops_remaining_repeated_steps(self):
        entity = self.make_entity("light")
        self.hass.services.outcomes.append(None)
        gate = self.gate()
        with self.assertLogs("smartir_consumer_test.light", level="ERROR") as logs:
            task = self.spawn(entity.async_turn_on(color_temp_kelvin=2000))
            await self.next_call()
            await self.next_call()
            self.assert_payloads("warmer", "warmer")
            self.assertFalse(task.done())
            gate.set_exception(HomeAssistantError("second step failed"))
            await self.finish(task)
        self.assertIn("second step failed", "\n".join(logs.output))
        self.assert_payloads("warmer", "warmer")
        self.assertEqual(self.hass.writes, [("on", 100, 2000)])
        self.assertFalse(entity._temp_lock.locked())

    async def test_light_cancelled_step_stops_sequence_and_releases_lock(self):
        entity = self.make_entity("light")
        self.gate()
        task = await self.start(entity.async_turn_on(color_temp_kelvin=2000, brightness=200))
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.hass.writes, [])
        self.assertEqual(entity._colortemp, 2000)
        await self.finish(self.spawn(entity.async_turn_off()))
        self.assert_payloads("warmer", "off")
        self.assertEqual(self.hass.services.max_active, 1)

    async def test_light_legacy_error_stops_group_not_later_brightness_group(self):
        """Ordinary errors are swallowed by send_command, unlike cancellation."""
        entity = self.make_entity("light")
        gate = self.gate()
        with self.assertLogs("smartir_consumer_test.light", level="ERROR"):
            task = await self.start(entity.async_turn_on(
                color_temp_kelvin=2000, brightness=200))
            gate.set_exception(HomeAssistantError("color step failed"))
            await self.finish(task)
        self.assert_payloads("warmer", "brighten")
        self.assertEqual(self.hass.writes, [("on", 200, 2000)])

    async def test_light_repeated_group_is_not_interleaved_by_concurrent_off(self):
        entity = self.make_entity("light")
        gate = self.gate()
        first = await self.start(entity.async_turn_on(color_temp_kelvin=3000))
        second = self.spawn(entity.async_turn_off())
        await asyncio.sleep(0)
        self.assert_payloads("warmer")
        self.assertFalse(second.done())
        gate.set_result(None)
        await self.finish(asyncio.gather(first, second))
        self.assert_payloads("warmer", "warmer", "off")
        self.assertEqual(self.hass.services.max_active, 1)

    async def test_media_power_on_waits_before_state_change_and_publication(self):
        entity = self.make_entity("media_player")
        gate = self.gate()
        task = await self.start(entity.async_turn_on())
        self.assertEqual(snapshot(entity), ("off", None))
        self.assertEqual(self.hass.writes, [])
        self.assertFalse(task.done())
        gate.set_result(None)
        await self.finish(task)
        self.assert_payloads("on")
        self.assertEqual(self.hass.writes, [("on", None)])

    async def test_media_channel_power_preamble_and_repeated_digits_are_awaited(self):
        entity = self.make_entity("media_player")
        gates = [self.gate() for _ in range(4)]
        task = self.spawn(entity.async_play_media("channel", "101"))
        expected = ("on", "1", "0", "1")
        for index, gate in enumerate(gates):
            await self.next_call()
            self.assertFalse(task.done())
            self.assert_payloads(*expected[:index + 1])
            self.assertEqual(self.hass.writes, [] if index == 0 else [("on", None)])
            gate.set_result(None)
        await self.finish(task)
        self.assertEqual(self.hass.writes, [("on", None), ("on", "Channel 101")])
        self.assertEqual(self.hass.services.max_active, 1)

    async def test_media_send_error_is_logged_but_legacy_power_state_commits(self):
        entity = self.make_entity("media_player")
        gate = self.gate()
        with self.assertLogs("smartir_consumer_test.media_player", level="ERROR") as logs:
            task = await self.start(entity.async_turn_on())
            gate.set_exception(HomeAssistantError("media unavailable"))
            await self.finish(task)
        self.assertIn("media unavailable", "\n".join(logs.output))
        self.assertEqual(self.hass.writes, [("on", None)])
        self.assertFalse(self.hass.services.calls[0].completed)

    async def test_media_cancelled_digit_stops_remaining_digits_and_unlocks(self):
        entity = self.make_entity("media_player")
        entity._state = "on"
        self.gate()
        task = await self.start(entity.async_play_media("channel", "101"))
        self.assertEqual(entity.source, "Channel 101")
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.hass.writes, [])
        self.assertFalse(entity._temp_lock.locked())
        await self.finish(self.spawn(entity.async_turn_off()))
        self.assert_payloads("1", "off")
        self.assertEqual(self.hass.writes, [("off", None)])

    async def test_media_legacy_failed_digit_does_not_stop_later_digits(self):
        entity = self.make_entity("media_player")
        entity._state = "on"
        gate = self.gate()
        with self.assertLogs("smartir_consumer_test.media_player", level="ERROR"):
            task = await self.start(entity.async_play_media("channel", "101"))
            gate.set_exception(HomeAssistantError("first digit failed"))
            await self.finish(task)
        self.assert_payloads("1", "0", "1")
        self.assertFalse(self.hass.services.calls[0].completed)
        self.assertTrue(all(call.completed for call in self.hass.services.calls[1:]))
        self.assertEqual(self.hass.writes, [("on", "Channel 101")])

    async def test_media_concurrent_volume_is_serialized_between_channel_digits(self):
        """The existing lock is per digit, not a channel-wide transaction."""
        entity = self.make_entity("media_player")
        entity._state = "on"
        gate = self.gate()
        channel = await self.start(entity.async_play_media("channel", "101"))
        volume = self.spawn(entity.async_volume_up())
        await asyncio.sleep(0)
        self.assertFalse(volume.done())
        self.assert_payloads("1")
        gate.set_result(None)
        await self.finish(asyncio.gather(channel, volume))
        self.assert_payloads("1", "volumeUp", "0", "1")
        self.assertEqual(self.hass.services.max_active, 1)

    async def test_controller_send_compatibility_surfaces_deferred_service_error(self):
        """Consumers swallow errors; the shared controller.send API must not."""
        entity = self.make_entity("fan")
        gate = self.gate()
        error = HomeAssistantError("service rejected payload")
        task = await self.start(entity._controller.send(code("high")))
        self.assertFalse(task.done())
        gate.set_exception(error)
        with self.assertRaises(HomeAssistantError) as result:
            await self.finish(task)
        self.assertIs(result.exception, error)
        self.assert_payloads("high")
        self.assertEqual(self.hass.writes, [])


if __name__ == "__main__":
    unittest.main()
