import asyncio
import aiofiles
import json
import logging
import os.path

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerEntity, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature, MediaType)
from homeassistant.const import (
    CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN)
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change_event
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from . import COMPONENT_ABS_DIR, Helper
from .controller import get_controller
from .power_feedback import consumption_state_is_on, retry_with_feedback_backoff

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "SmartIR Media Player"
DEFAULT_DEVICE_CLASS = "tv"
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
CONF_SOURCE_NAMES = 'source_names'
CONF_DEVICE_CLASS = 'device_class'

DEFAULT_POWER_CONSUMPTION_ON_THRESHOLD_WATTS = 10.0
DEFAULT_POWER_CONSUMPTION_RETRY_COUNT = 3
DEFAULT_POWER_CONSUMPTION_RETRY_INITIAL_DELAY_SECONDS = 2.0
DEFAULT_POWER_CONSUMPTION_RETRY_BACKOFF_MULTIPLIER = 1.5
DEFAULT_POWER_CONSUMPTION_RETRY_MAX_DELAY_SECONDS = 10.0

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
    vol.Optional(CONF_SOURCE_NAMES): dict,
    vol.Optional(CONF_DEVICE_CLASS, default=DEFAULT_DEVICE_CLASS): cv.string
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the IR Media Player platform."""
    device_code = config.get(CONF_DEVICE_CODE)
    device_files_subdir = os.path.join('codes', 'media_player')
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
                            "codes/media_player/{}.json")

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

    async_add_entities([SmartIRMediaPlayer(
        hass, config, device_data
    )])

class SmartIRMediaPlayer(MediaPlayerEntity, RestoreEntity):
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
        self._commands = device_data['commands']

        self._state = STATE_OFF
        self._sources_list = []
        self._source = None
        self._support_flags = 0

        self._device_class = config.get(CONF_DEVICE_CLASS)

        #Supported features
        if 'off' in self._commands and self._commands['off'] is not None:
            self._support_flags = self._support_flags | MediaPlayerEntityFeature.TURN_OFF

        if 'on' in self._commands and self._commands['on'] is not None:
            self._support_flags = self._support_flags | MediaPlayerEntityFeature.TURN_ON

        if 'previousChannel' in self._commands and self._commands['previousChannel'] is not None:
            self._support_flags = self._support_flags | MediaPlayerEntityFeature.PREVIOUS_TRACK

        if 'nextChannel' in self._commands and self._commands['nextChannel'] is not None:
            self._support_flags = self._support_flags | MediaPlayerEntityFeature.NEXT_TRACK

        if ('volumeDown' in self._commands and self._commands['volumeDown'] is not None) \
        or ('volumeUp' in self._commands and self._commands['volumeUp'] is not None):
            self._support_flags = self._support_flags | MediaPlayerEntityFeature.VOLUME_STEP

        if 'mute' in self._commands and self._commands['mute'] is not None:
            self._support_flags = self._support_flags | MediaPlayerEntityFeature.VOLUME_MUTE

        if 'sources' in self._commands and self._commands['sources'] is not None:
            self._support_flags = self._support_flags | MediaPlayerEntityFeature.SELECT_SOURCE | MediaPlayerEntityFeature.PLAY_MEDIA

            for source, new_name in config.get(CONF_SOURCE_NAMES, {}).items():
                if source in self._commands['sources']:
                    if new_name is not None:
                        self._commands['sources'][new_name] = self._commands['sources'][source]

                    del self._commands['sources'][source]

            #Sources list
            for key in self._commands['sources']:
                self._sources_list.append(key)

        self._temp_lock = asyncio.Lock()
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
            self._state = last_state.state

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
            self._sync_from_power_sensor()
        elif self._power_consumption_sensor:
            async_track_state_change_event(
                self.hass,
                self._power_consumption_sensor,
                self._async_power_consumption_sensor_changed,
            )
            self._sync_from_power_consumption()

    @property
    def should_poll(self):
        """Push an update after each command."""
        return True

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the media player."""
        return self._name

    @property
    def device_class(self):
        """Return the device_class of the media player."""
        return self._device_class

    @property
    def state(self):
        """Return the state of the player."""
        return self._state

    @property
    def media_title(self):
        """Return the title of current playing media."""
        return None

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MediaType.CHANNEL

    @property
    def source_list(self):
        return self._sources_list
        
    @property
    def source(self):
        return self._source

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return self._support_flags

    @property
    def extra_state_attributes(self):
        """Platform specific attributes."""
        return {
            'device_code': self._device_code,
            'manufacturer': self._manufacturer,
            'supported_models': self._supported_models,
            'supported_controller': self._supported_controller,
            'commands_encoding': self._commands_encoding,
        }

    async def async_turn_off(self):
        """Turn the media player off."""
        await self.send_command(self._commands['off'], desired_is_on=False)
        
        if self._power_sensor is None and self._power_consumption_sensor is None:
            self._state = STATE_OFF
            self._source = None
            self.async_write_ha_state()

    async def async_turn_on(self):
        """Turn the media player off."""
        await self.send_command(self._commands['on'], desired_is_on=True)

        if self._power_sensor is None and self._power_consumption_sensor is None:
            self._state = STATE_ON
            self.async_write_ha_state()

    async def async_media_previous_track(self):
        """Send previous track command."""
        await self.send_command(self._commands['previousChannel'])
        self.async_write_ha_state()

    async def async_media_next_track(self):
        """Send next track command."""
        await self.send_command(self._commands['nextChannel'])
        self.async_write_ha_state()

    async def async_volume_down(self):
        """Turn volume down for media player."""
        await self.send_command(self._commands['volumeDown'])
        self.async_write_ha_state()

    async def async_volume_up(self):
        """Turn volume up for media player."""
        await self.send_command(self._commands['volumeUp'])
        self.async_write_ha_state()
    
    async def async_mute_volume(self, mute):
        """Mute the volume."""
        await self.send_command(self._commands['mute'])
        self.async_write_ha_state()

    async def async_select_source(self, source):
        """Select channel from source."""
        self._source = source
        await self.send_command(self._commands['sources'][source])
        self.async_write_ha_state()

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Support channel change through play_media service."""
        if self._state == STATE_OFF:
            await self.async_turn_on()

        if media_type != MediaType.CHANNEL:
            _LOGGER.error("invalid media type")
            return
        if not media_id.isdigit():
            _LOGGER.error("media_id must be a channel number")
            return

        self._source = "Channel {}".format(media_id)
        for digit in media_id:
            await self.send_command(self._commands['sources']["Channel {}".format(digit)])
        self.async_write_ha_state()

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
        self._state = STATE_ON if is_on else STATE_OFF
        if not is_on:
            self._source = None
        self.async_write_ha_state()

    def _sync_from_power_sensor(self):
        if self._power_sensor is None:
            return
        power_state = self.hass.states.get(self._power_sensor)
        if power_state is None:
            return
        if power_state.state == STATE_ON:
            self._apply_effective_power(True)
        elif power_state.state == STATE_OFF:
            self._apply_effective_power(False)

    def _sync_from_power_consumption(self):
        if self._power_consumption_sensor is None:
            return
        power_state = self.hass.states.get(self._power_consumption_sensor)
        if power_state is None:
            return
        is_on = consumption_state_is_on(
            power_state, self._power_consumption_on_threshold_watts
        )
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

    async def send_command(self, command, desired_is_on=None):
        self._command_generation += 1
        command_generation = self._command_generation
        if desired_is_on is None:
            desired_is_on = self._state == STATE_ON

        async def resend_command():
            async with self._temp_lock:
                try:
                    await self._controller.send(command)
                except Exception as e:
                    _LOGGER.exception(e)

        await resend_command()
        await self._retry_consumption_feedback_if_needed(
            desired_is_on, command_generation, resend_command
        )
            
    async def async_update(self):
        if self._power_sensor is not None:
            self._sync_from_power_sensor()
        elif self._power_consumption_sensor is not None:
            self._sync_from_power_consumption()

    @callback
    async def _async_power_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
        if new_state is None:
            return
        old_state = event.data["old_state"]
        if old_state is not None and new_state.state == old_state.state:
            return
        if new_state.state == STATE_ON:
            self._apply_effective_power(True)
        elif new_state.state == STATE_OFF:
            self._apply_effective_power(False)

    @callback
    async def _async_power_consumption_sensor_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        new_state = event.data["new_state"]
        if new_state is None:
            return
        is_on = consumption_state_is_on(
            new_state, self._power_consumption_on_threshold_watts
        )
        if self._last_consumption_effective_on is not None and is_on == self._last_consumption_effective_on:
            return
        self._last_consumption_effective_on = is_on
        self._apply_effective_power(is_on)
