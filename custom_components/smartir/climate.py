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
CONF_RECEIVER_EVENT = 'receiver_event'
CONF_RECEIVER_DEVICE_ID = 'receiver_device_id'

RECEIVER_MIN_FRAME_LENGTH = 20
RECEIVER_LONG_SPACE_THRESHOLD = -700
RECEIVER_END_OF_FRAME_THRESHOLD = -5000
RECEIVER_MAX_BIT_ERRORS = 0

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
    vol.Optional(CONF_RECEIVER_EVENT): cv.string,
    vol.Optional(CONF_RECEIVER_DEVICE_ID): cv.string
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
        self._receiver_event = config.get(CONF_RECEIVER_EVENT)
        self._receiver_device_id = config.get(CONF_RECEIVER_DEVICE_ID)

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
        self._swing_commands = device_data.get('swingCommands', {})
        self._commands = device_data['commands']
        self._receiver_frames = self._build_receiver_frames(self._commands)

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

        if self._receiver_event and self._receiver_device_id:
            self.async_on_remove(
                self.hass.bus.async_listen(
                    self._receiver_event,
                    self._async_received_ir_frame,
                )
            )
        elif self._receiver_event or self._receiver_device_id:
            _LOGGER.warning(
                "Both receiver_event and receiver_device_id are required for %s",
                self.name,
            )

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
            await self.send_command()

        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        self._hvac_mode = hvac_mode
        
        if not hvac_mode == HVACMode.OFF:
            self._last_on_operation = hvac_mode

        await self.send_command()
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        """Set fan mode."""
        self._current_fan_mode = fan_mode
        
        if not self._hvac_mode.lower() == HVACMode.OFF:
            await self.send_command()      
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode):
        """Set swing mode."""
        self._current_swing_mode = swing_mode

        if not self._hvac_mode.lower() == HVACMode.OFF:
            swing_command = self._swing_commands.get(swing_mode)
            if swing_command:
                await self._controller.send(swing_command)
            else:
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

    async def send_command(self):
        async with self._temp_lock:
            try:
                self._on_by_remote = False
                operation_mode = self._hvac_mode
                fan_mode = self._current_fan_mode
                swing_mode = self._current_swing_mode
                target_temperature = '{0:g}'.format(self._target_temperature)
                if operation_mode.lower() == HVACMode.OFF:
                    await self._controller.send(self._commands['off'])
                    return

                if 'on' in self._commands:
                    await self._controller.send(self._commands['on'])
                    await asyncio.sleep(self._delay)

                if self._support_swing == True and not self._swing_commands:
                    await self._controller.send(
                        self._commands[operation_mode][fan_mode][swing_mode][target_temperature])
                else:
                    await self._controller.send(
                        self._commands[operation_mode][fan_mode][target_temperature])

            except Exception as e:
                _LOGGER.exception(e)

    @staticmethod
    def _build_receiver_frames(commands):
        """Flatten the SmartIR command tree into raw frames and their state."""
        frames = []

        def walk(node, metadata):
            if isinstance(node, str):
                try:
                    frames.append({
                        'raw': json.loads(node),
                        'metadata': metadata.copy(),
                    })
                except json.JSONDecodeError:
                    _LOGGER.warning("Invalid raw command in SmartIR device code")
                return

            if not isinstance(node, dict):
                return

            for key, value in node.items():
                new_metadata = metadata.copy()
                if not metadata and key == 'off':
                    new_metadata['command'] = 'off'
                elif not metadata:
                    new_metadata['mode'] = key
                elif 'mode' in metadata and 'fan' not in metadata:
                    new_metadata['fan'] = key
                elif 'fan' in metadata:
                    try:
                        new_metadata['temperature'] = float(key)
                    except ValueError:
                        new_metadata['temperature'] = key
                walk(value, new_metadata)

        walk(commands, {})
        return frames

    @staticmethod
    def _frame_signature(frame):
        """Convert Fujitsu raw timings to its stable short/long-space bit stream."""
        signature = []
        for index in range(2, len(frame) - 1, 2):
            space = frame[index + 1]
            if space <= RECEIVER_END_OF_FRAME_THRESHOLD:
                break
            signature.append(space <= RECEIVER_LONG_SPACE_THRESHOLD)
        return tuple(signature)

    @classmethod
    def _compare_received_frame(cls, received, candidate):
        """Compare decoded Fujitsu bits, ignoring harmless timing jitter."""
        received_signature = cls._frame_signature(received)
        candidate_signature = cls._frame_signature(candidate)
        if len(received_signature) != len(candidate_signature):
            return None
        if not received_signature:
            return None

        bit_errors = sum(
            received_bit != candidate_bit
            for received_bit, candidate_bit in zip(
                received_signature, candidate_signature
            )
        )
        return -bit_errors, bit_errors, len(received_signature)

    @callback
    def _async_received_ir_frame(self, event):
        """Update this climate entity from an IR frame received by ESPHome."""
        received_device_id = event.data.get('device_id')
        if received_device_id != self._receiver_device_id:
            _LOGGER.warning(
                "Ignoring IR event for %s: expected device_id=%s, received=%s",
                self.name,
                self._receiver_device_id,
                received_device_id,
            )
            return

        # The ESPHome AR-DB1 decoder has already validated its header and
        # checksum.  Do not fall back to fuzzy raw-frame matching for this
        # source: incomplete frames must leave the current state untouched.
        if event.data.get('protocol') == 'fujitsu_ardb1':
            decoded = event.data.get('decoded')
            if decoded is not True and str(decoded).lower() not in ('1', 'true'):
                _LOGGER.debug("Rejected incomplete AR-DB1 frame for %s", self.name)
                return

            command = event.data.get('command')
            if command == 'swing_toggle':
                if not self._swing_modes:
                    _LOGGER.warning("Received AR-DB1 swing command for %s without swing modes", self.name)
                    return
                self._current_swing_mode = (
                    'off' if self._current_swing_mode == 'vertical' else 'vertical'
                )
                _LOGGER.info("Received AR-DB1 swing toggle for %s: %s", self.name, self._current_swing_mode)
            elif command == 'off':
                self._hvac_mode = HVACMode.OFF
                _LOGGER.info("Received AR-DB1 OFF command for %s", self.name)
            else:
                mode = event.data.get('mode')
                fan_mode = event.data.get('fan')
                temperature = event.data.get('temperature')
                if mode not in self._operation_modes or fan_mode not in self._fan_modes:
                    _LOGGER.warning(
                        "Received unsupported AR-DB1 state for %s: mode=%s fan=%s",
                        self.name, mode, fan_mode,
                    )
                    return
                try:
                    temperature = float(temperature)
                except (TypeError, ValueError):
                    _LOGGER.warning("Received invalid AR-DB1 temperature for %s", self.name)
                    return

                self._hvac_mode = mode
                self._last_on_operation = mode
                self._current_fan_mode = fan_mode
                self._target_temperature = temperature
                swing_mode = event.data.get('swing_mode')
                if swing_mode in (self._swing_modes or []):
                    self._current_swing_mode = swing_mode
                _LOGGER.info(
                    "Received AR-DB1 state for %s: mode=%s fan=%s temperature=%s swing=%s",
                    self.name, mode, fan_mode, temperature, self._current_swing_mode,
                )

            self.async_write_ha_state()
            return

        raw_string = event.data.get('raw')
        if not isinstance(raw_string, str):
            return

        _LOGGER.warning(
            "Processing received IR frame for %s: %d timings",
            self.name,
            len(raw_string.split(',')),
        )

        try:
            received = [int(value.strip()) for value in raw_string.split(',')]
        except ValueError:
            _LOGGER.warning("Unable to parse received IR frame for %s", self.name)
            return

        if len(received) < RECEIVER_MIN_FRAME_LENGTH:
            return

        best = None
        best_metadata = []
        for frame in self._receiver_frames:
            result = self._compare_received_frame(received, frame['raw'])
            if result is None:
                continue
            if best is None or result[0] > best['score']:
                best = {
                    'metadata': frame['metadata'],
                    'score': result[0],
                    'bit_errors': result[1],
                    'bit_count': result[2],
                }
                best_metadata = [frame['metadata']]
            elif result[0] == best['score']:
                best_metadata.append(frame['metadata'])

        if best is None or best['bit_errors'] > RECEIVER_MAX_BIT_ERRORS:
            if best is None:
                _LOGGER.warning(
                    "Received IR frame for %s has no complete Fujitsu bit signature",
                    self.name,
                )
            else:
                _LOGGER.warning(
                    "Received IR frame rejected for %s: candidate=%s bit_errors=%d/%d",
                    self.name,
                    best['metadata'],
                    best['bit_errors'],
                    best['bit_count'],
                )
            return

        distinct_matches = {
            json.dumps(metadata, sort_keys=True)
            for metadata in best_metadata
        }
        if len(distinct_matches) != 1:
            _LOGGER.warning(
                "Received IR frame for %s is ambiguous and was ignored: %s",
                self.name,
                sorted(distinct_matches),
            )
            return

        metadata = best_metadata[0]
        if metadata.get('command') == 'off':
            self._hvac_mode = HVACMode.OFF
        else:
            mode = metadata.get('mode')
            fan_mode = metadata.get('fan')
            temperature = metadata.get('temperature')
            if mode not in self._operation_modes or fan_mode not in self._fan_modes:
                _LOGGER.warning("Received IR frame has unsupported SmartIR state: %s", metadata)
                return

            self._hvac_mode = mode
            self._last_on_operation = mode
            self._current_fan_mode = fan_mode
            if isinstance(temperature, (int, float)):
                self._target_temperature = temperature

        _LOGGER.warning(
            "Received IR match for %s: %s (bit_errors=%d/%d)",
            self.name,
            metadata,
            best['bit_errors'],
            best['bit_count'],
        )
        self.async_write_ha_state()
                
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
