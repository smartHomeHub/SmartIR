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
from homeassistant.helpers.event import async_track_state_change_event
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from . import COMPONENT_ABS_DIR, Helper
from .controller import get_controller
from .power_feedback import consumption_state_is_on, retry_with_feedback_backoff

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
CONF_POWER_CONSUMPTION_SENSOR = 'power_consumption_sensor'
CONF_POWER_CONSUMPTION_ON_THRESHOLD_WATTS = 'power_consumption_on_threshold_watts'
CONF_POWER_CONSUMPTION_RETRY_COUNT = "power_consumption_retry_count"
CONF_POWER_CONSUMPTION_RETRY_INITIAL_DELAY_SECONDS = (
    "power_consumption_retry_initial_delay_seconds"
)
CONF_POWER_CONSUMPTION_RETRY_BACKOFF_MULTIPLIER = (
    "power_consumption_retry_backoff_multiplier"
)
CONF_POWER_CONSUMPTION_RETRY_MAX_DELAY_SECONDS = (
    "power_consumption_retry_max_delay_seconds"
)

DEFAULT_POWER_CONSUMPTION_ON_THRESHOLD_WATTS = 10.0
DEFAULT_POWER_CONSUMPTION_RETRY_COUNT = 3
DEFAULT_POWER_CONSUMPTION_RETRY_INITIAL_DELAY_SECONDS = 2.0
DEFAULT_POWER_CONSUMPTION_RETRY_BACKOFF_MULTIPLIER = 1.5
DEFAULT_POWER_CONSUMPTION_RETRY_MAX_DELAY_SECONDS = 10.0

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
    vol.Optional(CONF_POWER_SENSOR_RESTORE_STATE, default=False): cv.boolean,
    vol.Optional(CONF_POWER_CONSUMPTION_SENSOR): cv.entity_id,
    vol.Optional(
        CONF_POWER_CONSUMPTION_ON_THRESHOLD_WATTS,
        default=DEFAULT_POWER_CONSUMPTION_ON_THRESHOLD_WATTS,
    ): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional(
        CONF_POWER_CONSUMPTION_RETRY_COUNT,
        default=DEFAULT_POWER_CONSUMPTION_RETRY_COUNT,
    ): vol.All(vol.Coerce(int), vol.Range(min=0)),
    vol.Optional(
        CONF_POWER_CONSUMPTION_RETRY_INITIAL_DELAY_SECONDS,
        default=DEFAULT_POWER_CONSUMPTION_RETRY_INITIAL_DELAY_SECONDS,
    ): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional(
        CONF_POWER_CONSUMPTION_RETRY_BACKOFF_MULTIPLIER,
        default=DEFAULT_POWER_CONSUMPTION_RETRY_BACKOFF_MULTIPLIER,
    ): vol.All(vol.Coerce(float), vol.Range(min=1)),
    vol.Optional(
        CONF_POWER_CONSUMPTION_RETRY_MAX_DELAY_SECONDS,
        default=DEFAULT_POWER_CONSUMPTION_RETRY_MAX_DELAY_SECONDS,
    ): vol.All(vol.Coerce(float), vol.Range(min=0)),
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
        self._power_consumption_sensor = config.get(CONF_POWER_CONSUMPTION_SENSOR)
        self._power_consumption_on_threshold_watts = config.get(
            CONF_POWER_CONSUMPTION_ON_THRESHOLD_WATTS
        )
        self._power_consumption_retry_count = config.get(
            CONF_POWER_CONSUMPTION_RETRY_COUNT
        )
        self._power_consumption_retry_initial_delay_seconds = config.get(
            CONF_POWER_CONSUMPTION_RETRY_INITIAL_DELAY_SECONDS
        )
        self._power_consumption_retry_backoff_multiplier = config.get(
            CONF_POWER_CONSUMPTION_RETRY_BACKOFF_MULTIPLIER
        )
        self._power_consumption_retry_max_delay_seconds = config.get(
            CONF_POWER_CONSUMPTION_RETRY_MAX_DELAY_SECONDS
        )
        self._last_consumption_effective_on = None

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
        self._command_generation = 0
        self._consumption_feedback_hold_count = 0

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
            self._current_fan_mode = last_state.attributes.get(
                'fan_mode', self._current_fan_mode)
            self._current_swing_mode = last_state.attributes.get('swing_mode')
            if self._current_swing_mode is None and self._swing_modes:
                self._current_swing_mode = self._swing_modes[0]
            self._target_temperature = last_state.attributes.get(
                ATTR_TEMPERATURE, self._target_temperature)

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

        if self._power_sensor and self._power_consumption_sensor:
            _LOGGER.warning(
                "%s: both %s and %s are set; using %s only",
                self.name,
                CONF_POWER_SENSOR,
                CONF_POWER_CONSUMPTION_SENSOR,
                CONF_POWER_SENSOR,
            )

        if self._power_sensor:
            async_track_state_change_event(self.hass, self._power_sensor, 
                                           self._async_power_sensor_changed)
        elif self._power_consumption_sensor:
            async_track_state_change_event(
                self.hass,
                self._power_consumption_sensor,
                self._async_power_consumption_sensor_changed,
            )
            cons_state = self.hass.states.get(self._power_consumption_sensor)
            if cons_state is not None:
                self._update_from_power_consumption(cons_state)

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
        hvac_mode = kwargs.get(ATTR_HVAC_MODE)  
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

        if hvac_mode:
            await self.async_set_hvac_mode(hvac_mode)
            return
        
        if not self._hvac_mode.lower() == HVACMode.OFF:
            self.async_write_ha_state()
            await self.send_command()

        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        self._hvac_mode = hvac_mode
        
        if not hvac_mode == HVACMode.OFF:
            self._last_on_operation = hvac_mode

        self.async_write_ha_state()
        await self.send_command()
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        """Set fan mode."""
        self._current_fan_mode = fan_mode
        
        if not self._hvac_mode.lower() == HVACMode.OFF:
            self.async_write_ha_state()
            await self.send_command()      
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode):
        """Set swing mode."""
        self._current_swing_mode = swing_mode

        if not self._hvac_mode.lower() == HVACMode.OFF:
            self.async_write_ha_state()
            await self.send_command()
        self.async_write_ha_state()

    async def async_turn_off(self):
        """Turn off."""
        await self.async_set_hvac_mode(HVACMode.OFF)
        
    async def async_turn_on(self):
        """Turn on."""
        if self._last_on_operation is not None:
            await self.async_set_hvac_mode(self._last_on_operation)
        else:
            await self.async_set_hvac_mode(self._operation_modes[1])

    def _consumption_feedback_enabled(self) -> bool:
        """Retries use consumption feedback only when binary power_sensor is not set."""
        return self._power_sensor is None and self._power_consumption_sensor is not None

    def _read_consumption_effective_power(self):
        """Return current on/off from power consumption or None if unavailable."""
        if not self._consumption_feedback_enabled():
            return None
        power_state = self.hass.states.get(self._power_consumption_sensor)
        if power_state is None:
            return None
        return consumption_state_is_on(
            power_state, self._power_consumption_on_threshold_watts
        )

    async def _send_current_climate_command(self, operation_mode, fan_mode, swing_mode, target_temperature):
        """Send the current climate command sequence once."""
        async with self._temp_lock:
            self._on_by_remote = False
            if operation_mode.lower() == HVACMode.OFF:
                await self._controller.send(self._commands['off'])
                return

            if 'on' in self._commands:
                await self._controller.send(self._commands['on'])
                await asyncio.sleep(self._delay)

            if self._support_swing:
                await self._controller.send(
                    self._commands[operation_mode][fan_mode][swing_mode][target_temperature]
                )
            else:
                await self._controller.send(
                    self._commands[operation_mode][fan_mode][target_temperature]
                )

    async def _retry_consumption_feedback_if_needed(
        self, desired_is_on: bool, command_generation: int, resend_command
    ):
        """Retry command with backoff until consumption feedback matches desired state."""
        if not self._consumption_feedback_enabled():
            return

        def should_skip_retry() -> bool:
            return command_generation != self._command_generation

        def is_feedback_matching() -> bool:
            current_is_on = self._read_consumption_effective_power()
            return current_is_on is not None and current_is_on == desired_is_on

        matched = await retry_with_feedback_backoff(
            retry_count=self._power_consumption_retry_count,
            initial_delay_seconds=self._power_consumption_retry_initial_delay_seconds,
            backoff_multiplier=self._power_consumption_retry_backoff_multiplier,
            max_delay_seconds=self._power_consumption_retry_max_delay_seconds,
            should_skip_retry=should_skip_retry,
            is_feedback_matching=is_feedback_matching,
            resend_command=resend_command,
        )
        if matched or should_skip_retry():
            return
        measured_is_on = self._read_consumption_effective_power()
        if measured_is_on is not None:
            self._last_consumption_effective_on = measured_is_on
            self._apply_effective_power(measured_is_on)

    async def send_command(self):
        self._command_generation += 1
        command_generation = self._command_generation
        operation_mode = self._hvac_mode
        fan_mode = self._current_fan_mode
        swing_mode = self._current_swing_mode
        target_temperature = '{0:g}'.format(self._target_temperature)
        desired_is_on = operation_mode.lower() != HVACMode.OFF

        async def resend_command():
            try:
                await self._send_current_climate_command(
                    operation_mode, fan_mode, swing_mode, target_temperature
                )
            except Exception as e:
                _LOGGER.exception(e)

        consumption_hold = self._consumption_feedback_enabled()
        if consumption_hold:
            self._consumption_feedback_hold_count += 1
        try:
            await resend_command()
            await self._retry_consumption_feedback_if_needed(
                desired_is_on, command_generation, resend_command
            )
        finally:
            if consumption_hold:
                self._consumption_feedback_hold_count -= 1
                
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
    def _apply_effective_power(self, is_on: bool) -> None:
        """Sync climate state from a binary on/off (power present or not)."""
        if is_on and self._hvac_mode == HVACMode.OFF:
            self._on_by_remote = True
            if self._power_sensor_restore_state and self._last_on_operation is not None:
                self._hvac_mode = self._last_on_operation
            else:
                self._hvac_mode = STATE_ON
            self.async_write_ha_state()
        elif not is_on:
            self._on_by_remote = False
            if self._hvac_mode != HVACMode.OFF:
                self._hvac_mode = HVACMode.OFF
            self.async_write_ha_state()

    @callback
    def _update_from_power_consumption(self, state) -> None:
        """Apply threshold to power sensor; only act on effective on/off change."""
        if self._consumption_feedback_hold_count > 0:
            return
        is_on = consumption_state_is_on(
            state, self._power_consumption_on_threshold_watts
        )
        if self._last_consumption_effective_on is not None and is_on == self._last_consumption_effective_on:
            return
        self._last_consumption_effective_on = is_on
        self._apply_effective_power(is_on)

    @callback
    async def _async_power_consumption_sensor_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        new_state = event.data["new_state"]
        if new_state is None:
            return
        self._update_from_power_consumption(new_state)

    @callback
    async def _async_power_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
    
        if new_state is None:
            return

        old_state = event.data["old_state"]
        if old_state is not None and new_state.state == old_state.state:
            return

        is_on = new_state.state == STATE_ON
        self._apply_effective_power(is_on)

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