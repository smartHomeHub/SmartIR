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
    CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN)
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change, async_track_state_change_event
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item
)
from . import COMPONENT_ABS_DIR, Helper
from .controller import get_controller
from .power_feedback import consumption_state_is_on, retry_with_feedback_backoff

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "SmartIR Fan"
DEFAULT_DELAY = 0.5

CONF_UNIQUE_ID = 'unique_id'
CONF_DEVICE_CODE = 'device_code'
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"
CONF_POWER_SENSOR = 'power_sensor'
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

SPEED_OFF = "off"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_UNIQUE_ID): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_DEVICE_CODE): cv.positive_int,
    vol.Required(CONF_CONTROLLER_DATA): cv.string,
    vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): cv.string,
    vol.Optional(CONF_POWER_SENSOR): cv.entity_id,
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
    """Set up the IR Fan platform."""
    device_code = config.get(CONF_DEVICE_CODE)
    device_files_subdir = os.path.join('codes', 'fan')
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
                            "codes/fan/{}.json")

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

    async_add_entities([SmartIRFan(
        hass, config, device_data
    )])

class SmartIRFan(FanEntity, RestoreEntity):
    def __init__(self, hass, config, device_data):
        self.hass = hass
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)
        self._device_code = config.get(CONF_DEVICE_CODE)
        self._controller_data = config.get(CONF_CONTROLLER_DATA)
        self._delay = config.get(CONF_DELAY)
        self._power_sensor = config.get(CONF_POWER_SENSOR)
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

        if (DIRECTION_REVERSE in self._commands and \
            DIRECTION_FORWARD in self._commands):
            self._direction = DIRECTION_REVERSE
            self._support_flags = (
                self._support_flags | FanEntityFeature.DIRECTION)
        if ('oscillate' in self._commands):
            self._oscillating = False
            self._support_flags = (
                self._support_flags | FanEntityFeature.OSCILLATE)


        self._temp_lock = asyncio.Lock()
        self._on_by_remote = False
        self._last_consumption_effective_on = None
        self._command_generation = 0

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
    
        last_state = await self.async_get_last_state()

        if last_state is not None:
            if 'speed' in last_state.attributes:
                self._speed = last_state.attributes['speed']

            #If _direction has a value the direction controls appears 
            #in UI even if SUPPORT_DIRECTION is not provided in the flags
            if ('direction' in last_state.attributes and \
                self._support_flags & FanEntityFeature.DIRECTION):
                self._direction = last_state.attributes['direction']

            if 'last_on_speed' in last_state.attributes:
                self._last_on_speed = last_state.attributes['last_on_speed']

        if self._power_sensor and self._power_consumption_sensor:
            _LOGGER.warning(
                "%s: both %s and %s are set; using %s only",
                self.name,
                CONF_POWER_SENSOR,
                CONF_POWER_CONSUMPTION_SENSOR,
                CONF_POWER_SENSOR,
            )

        if self._power_sensor:
            async_track_state_change_event(
                self.hass, self._power_sensor, self._async_power_sensor_changed
            )
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
        """Return the display name of the fan."""
        return self._name

    @property
    def state(self):
        """Return the current state."""
        if (self._on_by_remote or \
            self._speed != SPEED_OFF):
            return STATE_ON
        return SPEED_OFF

    @property
    def percentage(self):
        """Return speed percentage of the fan."""
        if (self._speed == SPEED_OFF):
            return 0

        return ordered_list_item_to_percentage(self._speed_list, self._speed)

    @property
    def speed_count(self):
        """Return the number of speeds the fan supports."""
        return len(self._speed_list)

    @property
    def oscillating(self):
        """Return the oscillation state."""
        return self._oscillating

    @property
    def current_direction(self):
        """Return the direction state."""
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
    def extra_state_attributes(self):
        """Platform specific attributes."""
        return {
            'last_on_speed': self._last_on_speed,
            'device_code': self._device_code,
            'manufacturer': self._manufacturer,
            'supported_models': self._supported_models,
            'supported_controller': self._supported_controller,
            'commands_encoding': self._commands_encoding,
        }

    async def async_set_percentage(self, percentage: int):
        """Set the desired speed for the fan."""
        if (percentage == 0):
             self._speed = SPEED_OFF
        else:
            self._speed = percentage_to_ordered_list_item(
                self._speed_list, percentage)

        if not self._speed == SPEED_OFF:
            self._last_on_speed = self._speed

        await self.send_command()
        self.async_write_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation of the fan."""
        self._oscillating = oscillating

        await self.send_command()
        self.async_write_ha_state()

    async def async_set_direction(self, direction: str):
        """Set the direction of the fan"""
        self._direction = direction

        if self._speed and self._speed.lower() != SPEED_OFF:
            await self.send_command()

        self.async_write_ha_state()

    async def async_turn_on(self, percentage: int = None, preset_mode: str = None, **kwargs):
        """Turn on the fan."""
        if percentage is None:
            percentage = ordered_list_item_to_percentage(
                self._speed_list, self._last_on_speed or self._speed_list[0])

        await self.async_set_percentage(percentage)

    async def async_turn_off(self):
        """Turn off the fan."""
        await self.async_set_percentage(0)

    def _consumption_feedback_enabled(self) -> bool:
        return self._power_sensor is None and self._power_consumption_sensor is not None

    def _read_consumption_effective_power(self):
        if not self._consumption_feedback_enabled():
            return None
        power_state = self.hass.states.get(self._power_consumption_sensor)
        if power_state is None:
            return None
        return consumption_state_is_on(
            power_state, self._power_consumption_on_threshold_watts
        )

    def _apply_effective_power(self, is_on: bool) -> None:
        if is_on and self._speed == SPEED_OFF:
            self._on_by_remote = True
            self._speed = None
            self.async_write_ha_state()
        elif not is_on:
            self._on_by_remote = False
            if self._speed != SPEED_OFF:
                self._speed = SPEED_OFF
            self.async_write_ha_state()

    @callback
    def _update_from_power_consumption(self, state) -> None:
        is_on = consumption_state_is_on(
            state, self._power_consumption_on_threshold_watts
        )
        if self._last_consumption_effective_on is not None and is_on == self._last_consumption_effective_on:
            return
        self._last_consumption_effective_on = is_on
        self._apply_effective_power(is_on)

    async def _retry_consumption_feedback_if_needed(
        self, desired_is_on: bool, command_generation: int, resend_command
    ):
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
        speed = self._speed or SPEED_OFF
        direction = self._direction or 'default'
        oscillating = self._oscillating
        desired_is_on = speed.lower() != SPEED_OFF

        if speed.lower() == SPEED_OFF:
            command = self._commands['off']
        elif oscillating:
            command = self._commands['oscillate']
        else:
            command = self._commands[direction][speed]

        async def resend_command():
            async with self._temp_lock:
                self._on_by_remote = False
                try:
                    await self._controller.send(command)
                except Exception as e:
                    _LOGGER.exception(e)

        await resend_command()
        await self._retry_consumption_feedback_if_needed(
            desired_is_on, command_generation, resend_command
        )

    @callback
    async def _async_power_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        """Handle power sensor changes."""
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        if new_state is None:
            return

        if old_state is not None and new_state.state == old_state.state:
            return

        self._apply_effective_power(new_state.state == STATE_ON)

    @callback
    async def _async_power_consumption_sensor_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        new_state = event.data["new_state"]
        if new_state is None:
            return
        self._update_from_power_consumption(new_state)