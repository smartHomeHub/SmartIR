import asyncio
import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVAC_MODES,
)

from homeassistant.const import (
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
    ATTR_TEMPERATURE,
    PRECISION_WHOLE,
    UnitOfTemperature,
)

from homeassistant.helpers.restore_state import RestoreEntity

from .controller import get_controller
from .helpers import async_load_device_data

_LOGGER = logging.getLogger(__name__)

CONF_UNIQUE_ID = "unique_id"
CONF_NAME = "name"
CONF_DEVICE_CODE = "device_code"
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"

DEFAULT_DELAY = 0.5

SUPPORT_FLAGS = (
    ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.FAN_MODE
)


async def async_setup_entry(hass, entry, async_add_entities):

    config = entry.data

    device_code = config.get(CONF_DEVICE_CODE)

    device_data = await async_load_device_data(device_code, "climate")

    entity = SmartIRClimate(hass, config, device_data)

    async_add_entities([entity], update_before_add=True)


class SmartIRClimate(ClimateEntity, RestoreEntity):

    def __init__(self, hass, config, device_data):

        self.hass = hass

        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)

        self._controller_data = config.get(CONF_CONTROLLER_DATA)
        self._delay = config.get(CONF_DELAY, DEFAULT_DELAY)

        self._supported_controller = device_data["supportedController"]
        self._commands_encoding = device_data["commandsEncoding"]

        self._min_temperature = device_data["minTemperature"]
        self._max_temperature = device_data["maxTemperature"]
        self._precision = device_data["precision"]

        valid_modes = [x for x in device_data["operationModes"] if x in HVAC_MODES]

        self._operation_modes = [HVACMode.OFF] + valid_modes

        self._fan_modes = device_data["fanModes"]

        self._commands = device_data["commands"]

        self._target_temperature = self._min_temperature
        self._hvac_mode = HVACMode.OFF

        self._current_fan_mode = self._fan_modes[0]

        self._current_temperature = None
        self._current_humidity = None

        self._support_flags = SUPPORT_FLAGS

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

        if last_state:
            self._hvac_mode = last_state.state
            self._target_temperature = last_state.attributes.get("temperature")

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def should_poll(self):
        return False

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return self._operation_modes

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def current_humidity(self):
        return self._current_humidity

    @property
    def min_temp(self):
        return self._min_temperature

    @property
    def max_temp(self):
        return self._max_temperature

    @property
    def fan_modes(self):
        return self._fan_modes

    @property
    def fan_mode(self):
        return self._current_fan_mode

    @property
    def supported_features(self):
        return self._support_flags

    async def async_set_temperature(self, **kwargs):

        temperature = kwargs.get(ATTR_TEMPERATURE)

        if temperature is None:
            return

        if self._precision == PRECISION_WHOLE:
            self._target_temperature = round(temperature)
        else:
            self._target_temperature = round(temperature, 1)

        await self.send_command()

        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):

        self._hvac_mode = hvac_mode

        await self.send_command()

        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):

        self._current_fan_mode = fan_mode

        await self.send_command()

        self.async_write_ha_state()

    async def async_turn_on(self):

        await self.async_set_hvac_mode(HVACMode.COOL)

    async def async_turn_off(self):

        await self.async_set_hvac_mode(HVACMode.OFF)

    async def send_command(self):

        async with self._temp_lock:

            try:

                operation_mode = self._hvac_mode
                fan_mode = self._current_fan_mode
                temp = f"{self._target_temperature:g}"

                if operation_mode == HVACMode.OFF:

                    await self._controller.send(self._commands["off"])
                    return

                await self._controller.send(
                    self._commands[operation_mode][fan_mode][temp]
                )

            except Exception as err:

                _LOGGER.exception("SmartIR send command failed: %s", err)