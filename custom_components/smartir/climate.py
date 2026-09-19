import asyncio
import aiofiles
import json
import logging
import os.path

import voluptuous as vol

from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    ClimateEntityFeature, HVACMode, HVAC_MODES, ATTR_HVAC_MODE)
from homeassistant.const import (
    CONF_NAME, STATE_ON, STATE_OFF, STATE_UNKNOWN, STATE_UNAVAILABLE, ATTR_TEMPERATURE,
    PRECISION_TENTHS, PRECISION_HALVES, PRECISION_WHOLE)
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.event import async_track_state_change, async_track_state_change_event
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from . import COMPONENT_ABS_DIR, Helper
from .controller import get_controller

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "SmartIR Climate"
DEFAULT_DELAY = 0.5

CONF_UNIQUE_ID = 'unique_id'
CONF_DEVICE_CODE = 'device_code'
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"
CONF_TEMPERATURE_SENSOR = 'temperature_sensor'
CONF_HUMIDITY_SENSOR = 'humidity_sensor'
CONF_POWER_SENSOR = 'power_sensor'
CONF_POWER_SENSOR_RESTORE_STATE = 'power_sensor_restore_state'

SUPPORT_FLAGS = (
    ClimateEntityFeature.TURN_OFF |
    ClimateEntityFeature.TURN_ON |
    ClimateEntityFeature.TARGET_TEMPERATURE | 
    ClimateEntityFeature.FAN_MODE
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_UNIQUE_ID): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_DEVICE_CODE): cv.positive_int,
    vol.Required(CONF_CONTROLLER_DATA): cv.string,
    vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): cv.positive_float,
    vol.Optional(CONF_TEMPERATURE_SENSOR): cv.entity_id,
    vol.Optional(CONF_HUMIDITY_SENSOR): cv.entity_id,
    vol.Optional(CONF_POWER_SENSOR): cv.entity_id,
    vol.Optional(CONF_POWER_SENSOR_RESTORE_STATE, default=False): cv.boolean
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the IR Climate platform."""
    _LOGGER.debug("Setting up the smartir platform")
    device_code = config.get(CONF_DEVICE_CODE)
    device_files_subdir = os.path.join('codes', 'climate')
    device_files_absdir = os.path.join(COMPONENT_ABS_DIR, device_files_subdir)

    if not os.path.isdir(device_files_absdir):
        os.makedirs(device_files_absdir)

    device_json_filename = str(device_code) + '.json'
    device_json_path = os.path.join(device_files_absdir, device_json_filename)

    if not os.path.exists(device_json_path):
        _LOGGER.warning("Couldn't find the device Json file. The component will " \
                        "try to download it from the GitHub repo.")

        try:
            codes_source = ("https://raw.githubusercontent.com/"
                            "smartHomeHub/SmartIR/master/"
                            "codes/climate/{}.json")

            await Helper.downloader(codes_source.format(device_code), device_json_path)
        except Exception:
            _LOGGER.error("There was an error while downloading the device Json file. " \
                          "Please check your internet connection or if the device code " \
                          "exists on GitHub. If the problem still exists please " \
                          "place the file manually in the proper directory.")
            return

    try:
        async with aiofiles.open(device_json_path, mode='r') as j:
            _LOGGER.debug(f"loading json file {device_json_path}")
            content = await j.read()
            device_data = json.loads(content)
            _LOGGER.debug(f"{device_json_path} file loaded")
    except Exception:
        _LOGGER.error("The device JSON file is invalid")
        return

    async_add_entities([SmartIRClimate(
        hass, config, device_data
    )])

class SmartIRClimate(ClimateEntity, RestoreEntity):
    def __init__(self, hass, config, device_data):
        _LOGGER.debug(f"SmartIRClimate init started for device {config.get(CONF_NAME)} supported models {device_data['supportedModels']}")
        self.hass = hass
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)
        self._device_code = config.get(CONF_DEVICE_CODE)
        self._controller_data = config.get(CONF_CONTROLLER_DATA)
        self._delay = config.get(CONF_DELAY)
        self._temperature_sensor = config.get(CONF_TEMPERATURE_SENSOR)
        self._humidity_sensor = config.get(CONF_HUMIDITY_SENSOR)
        self._power_sensor = config.get(CONF_POWER_SENSOR)
        self._power_sensor_restore_state = config.get(CONF_POWER_SENSOR_RESTORE_STATE)

        self._manufacturer = device_data['manufacturer']
        self._supported_models = device_data['supportedModels']
        self._supported_controller = device_data['supportedController']
        self._commands_encoding = device_data['commandsEncoding']
        self._min_temperature = device_data['minTemperature']
        self._max_temperature = device_data['maxTemperature']
        self._precision = device_data['precision']

        valid_hvac_modes = [x for x in device_data['operationModes'] if x in HVAC_MODES]

        self._operation_modes = [HVACMode.OFF] + valid_hvac_modes
        self._fan_modes = device_data['fanModes']
        self._swing_modes = device_data.get('swingModes')
        self._commands = device_data['commands']

        self._target_temperature = self._min_temperature
        self._hvac_mode = HVACMode.OFF
        self._current_fan_mode = self._fan_modes[0]
        self._current_swing_mode = None
        self._last_on_operation = None

        self._current_temperature = None
        self._current_humidity = None

        self._unit = hass.config.units.temperature_unit
        
        #Supported features
        self._support_flags = SUPPORT_FLAGS
        self._support_swing = False

        if self._swing_modes:
            self._support_flags = self._support_flags | ClimateEntityFeature.SWING_MODE
            self._current_swing_mode = self._swing_modes[0]
            self._support_swing = True

        self._temp_lock = asyncio.Lock()
        self._on_by_remote = False

        #Init the IR/RF controller
        self._controller = get_controller(
            self.hass,
            self._supported_controller,
            self._commands_encoding,
            self._controller_data,
            self._delay)
            
    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        _LOGGER.debug(f"async_added_to_hass {self} {self.name} {self.supported_features}")
    
        last_state = await self.async_get_last_state()
        
        if last_state is not None:
            self._hvac_mode = last_state.state
            self._current_fan_mode = last_state.attributes['fan_mode']
            self._current_swing_mode = last_state.attributes.get('swing_mode')
            self._target_temperature = last_state.attributes['temperature']

            if 'last_on_operation' in last_state.attributes:
                self._last_on_operation = last_state.attributes['last_on_operation']

        if self._temperature_sensor:
            async_track_state_change_event(self.hass, self._temperature_sensor, 
                                           self._async_temp_sensor_changed)

            temp_sensor_state = self.hass.states.get(self._temperature_sensor)
            if temp_sensor_state and temp_sensor_state.state != STATE_UNKNOWN:
                self._async_update_temp(temp_sensor_state)

        if self._humidity_sensor:
            async_track_state_change_event(self.hass, self._humidity_sensor, 
                                           self._async_humidity_sensor_changed)

            humidity_sensor_state = self.hass.states.get(self._humidity_sensor)
            if humidity_sensor_state and humidity_sensor_state.state != STATE_UNKNOWN:
                self._async_update_humidity(humidity_sensor_state)

        if self._power_sensor:
            async_track_state_change_event(self.hass, self._power_sensor, 
                                           self._async_power_sensor_changed)

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def state(self):
        """Return the current state."""
        if self.hvac_mode != HVACMode.OFF:
            return self.hvac_mode
        return HVACMode.OFF

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
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._operation_modes

    @property
    def hvac_mode(self):
        """Return hvac mode ie. heat, cool."""
        return self._hvac_mode

    @property
    def last_on_operation(self):
        """Return the last non-idle operation ie. heat, cool."""
        return self._last_on_operation

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return self._fan_modes

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return self._current_fan_mode

    @property
    def swing_modes(self):
        """Return the swing modes currently supported for this device."""
        return self._swing_modes

    @property
    def swing_mode(self):
        """Return the current swing mode."""
        return self._current_swing_mode

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._current_humidity

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def extra_state_attributes(self):
        """Platform specific attributes."""
        return {
            'last_on_operation': self._last_on_operation,
            'device_code': self._device_code,
            'manufacturer': self._manufacturer,
            'supported_models': self._supported_models,
            'supported_controller': self._supported_controller,
            'commands_encoding': self._commands_encoding
        }

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._async_apply_settings(
            temperature=temperature, hvac_mode=kwargs.get(ATTR_HVAC_MODE))

    async def async_set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        await self._async_apply_settings(hvac_mode=hvac_mode)

    async def async_set_fan_mode(self, fan_mode):
        """Set fan mode."""
        await self._async_apply_settings(fan_mode=fan_mode)

    async def async_set_swing_mode(self, swing_mode):
        """Set swing mode."""
        await self._async_apply_settings(swing_mode=swing_mode)

    async def async_turn_off(self):
        """Turn off."""
        await self.async_set_hvac_mode(HVACMode.OFF)
        
    async def async_turn_on(self):
        """Turn on."""
        await self._async_apply_settings(turn_on=True)

    async def _async_apply_settings(self, *, hvac_mode=None, temperature=None,
                                   fan_mode=None, swing_mode=None, turn_on=False):
        """Send one requested state before committing its assumed settings."""
        async with self._temp_lock:
            if turn_on:
                hvac_mode = self._last_on_operation
                if hvac_mode is None:
                    if len(self._operation_modes) < 2:
                        raise ServiceValidationError("No supported operation mode")
                    hvac_mode = self._operation_modes[1]

            if hvac_mode is not None and hvac_mode not in self._operation_modes:
                raise ServiceValidationError(f"Unsupported HVAC mode: {hvac_mode}")
            if fan_mode is not None and fan_mode not in self._fan_modes:
                raise ServiceValidationError(f"Unsupported fan mode: {fan_mode}")
            if swing_mode is not None and swing_mode not in (self._swing_modes or []):
                raise ServiceValidationError(f"Unsupported swing mode: {swing_mode}")
            if temperature is not None:
                if not self._min_temperature <= temperature <= self._max_temperature:
                    raise ServiceValidationError("Temperature is out of min/max range")
                if self._precision == PRECISION_WHOLE:
                    temperature = round(temperature)
                else:
                    temperature = round(temperature, 1)

            operation_mode = self._hvac_mode if hvac_mode is None else hvac_mode
            target_temperature = self._target_temperature if temperature is None else temperature
            fan_mode = self._current_fan_mode if fan_mode is None else fan_mode
            swing_mode = self._current_swing_mode if swing_mode is None else swing_mode

            # Settings-only changes while off are remembered without transmitting.
            if hvac_mode is not None or operation_mode != HVACMode.OFF:
                await self.send_command(
                    operation_mode, fan_mode, swing_mode, target_temperature)
                self._on_by_remote = False

            self._hvac_mode = operation_mode
            self._target_temperature = target_temperature
            self._current_fan_mode = fan_mode
            self._current_swing_mode = swing_mode
            if hvac_mode is not None and hvac_mode != HVACMode.OFF:
                self._last_on_operation = hvac_mode
            self.async_write_ha_state()

    async def send_command(self, operation_mode, fan_mode, swing_mode, temperature):
        """Send a selected state. The caller holds the transaction lock."""
        try:
            if operation_mode == HVACMode.OFF:
                command = self._commands['off']
            else:
                target_temperature = '{0:g}'.format(temperature)
                if self._support_swing:
                    command = self._commands[operation_mode][fan_mode][swing_mode][target_temperature]
                else:
                    command = self._commands[operation_mode][fan_mode][target_temperature]
            on_command = self._commands.get('on') if operation_mode != HVACMode.OFF else None
        except (KeyError, TypeError, ValueError) as err:
            raise ServiceValidationError(
                f"No command for HVAC mode {operation_mode}, fan {fan_mode}, "
                f"swing {swing_mode}, temperature {temperature}") from err

        commands = []
        if operation_mode != HVACMode.OFF and 'on' in self._commands:
            commands.append(on_command)
        commands.append(command)
        for selected_command in commands:
            codes = selected_command if isinstance(selected_command, list) else [selected_command]
            if not codes or any(not isinstance(code, str) or not code for code in codes):
                raise ServiceValidationError("IR commands must be nonempty strings or lists of strings")

        # Prepare the entire sequence before a preamble can operate the device.
        prepared = [self._controller.prepare(selected) for selected in commands]
        try:
            for index, payload in enumerate(prepared):
                if index:
                    await asyncio.sleep(self._delay)
                await self._controller.send_prepared(payload)
        except HomeAssistantError:
            raise
        except Exception as err:
            raise HomeAssistantError("Failed to send climate command") from err
                
    @callback
    async def _async_temp_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        """Handle temperature sensor changes."""
        new_state = event.data["new_state"]        

        if new_state is None:
            return

        self._async_update_temp(new_state)
        self.async_write_ha_state()

    @callback
    async def _async_humidity_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        """Handle humidity sensor changes."""
        new_state = event.data["new_state"]

        if new_state is None:
            return

        self._async_update_humidity(new_state)
        self.async_write_ha_state()
        
    @callback
    async def _async_power_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
    
        if new_state is None:
            return

        if old_state is not None and new_state.state == old_state.state:
            return

        # Apply power observations after any in-flight requested-state transaction.
        async with self._temp_lock:
            if new_state.state == STATE_ON and self._hvac_mode == HVACMode.OFF:
                self._on_by_remote = True
                if self._power_sensor_restore_state == True and self._last_on_operation is not None:
                    self._hvac_mode = self._last_on_operation
                else:
                    self._hvac_mode = STATE_ON

                self.async_write_ha_state()

            if new_state.state == STATE_OFF:
                self._on_by_remote = False
                if self._hvac_mode != HVACMode.OFF:
                    self._hvac_mode = HVACMode.OFF
                self.async_write_ha_state()

    @callback
    def _async_update_temp(self, state):
        """Update thermostat with latest state from temperature sensor."""
        try:
            if state.state != STATE_UNKNOWN and state.state != STATE_UNAVAILABLE:
                self._current_temperature = float(state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from temperature sensor: %s", ex)

    @callback
    def _async_update_humidity(self, state):
        """Update thermostat with latest state from humidity sensor."""
        try:
            if state.state != STATE_UNKNOWN and state.state != STATE_UNAVAILABLE:
                self._current_humidity = float(state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from humidity sensor: %s", ex)