import asyncio
import logging

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
    DIRECTION_REVERSE,
    DIRECTION_FORWARD,
)

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .controller import get_controller
from .helpers import async_load_device_data

_LOGGER = logging.getLogger(__name__)

CONF_UNIQUE_ID = "unique_id"
CONF_NAME = "name"
CONF_DEVICE_CODE = "device_code"
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"

DEFAULT_DELAY = 0.5
SPEED_OFF = "off"


async def async_setup_entry(hass, entry, async_add_entities):

    config = entry.data

    device_code = config.get(CONF_DEVICE_CODE)

    device_data = await async_load_device_data(device_code, "fan")

    async_add_entities(
        [
            SmartIRFan(
                hass,
                config,
                device_data,
            )
        ],
        True,
    )


class SmartIRFan(FanEntity, RestoreEntity):

    def __init__(self, hass, config, device_data):

        self.hass = hass

        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)

        self._controller_data = config.get(CONF_CONTROLLER_DATA)
        self._delay = config.get(CONF_DELAY, DEFAULT_DELAY)

        self._supported_controller = device_data["supportedController"]
        self._commands_encoding = device_data["commandsEncoding"]

        self._speed_list = device_data["speed"]
        self._commands = device_data["commands"]

        self._speed = SPEED_OFF
        self._direction = None
        self._last_on_speed = None
        self._oscillating = False

        self._support_flags = (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
        )

        if (
            DIRECTION_REVERSE in self._commands
            and DIRECTION_FORWARD in self._commands
        ):
            self._direction = DIRECTION_FORWARD
            self._support_flags |= FanEntityFeature.DIRECTION

        if "oscillate" in self._commands:
            self._support_flags |= FanEntityFeature.OSCILLATE

        self._temp_lock = asyncio.Lock()

        self._controller = get_controller(
            hass,
            self._supported_controller,
            self._commands_encoding,
            self._controller_data,
            self._delay,
        )

    async def async_added_to_hass(self):

        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()

        if last_state and "speed" in last_state.attributes:
            self._speed = last_state.attributes["speed"]

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def percentage(self):

        if self._speed == SPEED_OFF:
            return 0

        return ordered_list_item_to_percentage(
            self._speed_list,
            self._speed,
        )

    @property
    def speed_count(self):
        return len(self._speed_list)

    @property
    def supported_features(self):
        return self._support_flags

    async def async_set_percentage(self, percentage: int):

        if percentage == 0:
            self._speed = SPEED_OFF
        else:
            self._speed = percentage_to_ordered_list_item(
                self._speed_list,
                percentage,
            )

        await self.send_command()

        self.async_write_ha_state()

    async def async_turn_on(self, percentage=None, **kwargs):

        if percentage is None:
            percentage = ordered_list_item_to_percentage(
                self._speed_list,
                self._last_on_speed or self._speed_list[0],
            )

        await self.async_set_percentage(percentage)

    async def async_turn_off(self):

        await self.async_set_percentage(0)

    async def send_command(self):

        async with self._temp_lock:

            speed = self._speed

            if speed.lower() == SPEED_OFF:
                command = self._commands["off"]
            else:
                command = self._commands[speed]

            try:
                await self._controller.send(command)

            except Exception as e:
                _LOGGER.exception(e)