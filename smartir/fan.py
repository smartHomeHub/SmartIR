import asyncio
from base64 import b64encode
import binascii
import json
import logging
import os.path

import voluptuous as vol

from homeassistant.components.fan import (
    FanEntity, PLATFORM_SCHEMA, ATTR_SPEED, 
    SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH, 
    DIRECTION_REVERSE, DIRECTION_FORWARD,
    SUPPORT_SET_SPEED, SUPPORT_DIRECTION)
from homeassistant.const import (
    CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN)
from homeassistant.core import callback, split_entity_id
from homeassistant.helpers.event import async_track_state_change
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from . import Helper

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "SmartIR Fan"

CONF_DEVICE_CODE = 'device_code'
CONF_CONTROLLER_SEND_SERVICE = "controller_send_service"
CONF_POWER_SENSOR = 'power_sensor'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_DEVICE_CODE): cv.positive_int,
    vol.Required(CONF_CONTROLLER_SEND_SERVICE): cv.entity_id,
    vol.Optional(CONF_POWER_SENSOR): cv.entity_id
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    name = config.get(CONF_NAME)
    device_code = config.get(CONF_DEVICE_CODE)
    controller_send_service = config.get(CONF_CONTROLLER_SEND_SERVICE)
    power_sensor = config.get(CONF_POWER_SENSOR)

    abspath = os.path.dirname(os.path.abspath(__file__))
    device_files_subdir = os.path.join('codes', 'fan')
    device_files_path = os.path.join(abspath, device_files_subdir)

    if not os.path.isdir(device_files_path):
        os.makedirs(device_files_path)

    device_json_filename = str(device_code) + '.json'
    device_json_path = os.path.join(device_files_path, device_json_filename)

    if not os.path.exists(device_json_path):
        _LOGGER.warning("Couldn't find the device Json file. The component will " \
                        "try to download it from the GitHub repo.")

        try:
            codes_source = ("https://raw.githubusercontent.com/"
                            "smartHomeHub/SmartIR/master/smartir/"
                            "codes/fan/{}.json")

            Helper.downloader(codes_source.format(device_code), device_json_path)
        except:
            _LOGGER.error("There was an error while downloading the device Json file. " \
                          "Please check your internet connection or the device code " \
                          "exists on GitHub. If the problem still exists please " \
                          "place the file manually in the proper location.")
            return

    with open(device_json_path) as j:
        try:
            device_data = json.load(j)
        except:
            _LOGGER.error("The device JSON file is invalid")
            return

    async_add_entities([SmartIRFan(
        hass, name, device_code, device_data, controller_send_service, 
        power_sensor
    )])

class SmartIRFan(FanEntity, RestoreEntity):
    def __init__(self, hass, name, device_code, device_data, 
                 controller_send_service, power_sensor):
        self.hass = hass
        self._name = name
        self._device_code = device_code
        self._controller_send_service = controller_send_service
        self._power_sensor = power_sensor

        self._manufacturer = device_data['manufacturer']
        self._supported_models = device_data['supportedModels']
        self._supported_controller = device_data['supportedController']
        self._commands_encoding = device_data['commandsEncoding']
        self._speed_list = [SPEED_OFF] + device_data['speed']
        self._commands = device_data['commands']
        
        self._speed = SPEED_OFF
        self._direction = None
        self._last_on_speed = None

        self._support_flags = SUPPORT_SET_SPEED

        if (DIRECTION_REVERSE in self._commands and \
            DIRECTION_FORWARD in self._commands):
            self._direction = DIRECTION_REVERSE
            self._support_flags = (
                self._support_flags | SUPPORT_DIRECTION)

        self._temp_lock = asyncio.Lock()
        self._on_by_remote = False

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
    
        last_state = await self.async_get_last_state()

        if last_state is not None:
            if 'speed' in last_state.attributes:
                self._speed = last_state.attributes['speed']

            #If _direction has a value the direction controls appears 
            #in UI even if SUPPORT_DIRECTION is not provided in the flags
            if ('direction' in last_state.attributes and \
                self._support_flags & SUPPORT_DIRECTION):
                self._direction = last_state.attributes['direction']

            if 'last_on_speed' in last_state.attributes:
                self._last_on_speed = last_state.attributes['last_on_speed']

            if self._power_sensor:
                async_track_state_change(self.hass, self._power_sensor, 
                                         self._async_power_sensor_changed)

    @property
    def name(self):
        """Return the display name of the fan."""
        return self._name

    @property
    def state(self):
        """Return the current state."""
        if (self._on_by_remote or \
            self.speed != SPEED_OFF):
            return STATE_ON
        return SPEED_OFF

    @property
    def speed_list(self):
        """Get the list of available speeds."""
        return self._speed_list

    @property
    def speed(self):
        """Return the current speed."""
        return self._speed

    @property
    def oscillating(self):
        """Return the oscillation state."""
        return None

    @property
    def direction(self):
        """Return the oscillation state."""
        return self._direction

    @property
    def last_on_speed(self):
        """Return the last non-idle speed."""
        return self._last_on_speed

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def device_state_attributes(self) -> dict:
        """Platform specific attributes."""
        return {
            'last_on_speed': self._last_on_speed,
            'device_code': self._device_code,
            'manufacturer': self._manufacturer,
            'supported_models': self._supported_models,
            'supported_controller': self._supported_controller,
            'commands_encoding': self._commands_encoding,
        }

    async def async_set_speed(self, speed: str):
        """Set the speed of the fan."""
        self._speed = speed

        if not speed == SPEED_OFF:
            self._last_on_speed = speed

        await self.send_command()
        await self.async_update_ha_state()

    async def async_set_direction(self, direction: str):
        """Set the direction of the fan"""
        self._direction = direction

        if not self._speed.lower() == SPEED_OFF:
            await self.send_command()

        await self.async_update_ha_state()

    async def async_turn_on(self, speed: str = None, **kwargs):
        """Turn on the fan."""
        if speed is None:
            speed = self._last_on_speed or self._speed_list[1]

        await self.async_set_speed(speed)

    async def async_turn_off(self):
        """Turn off the fan."""
        await self.async_set_speed(SPEED_OFF)

    async def send_command(self):
        async with self._temp_lock:
            self._on_by_remote = False
            supported_controller = self._supported_controller
            commands_encoding = self._commands_encoding
            speed = self._speed
            direction = self._direction or 'default'

            if speed.lower() == SPEED_OFF:
                command = self._commands['off']
            else:
                command = self._commands[direction][speed] 

            service_domain = split_entity_id(self._controller_send_service)[0]
            service_name = split_entity_id(self._controller_send_service)[1]

            if supported_controller.lower() == 'broadlink':
                if commands_encoding.lower() == 'base64':
                    pass
                elif commands_encoding.lower() == 'hex':
                    try:
                        command = binascii.unhexlify(command)
                        command = b64encode(command).decode('utf-8')
                    except:
                        _LOGGER.error("Error while converting Hex to Base64")
                        return
                elif commands_encoding.lower() == 'pronto':
                    try:
                        command = command.replace(' ',"")
                        command = bytearray.fromhex(command)
                        command = Helper.pronto2lirc(command)
                        command = Helper.lirc2broadlink(command)
                        command = b64encode(command).decode('utf-8')
                    except:
                        _LOGGER.error("Error while converting Pronto to Base64")
                        return
                else:
                    _LOGGER.error("The commands encoding provided in the JSON file is not supported")
                    return

                service_data = {
                    'packet': [command]
                }

            else:
                _LOGGER.error("The controller provided in the JSON file is not supported")
                return

            await self.hass.services.async_call(service_domain, service_name, service_data)

    async def _async_power_sensor_changed(self, entity_id, old_state, new_state):
        """Handle power sensor changes."""
        if new_state is None:
            return

        if new_state.state == STATE_ON and self._speed == SPEED_OFF:
            self._on_by_remote = True
            self._speed = None
            await self.async_update_ha_state()

        if new_state.state == STATE_OFF:
            self._on_by_remote = False
            if self._speed != SPEED_OFF:
                self._speed = SPEED_OFF
            await self.async_update_ha_state()
