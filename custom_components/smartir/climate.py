import asyncio
import logging

import voluptuous as vol
from numbers import Number

from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
    HVAC_MODES,
    ATTR_HVAC_MODE,
)
from homeassistant.const import (
    CONF_NAME,
    STATE_ON,
    STATE_OFF,
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    PRECISION_HALVES,
    PRECISION_WHOLE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change_event, async_call_later
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.unit_conversion import TemperatureConverter
from . import DeviceData
from .controller import get_controller

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "SmartIR Climate"
DEFAULT_DELAY = 0.5
DEFAULT_POWER_SENSOR_DELAY = 10

CONF_UNIQUE_ID = "unique_id"
CONF_DEVICE_CODE = "device_code"
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_POWER_SENSOR = "power_sensor"
CONF_POWER_SENSOR_DELAY = "power_sensor_delay"
CONF_POWER_SENSOR_RESTORE_STATE = "power_sensor_restore_state"

PRECISION_DOUBLE = 2

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_DEVICE_CODE): cv.positive_int,
        vol.Required(CONF_CONTROLLER_DATA): cv.string,
        vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): cv.positive_float,
        vol.Optional(CONF_TEMPERATURE_SENSOR): cv.entity_id,
        vol.Optional(CONF_HUMIDITY_SENSOR): cv.entity_id,
        vol.Optional(CONF_POWER_SENSOR): cv.entity_id,
        vol.Optional(
            CONF_POWER_SENSOR_DELAY, default=DEFAULT_POWER_SENSOR_DELAY
        ): cv.positive_int,
        vol.Optional(CONF_POWER_SENSOR_RESTORE_STATE, default=True): cv.boolean,
    }
)


async def async_setup_platform(
    hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None
):
    """Set up the IR Climate platform."""
    _LOGGER.debug("Setting up the SmartIR climate platform")
    if not (
        device_data := await DeviceData.load_file(
            config.get(CONF_DEVICE_CODE),
            "climate",
            {
                "hvac_modes": [mode for mode in HVAC_MODES if mode != HVACMode.OFF],
            },
            hass,
        )
    ):
        _LOGGER.error("SmartIR climate device data init failed!")
        return

    async_add_entities([SmartIRClimate(hass, config, device_data)])


class SmartIRClimate(ClimateEntity, RestoreEntity):
    _attr_should_poll = False
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, hass, config, device_data):
        _LOGGER.debug(
            "SmartIRClimate init started for device %s supported models %s",
            config.get(CONF_NAME),
            device_data["supportedModels"],
        )
        self.hass = hass
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)
        self._device_code = config.get(CONF_DEVICE_CODE)
        self._controller_data = config.get(CONF_CONTROLLER_DATA)
        self._delay = config.get(CONF_DELAY)
        self._temperature_sensor = config.get(CONF_TEMPERATURE_SENSOR)
        self._humidity_sensor = config.get(CONF_HUMIDITY_SENSOR)
        self._power_sensor = config.get(CONF_POWER_SENSOR)
        self._power_sensor_delay = config.get(CONF_POWER_SENSOR_DELAY)
        self._power_sensor_restore_state = config.get(CONF_POWER_SENSOR_RESTORE_STATE)
        self._temperature_unit = hass.config.units.temperature_unit

        self._state = STATE_UNKNOWN
        self._hvac_mode = None
        self._preset_mode = None
        self._fan_mode = None
        self._swing_mode = None
        self._hvac_action = None
        self._on_by_remote = False
        self._current_temperature = None
        self._current_humidity = None
        self._support_flags = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        self._power_sensor_check_expect = None
        self._power_sensor_check_cancel = None

        self._manufacturer = device_data["manufacturer"]
        self._supported_models = device_data["supportedModels"]
        self._supported_controller = device_data["supportedController"]
        self._commands_encoding = device_data["commandsEncoding"]
        self._commands = device_data["commands"]

        # current temperature sensor precision
        self._ha_temperature_unit = hass.config.units.temperature_unit
        if self._ha_temperature_unit == UnitOfTemperature.FAHRENHEIT:
            self._precision = PRECISION_WHOLE
        else:
            self._precision = PRECISION_TENTHS

        # device temperature units
        if device_data["temperatureUnit"] == "F":
            self._data_temperature_unit = UnitOfTemperature.FAHRENHEIT
        elif device_data["temperatureUnit"] == "K":
            self._data_temperature_unit = UnitOfTemperature.KELVIN
        elif device_data["temperatureUnit"] == "C":
            self._data_temperature_unit = UnitOfTemperature.CELSIUS

        # target temperature steps
        self._data_temp_step = device_data["precision"]
        if self._data_temperature_unit in [
            UnitOfTemperature.CELSIUS,
            UnitOfTemperature.KELVIN,
        ]:
            if self._ha_temperature_unit == UnitOfTemperature.FAHRENHEIT:
                if self._data_temp_step == PRECISION_TENTHS:
                    self._temp_step = PRECISION_HALVES
                elif self._data_temp_step == PRECISION_HALVES:
                    self._temp_step = PRECISION_WHOLE
                else:
                    self._temp_step = PRECISION_DOUBLE
            else:
                self._temp_step = self._data_temp_step
        elif self._data_temperature_unit == UnitOfTemperature.FAHRENHEIT:
            if self._ha_temperature_unit in [
                UnitOfTemperature.CELSIUS,
                UnitOfTemperature.KELVIN,
            ]:
                if self._data_temp_step == PRECISION_DOUBLE:
                    self._temp_step = PRECISION_WHOLE
                elif self._data_temp_step == PRECISION_WHOLE:
                    self._temp_step = PRECISION_HALVES
                else:
                    self._temp_step = PRECISION_TENTHS
            else:
                self._temp_step = self._data_temp_step

        # min & max temperatures
        self._min_temperature = convert_temp(
            device_data["minTemperature"],
            self._data_temperature_unit,
            self._ha_temperature_unit,
            self._temp_step,
        )
        self._max_temperature = convert_temp(
            device_data["maxTemperature"],
            self._data_temperature_unit,
            self._ha_temperature_unit,
            self._temp_step,
        )
        self._target_temperature = self._min_temperature

        # hvac_modes
        self._hvac_modes = device_data["operationModes"]
        self._hvac_modes.append(HVACMode.OFF)

        # preset_modes
        self._preset_modes = device_data.get("presetModes")
        if isinstance(self._preset_modes, list) and len(self._preset_modes):
            self._support_flags = self._support_flags | ClimateEntityFeature.PRESET_MODE
            self._preset_mode = self._preset_modes[0]

        # fan_modes
        self._fan_modes = device_data.get("fanModes")
        if isinstance(self._fan_modes, list) and len(self._fan_modes):
            self._support_flags = self._support_flags | ClimateEntityFeature.FAN_MODE
            self._fan_mode = self._fan_modes[0]

        # swing_modes
        self._swing_modes = device_data.get("swingModes")
        if isinstance(self._swing_modes, list) and len(self._swing_modes):
            self._support_flags = self._support_flags | ClimateEntityFeature.SWING_MODE
            self._swing_mode = self._swing_modes[0]

        # Init exclusive lock for sending IR commands
        self._temp_lock = asyncio.Lock()

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
        _LOGGER.debug(
            f"async_added_to_hass {self} {self.name} {self.supported_features}"
        )

        last_state = await self.async_get_last_state()

        if last_state is not None:
            if last_state.state == STATE_OFF:
                self._state = STATE_OFF
            else:
                self._state = STATE_ON

            if last_state.attributes.get("hvac_mode") in self._hvac_modes:
                self._hvac_mode = last_state.attributes.get("hvac_mode")

            if (
                self._support_flags & ClimateEntityFeature.PRESET_MODE
                and last_state.attributes.get("preset_mode") in self._preset_modes
            ):
                self._preset_mode = last_state.attributes.get("preset_mode")

            if (
                self._support_flags & ClimateEntityFeature.FAN_MODE
                and last_state.attributes.get("fan_mode") in self._fan_modes
            ):
                self._fan_mode = last_state.attributes.get("fan_mode")

            if (
                self._support_flags & ClimateEntityFeature.SWING_MODE
                and last_state.attributes.get("swing_mode") in self._swing_modes
            ):
                self._swing_mode = last_state.attributes.get("swing_mode")

            temperature = last_state.attributes.get("temperature")
            if (
                temperature is not None
                and temperature >= self._min_temperature
                and temperature <= self._max_temperature
            ):
                self._target_temperature = temperature

            if self._power_sensor:
                self._on_by_remote = last_state.attributes.get("on_by_remote", False)

        if self._temperature_sensor:
            async_track_state_change_event(
                self.hass, self._temperature_sensor, self._async_temp_sensor_changed
            )
            if last_state is not None:
                self._current_temperature = last_state.attributes.get(
                    "current_temperature"
                )

        if self._humidity_sensor:
            async_track_state_change_event(
                self.hass, self._humidity_sensor, self._async_humidity_sensor_changed
            )
            if last_state is not None:
                self._current_humidity = last_state.attributes.get("current_humidity")

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
        """Return the name of the climate device."""
        return self._name

    @property
    def state(self):
        """Return the current state."""
        if self._on_by_remote and not self._power_sensor_restore_state:
            return self._state
        elif self._state == STATE_OFF:
            return HVACMode.OFF
        else:
            return self._hvac_mode

    @property
    def precision(self) -> float:
        """Return the precision of the system."""
        return self._precision

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._temperature_unit

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
        if self._on_by_remote and not self._power_sensor_restore_state:
            return None
        else:
            return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._temp_step

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._hvac_modes

    @property
    def hvac_mode(self):
        """Return hvac mode ie. heat, cool."""
        if self._on_by_remote and not self._power_sensor_restore_state:
            return None
        else:
            return self._hvac_mode

    @property
    def preset_modes(self):
        """Return the list of available preset modes."""
        return self._preset_modes

    @property
    def preset_mode(self):
        """Return the preset mode."""
        if self._on_by_remote and not self._power_sensor_restore_state:
            return None
        else:
            return self._preset_mode

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return self._fan_modes

    @property
    def fan_mode(self):
        """Return the fan setting."""
        if self._on_by_remote and not self._power_sensor_restore_state:
            return None
        else:
            return self._fan_mode

    @property
    def swing_modes(self):
        """Return the swing modes currently supported for this device."""
        return self._swing_modes

    @property
    def swing_mode(self):
        """Return the current swing mode."""
        if self._on_by_remote and not self._power_sensor_restore_state:
            return None
        else:
            return self._swing_mode

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
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation if supported."""
        if self._on_by_remote and not self._power_sensor_restore_state:
            return None
        else:
            return self._hvac_action

    @property
    def extra_state_attributes(self):
        """Platform specific attributes."""
        return {
            "hvac_mode": self._hvac_mode,
            "on_by_remote": self._on_by_remote,
            "device_code": self._device_code,
            "manufacturer": self._manufacturer,
            "supported_models": self._supported_models,
            "supported_controller": self._supported_controller,
            "commands_encoding": self._commands_encoding,
        }

    async def async_set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        if hvac_mode not in self._hvac_modes:
            _LOGGER.error("The hvac_mode '%s' is not supported.", hvac_mode)
            return

        if hvac_mode == HVACMode.OFF:
            state = STATE_OFF
            hvac_mode = self._hvac_mode
        else:
            state = STATE_ON

        await self._send_command(
            state,
            hvac_mode,
            self._preset_mode,
            self._fan_mode,
            self._swing_mode,
            self._target_temperature,
        )

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        hvac_mode = kwargs.get(ATTR_HVAC_MODE)
        temperature = kwargs.get(ATTR_TEMPERATURE)

        if temperature is None or not isinstance(temperature, Number):
            return

        if temperature < self._min_temperature or temperature > self._max_temperature:
            _LOGGER.error("The temperature value is out of min/max range.")
            return

        if hvac_mode is None:
            hvac_mode = self._hvac_mode
            if self._state == STATE_OFF:
                state = STATE_OFF
            else:
                state = STATE_ON
        elif hvac_mode not in self._hvac_modes:
            _LOGGER.error("The hvac mode '%s' is not supported.", hvac_mode)
            return
        else:
            if hvac_mode == HVACMode.OFF:
                state = STATE_OFF
                hvac_mode = self._hvac_mode
            else:
                state = STATE_ON

        await self._send_command(
            state,
            hvac_mode,
            self._preset_mode,
            self._fan_mode,
            self._swing_mode,
            temperature,
        )

    async def async_set_preset_mode(self, preset_mode):
        """Set preset mode."""
        preset_mode = str(preset_mode)
        if preset_mode not in self._preset_modes:
            _LOGGER.error("The preset mode '%s' is not supported.", preset_mode)
            return

        await self._send_command(
            self._state,
            self._hvac_mode,
            preset_mode,
            self._fan_mode,
            self._swing_mode,
            self._target_temperature,
        )

    async def async_set_fan_mode(self, fan_mode):
        """Set fan mode."""
        fan_mode = str(fan_mode)
        if fan_mode not in self._fan_modes:
            _LOGGER.error("The fan mode '%s' is not supported.", fan_mode)
            return

        await self._send_command(
            self._state,
            self._hvac_mode,
            self._preset_mode,
            fan_mode,
            self._swing_mode,
            self._target_temperature,
        )

    async def async_set_swing_mode(self, swing_mode):
        """Set swing mode."""
        swing_mode = str(swing_mode)
        if swing_mode not in self._swing_modes:
            _LOGGER.error("The swing mode '%s' is not supported.", swing_mode)
            return

        await self._send_command(
            self._state,
            self._hvac_mode,
            self._preset_mode,
            self._fan_mode,
            swing_mode,
            self._target_temperature,
        )

    async def async_turn_off(self):
        """Turn off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self):
        """Turn on."""
        await self.async_set_hvac_mode(self._hvac_mode)

    async def _send_command(
        self, state, hvac_mode, preset_mode, fan_mode, swing_mode, temperature
    ):
        async with self._temp_lock:
            if self._power_sensor and self._state != state:
                self._async_power_sensor_check_schedule(state)

            try:
                if state == STATE_OFF:
                    if (
                        self._hvac_mode == HVACMode.COOL
                        and "off_cool" in self._commands.keys()
                        and isinstance(self._commands["off_cool"], str)
                    ):
                        _LOGGER.debug("Found 'off_cool' operation mode command.")
                        await self._controller.send(self._commands["off_cool"])
                    elif (
                        self._hvac_mode == HVACMode.HEAT
                        and "off_heat" in self._commands.keys()
                        and isinstance(self._commands["off_heat"], str)
                    ):
                        _LOGGER.debug("Found 'off_heat' operation mode command.")
                        await self._controller.send(self._commands["off_heat"])
                    elif (
                        self._hvac_mode == HVACMode.FAN_ONLY
                        and "off_fan_only" in self._commands.keys()
                        and isinstance(self._commands["off_fan_only"], str)
                    ):
                        _LOGGER.debug("Found 'off_fan_only' operation mode command.")
                        await self._controller.send(self._commands["off_fan_only"])
                    elif (
                        self._hvac_mode == HVACMode.DRY
                        and "off_dry" in self._commands.keys()
                        and isinstance(self._commands["off_dry"], str)
                    ):
                        _LOGGER.debug("Found 'off_dry' operation mode command.")
                        await self._controller.send(self._commands["off_dry"])
                    elif "off" in self._commands.keys() and isinstance(
                        self._commands["off"], str
                    ):
                        _LOGGER.debug("Found 'off' operation mode command.")
                        await self._controller.send(self._commands["off"])
                    else:
                        _LOGGER.error(
                            "Missing device IR code for any of off/off_cool/off_heat/off_fan operation mode."
                        )
                        return
                else:
                    commands = self._commands
                    if not isinstance(commands, dict):
                        _LOGGER.error("No device IR codes are defined.")
                        return

                    if "on" in commands.keys() and isinstance(commands["on"], str):
                        """if on code is not present, the on bit can be still set later in the all operation/fan codes"""
                        _LOGGER.debug("Found 'on' operation mode command.")
                        await self._controller.send(commands["on"])
                        await asyncio.sleep(self._delay)

                    if hvac_mode in commands.keys():
                        commands = commands[hvac_mode]
                        _LOGGER.debug(
                            "Found '%s' operation mode command.",
                            hvac_mode,
                        )
                    else:
                        _LOGGER.error(
                            "Missing device IR code for '%s' operation mode.", hvac_mode
                        )
                        return

                    if self._preset_modes:
                        if isinstance(commands, dict):
                            for key in ["-", preset_mode] + self._preset_modes:
                                if key in commands.keys():
                                    preset_mode = key
                                    commands = commands[key]
                                    _LOGGER.debug(
                                        "Found '%s' preset mode command.",
                                        preset_mode,
                                    )
                                    break
                            else:
                                _LOGGER.error(
                                    "Missing device IR codes for selected '%s' preset mode.",
                                    preset_mode,
                                )
                                return
                        else:
                            _LOGGER.error(
                                "No device IR codes for preset modes are defined.",
                            )
                            return

                    if self._fan_modes:
                        if isinstance(commands, dict):
                            for key in ["-", fan_mode] + self._fan_modes:
                                if key in commands.keys():
                                    fan_mode = key
                                    commands = commands[key]
                                    _LOGGER.debug(
                                        "Found '%s' fan mode command.",
                                        fan_mode,
                                    )
                                    break
                            else:
                                _LOGGER.error(
                                    "Missing device IR codes for selected '%s' fan mode.",
                                    fan_mode,
                                )
                                return
                        else:
                            _LOGGER.error(
                                "No device IR codes for fan modes are defined.",
                            )
                            return

                    if self._swing_modes:
                        if isinstance(commands, dict):
                            for key in ["-", swing_mode] + self._swing_modes:
                                if key in commands.keys():
                                    swing_mode = key
                                    commands = commands[key]
                                    _LOGGER.debug(
                                        "Found '%s' swing mode command.",
                                        swing_mode,
                                    )
                                    break
                            else:
                                _LOGGER.error(
                                    "Missing device IR codes for selected '%s' swing mode.",
                                    swing_mode,
                                )
                                return
                        else:
                            _LOGGER.error(
                                "No device IR codes for swing modes are defined.",
                            )
                            return

                    if isinstance(commands, dict):
                        target_temperature = convert_temp(
                            temperature,
                            self._ha_temperature_unit,
                            self._data_temperature_unit,
                            None,
                        )
                        _LOGGER.debug(
                            "Input HA temperature '%s%s' converted into device temperature '%s%s'.",
                            temperature,
                            self._ha_temperature_unit,
                            target_temperature,
                            self._data_temperature_unit,
                        )

                        if "-" in commands.keys():
                            temperature = "-"
                            commands = commands["-"]
                        elif (
                            target_temperature is not None
                            and (
                                temp := sorted(
                                    commands.keys(),
                                    key=lambda value: abs(
                                        float(value) - target_temperature
                                    ),
                                )
                            )
                            and len(temp)
                        ):
                            # convert selected device temperature back to HA units
                            temp_ha = convert_temp(
                                temp[0],
                                self._data_temperature_unit,
                                self._ha_temperature_unit,
                                self._temp_step,
                            )
                            _LOGGER.debug(
                                "Input HA temperature '%s%s' closest found device temperature command '%s%s' converts back into HA '%s%s' temperature.",
                                temperature,
                                self._ha_temperature_unit,
                                temp[0],
                                self._data_temperature_unit,
                                temp_ha,
                                self._ha_temperature_unit,
                            )
                            temperature = temp_ha
                            commands = commands[str(temp[0])]
                        else:
                            _LOGGER.error(
                                "Missing device IR codes for selected '%s' temperature.",
                                target_temperature,
                            )
                            return
                        _LOGGER.debug(
                            "Found '%s', temperature command.",
                            temperature,
                        )
                    else:
                        _LOGGER.error(
                            "No device IR codes for temperatures are defined.",
                        )
                        return

                    if not isinstance(commands, str):
                        _LOGGER.error(
                            "No device IR code found.",
                        )
                        return

                    await self._controller.send(commands)

                self._on_by_remote = False
                self._state = state
                self._hvac_mode = hvac_mode
                if preset_mode != "-":
                    self._preset_mode = preset_mode
                if fan_mode != "-":
                    self._fan_mode = fan_mode
                if swing_mode != "-":
                    self._swing_mode = swing_mode
                if temperature != "-":
                    self._target_temperature = temperature
                await self._async_update_hvac_action()
                self.async_write_ha_state()

            except Exception as e:
                _LOGGER.exception(
                    "Exception raised in the in the _send_command '%s'", e
                )

    async def _async_temp_sensor_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle temperature sensor changes."""
        new_state = event.data["new_state"]
        if new_state is None:
            return

        self._async_update_temp(new_state)
        await self._async_update_hvac_action()
        self.async_write_ha_state()

    async def _async_humidity_sensor_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle humidity sensor changes."""
        new_state = event.data["new_state"]
        if new_state is None:
            return

        self._async_update_humidity(new_state)
        await self._async_update_hvac_action()
        self.async_write_ha_state()

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

        if new_state.state == STATE_ON and self._state == STATE_OFF:
            self._state = STATE_ON
            self._on_by_remote = True
            await self._async_update_hvac_action()
        elif new_state.state == STATE_OFF:
            self._on_by_remote = False
            if self._state == STATE_ON:
                self._state = STATE_OFF
                await self._async_update_hvac_action()
        self.async_write_ha_state()

    async def _async_update_hvac_action(self):
        """Update thermostat current hvac action."""
        if not self._temperature_sensor:
            return

        if self._state == STATE_OFF:
            self._hvac_action = HVACAction.OFF
        elif (
            (
                self._hvac_mode == HVACMode.HEAT
                or self._hvac_mode == HVACMode.HEAT_COOL
                or self._hvac_mode == HVACMode.AUTO
            )
            and self._current_temperature is not None
            and self._current_temperature < self._target_temperature
        ):
            self._hvac_action = HVACAction.HEATING
        elif (
            (
                self._hvac_mode == HVACMode.COOL
                or self._hvac_mode == HVACMode.HEAT_COOL
                or self._hvac_mode == HVACMode.AUTO
            )
            and self._current_temperature is not None
            and self._current_temperature > self._target_temperature
        ):
            self._hvac_action = HVACAction.COOLING
        elif self._hvac_mode == HVACMode.DRY:
            self._hvac_action = HVACAction.DRYING
        elif self._hvac_mode == HVACMode.FAN_ONLY:
            self._hvac_action = HVACAction.FAN
        else:
            self._hvac_action = HVACAction.IDLE

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

    @callback
    def _async_power_sensor_check_schedule(self, state):
        if self._power_sensor_check_cancel:
            self._power_sensor_check_cancel()
            self._power_sensor_check_cancel = None
            self._power_sensor_check_expect = None

        @callback
        def _async_power_sensor_check(*_):
            self._power_sensor_check_cancel = None
            expected_state = self._power_sensor_check_expect
            self._power_sensor_check_expect = None
            current_state = getattr(
                self.hass.states.get(self._power_sensor), "state", None
            )
            _LOGGER.debug(
                "Executing power sensor check for expected state '%s', current state '%s'.",
                expected_state,
                current_state,
            )

            if (
                expected_state in [STATE_ON, STATE_OFF]
                and current_state in [STATE_ON, STATE_OFF]
                and expected_state != current_state
            ):
                self._state = current_state
                _LOGGER.debug(
                    "Power sensor check failed, reverted device state to '%s'.",
                    self._state,
                )
                self.async_write_ha_state()

        self._power_sensor_check_expect = state
        self._power_sensor_check_cancel = async_call_later(
            self.hass, self._power_sensor_delay, _async_power_sensor_check
        )
        _LOGGER.debug("Scheduled power sensor check for '%s' state", state)


def convert_temp(temperature: Number, from_unit: str, to_unit: str, precision: Number):
    _LOGGER.debug(
        "convert temp '%s' from '%s' to '%s' with '%s' precision.",
        temperature,
        from_unit,
        to_unit,
        precision,
    )

    if temperature is None:
        _LOGGER.error("Invalid temperature '%s'.", temperature)
        return None

    try:
        temperature = float(temperature)
    except:
        _LOGGER.error(
            "Input temperature '%s' is not valid number, '%s'.",
            temperature,
            type(temperature),
        )
        return None

    if from_unit != to_unit:
        temperature = TemperatureConverter.converter_factory(from_unit, to_unit)(
            temperature
        )

    # Round in the units appropriate
    if precision is None:
        return temperature
    elif precision == PRECISION_HALVES:
        return round(temperature * 2) / 2.0
    elif precision == PRECISION_TENTHS:
        return round(temperature, 1)
    elif precision == PRECISION_WHOLE:
        return round(temperature)
    elif precision >= PRECISION_DOUBLE:
        return round(temperature / precision) * precision
    else:
        _LOGGER.error("Invalid precision '%s'.", precision)
        return None
