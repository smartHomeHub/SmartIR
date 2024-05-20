import asyncio
import logging

import voluptuous as vol

from homeassistant.components.fan import (
    FanEntity,
    PLATFORM_SCHEMA,
    DIRECTION_REVERSE,
    DIRECTION_FORWARD,
    SUPPORT_SET_SPEED,
    SUPPORT_DIRECTION,
    SUPPORT_OSCILLATE,
    ATTR_OSCILLATING,
)
from homeassistant.const import CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, Event, EventStateChangedData
from homeassistant.helpers.event import async_track_state_change_event
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)
from . import DeviceData
from .controller import get_controller

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "SmartIR Fan"
DEFAULT_DELAY = 0.5

CONF_UNIQUE_ID = "unique_id"
CONF_DEVICE_CODE = "device_code"
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"
CONF_POWER_SENSOR = "power_sensor"
CONF_POWER_SENSOR_RESTORE_STATE = "power_sensor_restore_state"

SPEED_OFF = "off"

SUPPORT_FLAGS = SUPPORT_SET_SPEED

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_DEVICE_CODE): cv.positive_int,
        vol.Required(CONF_CONTROLLER_DATA): cv.string,
        vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): cv.string,
        vol.Optional(CONF_POWER_SENSOR): cv.entity_id,
        vol.Optional(CONF_POWER_SENSOR_RESTORE_STATE, default=False): cv.boolean,
    }
)


async def async_setup_platform(
    hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None
):
    """Set up the IR Fan platform."""
    _LOGGER.debug("Setting up the smartir fan platform")
    if not (
        device_data := DeviceData.load_file(
            config.get(CONF_DEVICE_CODE),
            "fan",
            [
                "manufacturer",
                "supportedModels",
                "supportedController",
                "commandsEncoding",
                "speed",
            ],
        )
    ):
        _LOGGER.error("Smartir fan device data init failed!")
        return

    async_add_entities([SmartIRFan(hass, config, device_data)])


class SmartIRFan(FanEntity, RestoreEntity):
    def __init__(self, hass, config, device_data):
        self.hass = hass
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)
        self._device_code = config.get(CONF_DEVICE_CODE)
        self._controller_data = config.get(CONF_CONTROLLER_DATA)
        self._delay = config.get(CONF_DELAY)
        self._power_sensor = config.get(CONF_POWER_SENSOR)
        self._power_sensor_restore_state = config.get(CONF_POWER_SENSOR_RESTORE_STATE)

        self._manufacturer = device_data["manufacturer"]
        self._supported_models = device_data["supportedModels"]
        self._supported_controller = device_data["supportedController"]
        self._commands_encoding = device_data["commandsEncoding"]
        self._speed_list = device_data["speed"]
        self._commands = device_data["commands"]

        self._speed = SPEED_OFF
        self._current_direction = None
        self._last_on_speed = None
        self._oscillating = None
        self._support_flags = SUPPORT_FLAGS

        if DIRECTION_REVERSE in self._commands and DIRECTION_FORWARD in self._commands:
            self._current_direction = DIRECTION_REVERSE
            self._support_flags = self._support_flags | SUPPORT_DIRECTION
        if "oscillate" in self._commands:
            self._oscillating = False
            self._support_flags = self._support_flags | SUPPORT_OSCILLATE

        self._temp_lock = asyncio.Lock()
        self._on_by_remote = False

        # Init the IR/RF controller
        self._controller = get_controller(
            self.hass,
            self._supported_controller,
            self._commands_encoding,
            self._controller_data,
            self._delay,
        )

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()

        if last_state is not None:
            if "speed" in last_state.attributes:
                self._speed = last_state.attributes["speed"]

            # If _direction has a value the direction controls appears
            # in UI even if SUPPORT_DIRECTION is not provided in the flags
            if (
                "current_direction" in last_state.attributes
                and self._support_flags & SUPPORT_DIRECTION
            ):
                self._current_direction = last_state.attributes["current_direction"]

            if (
                "oscillating" in last_state.attributes
                and self._support_flags & SUPPORT_OSCILLATE
            ):
                self._oscillating = last_state.attributes["oscillating"]

            if "last_on_speed" in last_state.attributes:
                self._last_on_speed = last_state.attributes["last_on_speed"]

        if self._power_sensor:
            async_track_state_change_event(
                self.hass, self._power_sensor, self._async_power_sensor_changed
            )

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the display name of the fan."""
        return self._name

    @property
    def state(self):
        """Return the current state."""
        if self._speed != SPEED_OFF:
            return STATE_ON
        return SPEED_OFF

    @property
    def percentage(self):
        """Return speed percentage of the fan."""
        if self._speed == STATE_UNKNOWN:
            return STATE_UNKNOWN
        if self._speed == SPEED_OFF:
            return 0

        return ordered_list_item_to_percentage(self._speed_list, self._speed)

    @property
    def speed_count(self):
        """Return the number of speeds the fan supports."""
        return len(self._speed_list)

    @property
    def oscillating(self):
        """Return the oscillation state."""
        if self._speed == STATE_UNKNOWN:
            return STATE_UNKNOWN
        return self._oscillating

    @property
    def current_direction(self):
        """Return the direction state."""
        if self._speed == STATE_UNKNOWN:
            return STATE_UNKNOWN
        return self._current_direction

    @property
    def last_on_speed(self):
        """Return the last non-idle speed."""
        return self._last_on_speed

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def extra_state_attributes(self):
        """Platform specific attributes."""
        return {
            "last_on_speed": self._last_on_speed,
            "device_code": self._device_code,
            "manufacturer": self._manufacturer,
            "supported_models": self._supported_models,
            "supported_controller": self._supported_controller,
            "commands_encoding": self._commands_encoding,
        }

    async def async_set_percentage(self, percentage: int):
        """Set the desired speed for the fan."""
        if percentage == 0:
            self._speed = SPEED_OFF
        else:
            self._speed = percentage_to_ordered_list_item(self._speed_list, percentage)

        if not self._speed == SPEED_OFF:
            self._last_on_speed = self._speed

        await self.send_command()
        self.async_write_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation of the fan."""
        self._oscillating = oscillating

        await self.send_command()
        self.async_write_ha_state()

    async def async_set_direction(self, direction: str):
        """Set the direction of the fan"""
        self._current_direction = direction

        if not self._speed.lower() == SPEED_OFF:
            await self.send_command()

        self.async_write_ha_state()

    async def async_turn_on(
        self, percentage: int = None, preset_mode: str = None, **kwargs
    ):
        """Turn on the fan."""
        if percentage is None:
            percentage = ordered_list_item_to_percentage(
                self._speed_list, self._last_on_speed or self._speed_list[0]
            )

        await self.async_set_percentage(percentage)

    async def async_turn_off(self):
        """Turn off the fan."""
        await self.async_set_percentage(0)

    async def send_command(self):
        async with self._temp_lock:
            self._on_by_remote = False
            speed = self._speed
            direction = self._current_direction or "default"
            oscillating = self._oscillating

            if speed.lower() == SPEED_OFF:
                command = self._commands["off"]
            elif oscillating:
                command = self._commands["oscillate"]
            else:
                command = self._commands[direction][speed]

            try:
                await self._controller.send(command)
            except Exception as e:
                _LOGGER.exception(e)

    async def _async_power_sensor_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle power sensor changes."""
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        if new_state is None:
            return

        if old_state is not None and new_state.state == old_state.state:
            return

        if new_state.state == STATE_ON and self._speed == SPEED_OFF:
            self._on_by_remote = True
            if (
                self._power_sensor_restore_state == True
                and self._last_on_speed is not None
            ):
                self._speed = self._last_on_speed
            else:
                self._speed = STATE_UNKNOWN
            self.async_write_ha_state()
        elif new_state.state == STATE_OFF:
            self._on_by_remote = False
            if self._speed != SPEED_OFF:
                self._speed = SPEED_OFF
            self.async_write_ha_state()
