import asyncio
import aiofiles
import json
import logging
import os.path

import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
    PLATFORM_SCHEMA,
)
from homeassistant.const import (
    CONF_NAME,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from . import COMPONENT_ABS_DIR, Helper
from .controller import get_controller

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "SmartIR Light"
DEFAULT_DELAY = 0.5

CONF_UNIQUE_ID = "unique_id"
CONF_DEVICE_CODE = "device_code"
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"
CONF_POWER_SENSOR = "power_sensor"

CMD_BRIGHTNESS_INCREASE = "brighten"
CMD_BRIGHTNESS_DECREASE = "dim"
CMD_COLORMODE_COLDER = "colder"
CMD_COLORMODE_WARMER = "warmer"
CMD_POWER_ON = "on"
CMD_POWER_OFF = "off"
CMD_NIGHTLIGHT = "night"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_DEVICE_CODE): cv.positive_int,
        vol.Required(CONF_CONTROLLER_DATA): cv.string,
        vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): cv.string,
        vol.Optional(CONF_POWER_SENSOR): cv.entity_id,
    }
)


async def async_setup_platform(
    hass,
    config,
    async_add_entities,
    discovery_info=None,
):
    """Set up the IR Light platform."""
    device_code = config.get(CONF_DEVICE_CODE)
    device_files_subdir = os.path.join("codes", "light")
    device_files_absdir = os.path.join(COMPONENT_ABS_DIR, device_files_subdir)

    if not os.path.isdir(device_files_absdir):
        os.makedirs(device_files_absdir)

    device_json_filename = str(device_code) + ".json"
    device_json_path = os.path.join(device_files_absdir, device_json_filename)

    if not os.path.exists(device_json_path):
        _LOGGER.warning(
            "Couldn't find the device Json file. The component "
            "will try to download it from the Github repo."
        )

        try:
            codes_source = (
                "https://raw.githubusercontent.com/"
                "smartHomeHub/SmartIR/master/"
                "codes/light/{}.json"
            )

            await Helper.downloader(
                codes_source.format(device_code),
                device_json_path,
            )
        except Exception:
            _LOGGER.error(
                "There was an error while downloading the device Json file. "
                "Please check your internet connection or if the device code "
                "exists on GitHub. If the problem still exists please "
                "place the file manually in the proper directory."
            )
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

    async_add_entities([SmartIRLight(hass, config, device_data)])


# find the closest match in a sorted list
def closest_match(value, list):
    prev_val = None
    for index, entry in enumerate(list):
        if entry > (value or 0):
            if prev_val is None:
                return index
            diff_lo = value - prev_val
            diff_hi = entry - value
            if diff_lo < diff_hi:
                return index - 1
            return index
        prev_val = entry

    return len(list) - 1


class SmartIRLight(LightEntity, RestoreEntity):
    def __init__(self, hass, config, device_data):
        self.hass = hass
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)
        self._device_code = config.get(CONF_DEVICE_CODE)
        self._controller_data = config.get(CONF_CONTROLLER_DATA)
        self._delay = config.get(CONF_DELAY)
        self._power_sensor = config.get(CONF_POWER_SENSOR)

        self._manufacturer = device_data["manufacturer"]
        self._supported_models = device_data["supportedModels"]
        self._supported_controller = device_data["supportedController"]
        self._commands_encoding = device_data["commandsEncoding"]
        self._brightnesses = device_data["brightness"]
        self._colortemps = device_data["colorTemperature"]
        self._commands = device_data["commands"]

        self._power = STATE_ON
        self._brightness = None
        self._colortemp = None

        self._temp_lock = asyncio.Lock()
        self._on_by_remote = False
        self._support_color_mode = ColorMode.UNKNOWN

        if (
            CMD_COLORMODE_COLDER in self._commands
            and CMD_COLORMODE_WARMER in self._commands
        ):
            self._colortemp = self.max_color_temp_kelvin
            self._support_color_mode = ColorMode.COLOR_TEMP

        if CMD_NIGHTLIGHT in self._commands or (
            CMD_BRIGHTNESS_INCREASE in self._commands
            and CMD_BRIGHTNESS_DECREASE in self._commands
        ):
            self._brightness = 100
            self._support_brightness = True
            if self._support_color_mode == ColorMode.UNKNOWN:
                self._support_color_mode = ColorMode.BRIGHTNESS
        else:
            self._support_brightness = False

        if (
            CMD_POWER_OFF in self._commands
            and CMD_POWER_ON in self._commands
            and self._support_color_mode == ColorMode.UNKNOWN
        ):
            self._support_color_mode = ColorMode.ONOFF

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
            self._power = last_state.state
            if ATTR_BRIGHTNESS in last_state.attributes:
                self._brightness = last_state.attributes[ATTR_BRIGHTNESS]
            if ATTR_COLOR_TEMP_KELVIN in last_state.attributes:
                self._colortemp = last_state.attributes[ATTR_COLOR_TEMP_KELVIN]

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
        """Return the display name of the light."""
        return self._name

    @property
    def supported_color_modes(self):
        """Return the list of supported color modes."""
        return [self._support_color_mode]

    @property
    def color_mode(self):
        return self._support_color_mode

    @property
    def color_temp_kelvin(self):
        return self._colortemp

    @property
    def min_color_temp_kelvin(self):
        if self._colortemps:
            return self._colortemps[0]

    @property
    def max_color_temp_kelvin(self):
        if self._colortemps:
            return self._colortemps[-1]

    @property
    def is_on(self):
        return self._power == STATE_ON or self._on_by_remote

    @property
    def brightness(self):
        return self._brightness

    @property
    def extra_state_attributes(self):
        """Platform specific attributes."""
        return {
            "device_code": self._device_code,
            "manufacturer": self._manufacturer,
            "supported_models": self._supported_models,
            "supported_controller": self._supported_controller,
            "commands_encoding": self._commands_encoding,
            "on_by_remote": self._on_by_remote,
        }

    async def async_turn_on(self, **params):
        did_something = False
        # Turn the light on if off
        if self._power != STATE_ON and not self._on_by_remote:
            self._power = STATE_ON
            did_something = True
            await self.send_command(CMD_POWER_ON)

        if (
            ATTR_COLOR_TEMP_KELVIN in params
            and ColorMode.COLOR_TEMP == self._support_color_mode
        ):
            target = params.get(ATTR_COLOR_TEMP_KELVIN)
            old_color_temp = closest_match(self._colortemp, self._colortemps)
            new_color_temp = closest_match(target, self._colortemps)
            _LOGGER.debug(
                f"Changing color temp from {self._colortemp}K step {old_color_temp} to {target}K step {new_color_temp}"
            )

            steps = new_color_temp - old_color_temp
            did_something = True
            if steps < 0:
                cmd = CMD_COLORMODE_WARMER
                steps = abs(steps)
            else:
                cmd = CMD_COLORMODE_COLDER

            if steps > 0 and cmd:
                # If we are heading for the highest or lowest value,
                # take the opportunity to resync by issuing enough
                # commands to go the full range.
                if new_color_temp == len(self._colortemps) - 1 or new_color_temp == 0:
                    steps = len(self._colortemps)
                self._colortemp = self._colortemps[new_color_temp]
                await self.send_command(cmd, steps)

        if ATTR_BRIGHTNESS in params and self._support_brightness:
            # before checking the supported brightnesses, make a special case
            # when a nightlight is fitted for brightness of 1
            if params.get(ATTR_BRIGHTNESS) == 1 and CMD_NIGHTLIGHT in self._commands:
                self._brightness = 1
                self._power = STATE_ON
                did_something = True
                await self.send_command(CMD_NIGHTLIGHT)

            elif self._brightnesses:
                target = params.get(ATTR_BRIGHTNESS)
                old_brightness = closest_match(self._brightness, self._brightnesses)
                new_brightness = closest_match(target, self._brightnesses)
                did_something = True
                _LOGGER.debug(
                    f"Changing brightness from {self._brightness} step {old_brightness} to {target} step {new_brightness}"
                )
                steps = new_brightness - old_brightness
                if steps < 0:
                    cmd = CMD_BRIGHTNESS_DECREASE
                    steps = abs(steps)
                else:
                    cmd = CMD_BRIGHTNESS_INCREASE

                if steps > 0 and cmd:
                    # If we are heading for the highest or lowest value,
                    # take the opportunity to resync by issuing enough
                    # commands to go the full range.
                    if (
                        new_brightness == len(self._brightnesses) - 1
                        or new_brightness == 0
                    ):
                        steps = len(self._colortemps)
                    did_something = True
                    self._brightness = self._brightnesses[new_brightness]
                    await self.send_command(cmd, steps)

        # If we did nothing above, and the light is not detected as on
        # already issue the on command, even though we think the light
        # is on.  This is because we may be out of sync due to use of the
        # remote when we don't have anything to detect it.
        # If we do have such monitoring, avoid issuing the command in case
        # on and off are the same remote code.
        if not did_something and not self._on_by_remote:
            self._power = STATE_ON
            await self.send_command(CMD_POWER_ON)

        self.async_write_ha_state()

    async def async_turn_off(self):
        self._power = STATE_OFF
        await self.send_command(CMD_POWER_OFF)
        self.async_write_ha_state()

    async def async_toggle(self):
        await (self.async_turn_on() if not self.is_on else self.async_turn_off())

    async def send_command(self, cmd, count=1):
        if cmd not in self._commands:
            _LOGGER.error(f"Unknown command '{cmd}'")
            return
        _LOGGER.debug(f"Sending {cmd} remote command {count} times.")
        remote_cmd = self._commands.get(cmd)
        async with self._temp_lock:
            self._on_by_remote = False
            try:
                for _ in range(count):
                    await self._controller.send(remote_cmd)
            except Exception as e:
                _LOGGER.exception(e)

    @callback
    async def _async_power_sensor_changed(self, event):
        """Handle power sensor changes."""
        new_state = event.data["new_state"]
        if new_state is None:
            return
        old_state = event.data["old_state"]
        if new_state.state == old_state.state:
            return

        if new_state.state == STATE_ON:
            self._on_by_remote = True
            self.async_write_ha_state()

        if new_state.state == STATE_OFF:
            self._on_by_remote = False
            self._power = STATE_OFF
            self.async_write_ha_state()
