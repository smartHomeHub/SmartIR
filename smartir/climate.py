import asyncio
from base64 import b64encode
import binascii
import json
import logging
import os.path

import voluptuous as vol

"""
from homeassistant.components.climate import ClimateDevice, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    STATE_HEAT, STATE_COOL, STATE_AUTO, STATE_DRY,
    SUPPORT_OPERATION_MODE, SUPPORT_TARGET_TEMPERATURE, SUPPORT_FAN_MODE,
    SUPPORT_ON_OFF)
"""
from homeassistant.components.climate import (
    STATE_HEAT, STATE_COOL, STATE_AUTO, STATE_DRY, ClimateDevice,
    SUPPORT_OPERATION_MODE, SUPPORT_TARGET_TEMPERATURE, SUPPORT_FAN_MODE,
    SUPPORT_ON_OFF, PLATFORM_SCHEMA)
from homeassistant.const import (
    CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN, ATTR_TEMPERATURE,
    PRECISION_HALVES, PRECISION_TENTHS, PRECISION_WHOLE)
from homeassistant.core import callback, split_entity_id
from homeassistant.helpers.event import async_track_state_change
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from . import Helper

_LOGGER = logging.getLogger(__name__)

VERSION = '1.1.0'

DEFAULT_NAME = "SmartIR Climate"

CONF_DEVICE_CODE = 'device_code'
CONF_CONTROLLER_SEND_SERVICE = "controller_send_service"
CONF_TEMPERATURE_SENSOR = 'temperature_sensor'
CONF_HUMIDITY_SENSOR = 'humidity_sensor'
CONF_POWER_SENSOR = 'power_sensor'

SUPPORT_FLAGS = (
    SUPPORT_TARGET_TEMPERATURE | 
    SUPPORT_OPERATION_MODE | 
    SUPPORT_FAN_MODE | 
    SUPPORT_ON_OFF
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_DEVICE_CODE): cv.positive_int,
    vol.Required(CONF_CONTROLLER_SEND_SERVICE): cv.entity_id,
    vol.Optional(CONF_TEMPERATURE_SENSOR): cv.entity_id,
    vol.Optional(CONF_HUMIDITY_SENSOR): cv.entity_id,
    vol.Optional(CONF_POWER_SENSOR): cv.entity_id
})

async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the IR Climate platform."""
    name = config.get(CONF_NAME)
    device_code = config.get(CONF_DEVICE_CODE)
    controller_send_service = config.get(CONF_CONTROLLER_SEND_SERVICE)
    temperature_sensor = config.get(CONF_TEMPERATURE_SENSOR)
    humidity_sensor = config.get(CONF_HUMIDITY_SENSOR)
    power_sensor = config.get(CONF_POWER_SENSOR)

    abspath = os.path.dirname(os.path.abspath(__file__))
    device_json_file = "{}/codes/climate/{}.json".format(abspath, device_code)

    if not os.path.exists(device_json_file):
        _LOGGER.error("The device JSON file was not found. [%s]", device_json_file)
        return

    with open(device_json_file) as j:
        try:
            device_data = json.load(j)
        except:
            _LOGGER.error("The device JSON file is invalid")
            return

    async_add_devices([SmartIRClimate(
        hass, name, device_code, device_data, controller_send_service, 
        temperature_sensor, humidity_sensor, power_sensor
    )])

class SmartIRClimate(ClimateDevice, RestoreEntity):
    def __init__(self, hass, name, device_code, device_data, 
                 controller_send_service, temperature_sensor, 
                 humidity_sensor, power_sensor):
        self.hass = hass
        self._name = name
        self._device_code = device_code
        self._controller_send_service = controller_send_service
        self._temperature_sensor = temperature_sensor
        self._humidity_sensor = humidity_sensor
        self._power_sensor = power_sensor

        self._manufacturer = device_data['manufacturer']
        self._supported_models = device_data['supportedModels']
        self._supported_controller = device_data['supportedController']
        self._commands_encoding = device_data['commandsEncoding']
        self._min_temperature = device_data['minTemperature']
        self._max_temperature = device_data['maxTemperature']
        self._precision = device_data['precision']
        self._operation_modes = [STATE_OFF] + device_data['operationModes']
        self._fan_modes = device_data['fanModes']
        self._commands = device_data['commands']

        self._target_temperature = self._min_temperature
        self._current_operation = STATE_OFF
        self._current_fan_mode = self._fan_modes[0]
        self._last_on_operation = None

        self._current_temperature = None
        self._current_humidity = None

        self._unit = hass.config.units.temperature_unit
        self._support_flags = SUPPORT_FLAGS

        self._temp_lock = asyncio.Lock()
        self._on_by_remote = False

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
    
        last_state = await self.async_get_last_state()
        
        if last_state is not None:
            self._target_temperature = last_state.attributes['temperature']
            self._current_operation = last_state.attributes['operation_mode']
            self._current_fan_mode = last_state.attributes['fan_mode']

            if 'last_on_operation' in last_state.attributes:
                self._last_on_operation = last_state.attributes['last_on_operation']

        if self._temperature_sensor:
            async_track_state_change(self.hass, self._temperature_sensor, 
                                     self._async_temp_sensor_changed)

            temp_sensor_state = self.hass.states.get(self._temperature_sensor)
            if temp_sensor_state and temp_sensor_state.state != STATE_UNKNOWN:
                self._async_update_temp(temp_sensor_state)

        if self._humidity_sensor:
            async_track_state_change(self.hass, self._humidity_sensor, 
                                     self._async_humidity_sensor_changed)

            humidity_sensor_state = self.hass.states.get(self._humidity_sensor)
            if humidity_sensor_state and humidity_sensor_state.state != STATE_UNKNOWN:
                self._async_update_humidity(humidity_sensor_state)

        if self._power_sensor:
            async_track_state_change(self.hass, self._power_sensor, 
                                     self._async_power_sensor_changed)

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def state(self):
        """Return the current state."""
        if self._on_by_remote:
            return STATE_ON
        if self.current_operation != STATE_OFF:
            return self.current_operation
        return STATE_OFF

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def min_temp(self):
        """Return the polling state."""
        return self._min_temperature
        
    @property
    def max_temp(self):
        """Return the polling state."""
        return self._max_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._precision

    @property
    def precision(self):
        """Return the precision of the system."""
        return self._precision

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return self._operation_modes

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool."""
        return self._current_operation

    @property
    def last_on_operation(self):
        """Return the last non-idle operation ie. heat, cool."""
        return self._last_on_operation

    @property
    def fan_list(self):
        """Return the list of available fan modes."""
        return self._fan_modes

    @property
    def current_fan_mode(self):
        """Return the fan setting."""
        return self._current_fan_mode

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._current_humidity

    @property
    def is_on(self):
        return None

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def device_state_attributes(self) -> dict:
        """Platform specific attributes."""
        return {
            'last_on_operation': self._last_on_operation,
            'device_code': self._device_code,
            'manufacturer': self._manufacturer,
            'supported_models': self._supported_models,
            'supported_controller': self._supported_controller,
            'commands_encoding': self._commands_encoding,
        }

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        
        if temperature is None:
            return
            
        if temperature < self._min_temperature or temperature > self._max_temperature:
            _LOGGER.warning('The temperature value is out of min/max range') 
            return

        if self._precision == PRECISION_WHOLE:
            self._target_temperature = round(temperature)
        else:
            self._target_temperature = round(temperature, 1)
        
        if not self._current_operation.lower() == STATE_OFF:
            await self.send_command()
        await self.async_update_ha_state()

    async def async_set_operation_mode(self, operation_mode):
        """Set operation mode."""
        self._current_operation = operation_mode
        
        if not operation_mode == STATE_OFF:
            self._last_on_operation = operation_mode

        await self.send_command()
        await self.async_update_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        """Set fan mode."""
        self._current_fan_mode = fan_mode
        
        if not self._current_operation.lower() == STATE_OFF:
            await self.send_command()      
        await self.async_update_ha_state()

    async def async_turn_off(self):
        """Turn off."""
        await self.async_set_operation_mode(STATE_OFF)
        
    async def async_turn_on(self):
        """Turn on."""
        if self._last_on_operation is not None:
            await self.async_set_operation_mode(self._last_on_operation)
        else:
            await self.async_set_operation_mode(self._operation_modes[1])

    async def send_command(self):
        async with self._temp_lock:
            self._on_by_remote = False
            supported_controller = self._supported_controller
            commands_encoding = self._commands_encoding
            operation_mode = self._current_operation
            fan_mode = self._current_fan_mode
            target_temperature = '{0:g}'.format(self._target_temperature)

            if operation_mode.lower() == STATE_OFF:
                command = self._commands['off']
                _LOGGER.debug("Sending command Off")
            else:
                command = self._commands[operation_mode][fan_mode][target_temperature]
                _LOGGER.debug("Sending command %s%s%s", 
                                operation_mode.capitalize(), 
                                fan_mode.capitalize(), 
                                target_temperature)
            
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

            _LOGGER.debug("%s.%s %s", service_domain, service_name, service_data)
            await self.hass.services.async_call(service_domain, service_name, service_data)

    async def _async_temp_sensor_changed(self, entity_id, old_state, new_state):
        """Handle temperature sensor changes."""
        if new_state is None:
            return

        self._async_update_temp(new_state)
        await self.async_update_ha_state()

    async def _async_humidity_sensor_changed(self, entity_id, old_state, new_state):
        """Handle humidity sensor changes."""
        if new_state is None:
            return

        self._async_update_humidity(new_state)
        await self.async_update_ha_state()

    async def _async_power_sensor_changed(self, entity_id, old_state, new_state):
        """Handle power sensor changes."""
        if new_state is None:
            return

        if new_state.state == STATE_OFF and self._current_operation != STATE_OFF:
            self._current_operation = STATE_OFF
            await self.async_update_ha_state()

        if new_state.state == STATE_ON and self._current_operation == STATE_OFF:
            self._on_by_remote = True
            await self.async_update_ha_state()

    @callback
    def _async_update_temp(self, state):
        """Update thermostat with latest state from temperature sensor."""
        try:
            if state.state != STATE_UNKNOWN:
                self._current_temperature = float(state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from temperature sensor: %s", ex)

    @callback
    def _async_update_humidity(self, state):
        """Update thermostat with latest state from humidity sensor."""
        try:
            if state.state != STATE_UNKNOWN:
                self._current_humidity = float(state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from humidity sensor: %s", ex)
