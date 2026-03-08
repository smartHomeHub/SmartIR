import asyncio
import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)

from homeassistant.const import STATE_OFF, STATE_ON
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


async def async_setup_entry(hass, entry, async_add_entities):

    config = entry.data

    device_code = config.get(CONF_DEVICE_CODE)

    device_data = await async_load_device_data(device_code, "light")

    async_add_entities(
        [
            SmartIRLight(
                hass,
                config,
                device_data,
            )
        ],
        True,
    )


class SmartIRLight(LightEntity, RestoreEntity):

    def __init__(self, hass, config, device_data):

        self.hass = hass

        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)

        self._controller_data = config.get(CONF_CONTROLLER_DATA)
        self._delay = config.get(CONF_DELAY, DEFAULT_DELAY)

        self._supported_controller = device_data["supportedController"]
        self._commands_encoding = device_data["commandsEncoding"]

        self._brightnesses = device_data.get("brightness")
        self._colortemps = device_data.get("colorTemperature")
        self._commands = device_data["commands"]

        self._power = STATE_OFF
        self._brightness = None
        self._colortemp = None

        self._color_mode = ColorMode.ONOFF

        if self._brightnesses:
            self._color_mode = ColorMode.BRIGHTNESS

        if self._colortemps:
            self._color_mode = ColorMode.COLOR_TEMP

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
            self._power = last_state.state

            if ATTR_BRIGHTNESS in last_state.attributes:
                self._brightness = last_state.attributes[ATTR_BRIGHTNESS]

            if ATTR_COLOR_TEMP_KELVIN in last_state.attributes:
                self._colortemp = last_state.attributes[ATTR_COLOR_TEMP_KELVIN]

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def supported_color_modes(self):
        return [self._color_mode]

    @property
    def color_mode(self):
        return self._color_mode

    @property
    def is_on(self):
        return self._power == STATE_ON

    @property
    def brightness(self):
        return self._brightness

    @property
    def color_temp_kelvin(self):
        return self._colortemp

    async def async_turn_on(self, **kwargs):

        if self._power == STATE_OFF:
            await self._controller.send(self._commands["on"])
            self._power = STATE_ON

        if ATTR_BRIGHTNESS in kwargs and self._brightnesses:
            self._brightness = kwargs[ATTR_BRIGHTNESS]

        if ATTR_COLOR_TEMP_KELVIN in kwargs and self._colortemps:
            self._colortemp = kwargs[ATTR_COLOR_TEMP_KELVIN]

        self.async_write_ha_state()

    async def async_turn_off(self):

        await self._controller.send(self._commands["off"])

        self._power = STATE_OFF

        self.async_write_ha_state()