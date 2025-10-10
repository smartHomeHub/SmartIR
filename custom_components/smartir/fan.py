import asyncio
import aiofiles
import json
import logging
import os.path

import voluptuous as vol

from homeassistant.components.fan import (
    FanEntity, FanEntityFeature,
    PLATFORM_SCHEMA, DIRECTION_REVERSE, DIRECTION_FORWARD)
from homeassistant.const import (
    CONF_NAME, STATE_OFF, STATE_ON)
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change_event
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item
)
from . import COMPONENT_ABS_DIR, Helper
from .controller import get_controller

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "SmartIR Fan"
DEFAULT_DELAY = 0.5

CONF_UNIQUE_ID = 'unique_id'
CONF_DEVICE_CODE = 'device_code'
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"
CONF_POWER_SENSOR = 'power_sensor'

SPEED_OFF = "off"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_UNIQUE_ID): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_DEVICE_CODE): cv.positive_int,
    vol.Required(CONF_CONTROLLER_DATA): cv.string,
    vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): cv.positive_float,
    vol.Optional(CONF_POWER_SENSOR): cv.entity_id
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    device_code = config.get(CONF_DEVICE_CODE)
    device_files_subdir = os.path.join('codes', 'fan')
    device_files_absdir = os.path.join(COMPONENT_ABS_DIR, device_files_subdir)

    if not os.path.isdir(device_files_absdir):
        os.makedirs(device_files_absdir)

    device_json_filename = str(device_code) + '.json'
    device_json_path = os.path.join(device_files_absdir, device_json_filename)

    if not os.path.exists(device_json_path):
        _LOGGER.warning("Device JSON file not found. Attempting download from GitHub.")
        try:
            codes_source = ("https://raw.githubusercontent.com/"
                            "smartHomeHub/SmartIR/master/"
                            "codes/fan/{}.json")
            await Helper.downloader(codes_source.format(device_code), device_json_path)
        except Exception as err:
            _LOGGER.error("Failed to download device JSON file. Check internet connection "
                          "or device code validity. Error: %s", err)
            return

    try:
        async with aiofiles.open(device_json_path, mode='r') as j:
            content = await j.read()
            device_data = json.loads(content)
    except json.JSONDecodeError as err:
        _LOGGER.error("Invalid JSON file: %s", err)
        return
    except Exception as err:
        _LOGGER.error("Failed to load JSON file: %s", err)
        return

    # Validate required keys
    required_keys = ['manufacturer', 'supportedModels', 'supportedController', 
                     'commandsEncoding', 'speed', 'commands']
    if missing := [key for key in required_keys if key not in device_data]:
        _LOGGER.error("Missing required keys in JSON: %s", missing)
        return

    async_add_entities([SmartIRFan(hass, config, device_data)])

class SmartIRFan(FanEntity, RestoreEntity):

    def __init__(self, hass, config, device_data):
        self.hass = hass
        self._attr_unique_id = config.get(CONF_UNIQUE_ID)
        self._attr_name = config.get(CONF_NAME)
        self._device_code = config.get(CONF_DEVICE_CODE)
        self._controller_data = config.get(CONF_CONTROLLER_DATA)
        self._delay = config.get(CONF_DELAY)
        self._power_sensor = config.get(CONF_POWER_SENSOR)

        self._manufacturer = device_data['manufacturer']
        self._supported_models = device_data['supportedModels']
        self._supported_controller = device_data['supportedController']
        self._commands_encoding = device_data['commandsEncoding']
        self._speed_list = device_data['speed']
        self._commands = device_data['commands']
        
        self._speed = SPEED_OFF
        self._direction = None
        self._last_on_speed = None
        self._oscillating = None
        self._support_flags = (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.TURN_ON)

        if (DIRECTION_REVERSE in self._commands and
            DIRECTION_FORWARD in self._commands):
            self._direction = DIRECTION_REVERSE
            self._support_flags |= FanEntityFeature.DIRECTION
        if 'oscillate' in self._commands:
            self._oscillating = False
            self._support_flags |= FanEntityFeature.OSCILLATE

        self._command_lock = asyncio.Lock()
        self._on_by_remote = False

        self._controller = get_controller(
            self.hass,
            self._supported_controller,
            self._commands_encoding,
            self._controller_data,
            self._delay)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        
        try:
            if last_state := await self.async_get_last_state():
                if 'speed' in last_state.attributes:
                    self._speed = last_state.attributes['speed']
                elif 'percentage' in last_state.attributes:
                    percentage = last_state.attributes['percentage']
                    self._speed = SPEED_OFF if percentage == 0 else \
                        percentage_to_ordered_list_item(self._speed_list, percentage)
                
                if (self._support_flags & FanEntityFeature.DIRECTION and
                    'direction' in last_state.attributes):
                    self._direction = last_state.attributes['direction']
                
                if 'oscillating' in last_state.attributes:
                    self._oscillating = last_state.attributes['oscillating']
                
                if 'last_on_speed' in last_state.attributes:
                    self._last_on_speed = last_state.attributes['last_on_speed']
        except Exception as err:
            _LOGGER.warning("State restoration failed for %s: %s", self._attr_name, err)

        if self._power_sensor:
            async_track_state_change_event(self.hass, self._power_sensor,
                                           self._async_power_sensor_changed)

    @property
    def percentage(self):
        if self._speed == SPEED_OFF:
            return 0
        return ordered_list_item_to_percentage(self._speed_list, self._speed)

    @property
    def speed_count(self):
        return len(self._speed_list)

    @property
    def oscillating(self):
        return self._oscillating

    @property
    def current_direction(self):
        return self._direction

    @property
    def supported_features(self):
        return self._support_flags

    @property
    def extra_state_attributes(self):
        return {
            'last_on_speed': self._last_on_speed,
            'device_code': self._device_code,
            'manufacturer': self._manufacturer,
            'supported_models': self._supported_models,
            'supported_controller': self._supported_controller,
            'commands_encoding': self._commands_encoding,
        }

    async def async_set_percentage(self, percentage: int):
        if percentage == 0:
            self._speed = SPEED_OFF
        else:
            self._speed = percentage_to_ordered_list_item(self._speed_list, percentage)

        if self._speed != SPEED_OFF:
            self._last_on_speed = self._speed

        await self.send_command()
        self.async_write_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        self._oscillating = oscillating
        try:
            await self._controller.send(self._commands['oscillate'])
        except Exception as err:
            _LOGGER.exception("Oscillate command failed for %s: %s", self._attr_name, err)
        self.async_write_ha_state()

    async def async_set_direction(self, direction: str):
        self._direction = direction
        if self._speed != SPEED_OFF:
            await self.send_command()
        self.async_write_ha_state()

    async def async_turn_on(self, percentage: int = None, preset_mode: str = None, **kwargs):
        if percentage is None:
            if self._last_on_speed:
                percentage = ordered_list_item_to_percentage(self._speed_list, self._last_on_speed)
            else:
                percentage = ordered_list_item_to_percentage(self._speed_list, self._speed_list[0])
        await self.async_set_percentage(percentage)

    async def async_turn_off(self):
        await self.async_set_percentage(0)

    async def send_command(self):
        async with self._command_lock:
            self._on_by_remote = False
            speed = self._speed
            direction = self._direction or 'default'

            if speed is None:
                _LOGGER.warning("Speed is None for %s, skipping command", self._attr_name)
                return
            elif speed.lower() == SPEED_OFF:
                if 'off' not in self._commands:
                    _LOGGER.error("'off' command not found for %s", self._attr_name)
                    return
                command = self._commands['off']
            else:
                if direction not in self._commands:
                    _LOGGER.error("Direction '%s' not found for %s", direction, self._attr_name)
                    return
                if not isinstance(self._commands[direction], dict) or speed not in self._commands[direction]:
                    _LOGGER.error("Speed '%s' not in commands[%s] for %s", speed, direction, self._attr_name)
                    return
                command = self._commands[direction][speed]

            try:
                await self._controller.send(command)
            except Exception as err:
                _LOGGER.exception("Command send failed for %s: %s", self._attr_name, err)

    @callback
    def _async_power_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
        old_state = event.data["old_state"]

        if new_state is None or old_state is None or new_state.state == old_state.state:
            return

        if new_state.state == STATE_ON and self._speed == SPEED_OFF:
            self._on_by_remote = True
            self._speed = self._last_on_speed or self._speed_list[0]
            self.async_write_ha_state()
        elif new_state.state == STATE_OFF:
            self._on_by_remote = False
            if self._speed != SPEED_OFF:
                self._speed = SPEED_OFF
            self.async_write_ha_state()
