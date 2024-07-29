import asyncio
import logging

import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntity, PLATFORM_SCHEMA
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MEDIA_TYPE_CHANNEL,
)
from homeassistant.const import CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change_event, async_call_later
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType
from . import DeviceData
from .controller import get_controller, get_controller_schema

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "SmartIR Media Player"
DEFAULT_DEVICE_CLASS = "tv"
DEFAULT_DELAY = 0.5
DEFAULT_POWER_SENSOR_DELAY = 10

CONF_UNIQUE_ID = "unique_id"
CONF_DEVICE_CODE = "device_code"
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"
CONF_POWER_SENSOR = "power_sensor"
CONF_POWER_SENSOR_DELAY = "power_sensor_delay"
CONF_POWER_SENSOR_RESTORE_STATE = "power_sensor_restore_state"
CONF_SOURCE_NAMES = "source_names"
CONF_DEVICE_CLASS = "device_class"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_DEVICE_CODE): cv.positive_int,
        vol.Required(CONF_CONTROLLER_DATA): get_controller_schema(vol, cv),
        vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): cv.positive_float,
        vol.Optional(CONF_POWER_SENSOR): cv.entity_id,
        vol.Optional(
            CONF_POWER_SENSOR_DELAY, default=DEFAULT_POWER_SENSOR_DELAY
        ): cv.positive_int,
        vol.Optional(CONF_POWER_SENSOR_RESTORE_STATE, default=True): cv.boolean,
        vol.Optional(CONF_SOURCE_NAMES): dict,
        vol.Optional(CONF_DEVICE_CLASS, default=DEFAULT_DEVICE_CLASS): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None
):
    """Set up the IR Media Player platform."""
    _LOGGER.debug("Setting up the SmartIR media player platform")
    if not (
        device_data := await DeviceData.load_file(
            config.get(CONF_DEVICE_CODE),
            "media_player",
            {},
            hass,
        )
    ):
        _LOGGER.error("SmartIR media player device data init failed!")
        return

    async_add_entities([SmartIRMediaPlayer(hass, config, device_data)])


class SmartIRMediaPlayer(MediaPlayerEntity, RestoreEntity):
    _attr_should_poll = False

    def __init__(self, hass, config, device_data):
        self.hass = hass
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)
        self._device_code = config.get(CONF_DEVICE_CODE)
        self._controller_data = config.get(CONF_CONTROLLER_DATA)
        self._delay = config.get(CONF_DELAY)
        self._power_sensor = config.get(CONF_POWER_SENSOR)
        self._power_sensor_delay = config.get(CONF_POWER_SENSOR_DELAY)
        self._power_sensor_restore_state = config.get(CONF_POWER_SENSOR_RESTORE_STATE)
        self._device_class = config.get(CONF_DEVICE_CLASS)

        self._state = STATE_UNKNOWN
        self._sources_list = []
        self._source = None
        self._on_by_remote = False
        self._support_flags = 0
        self._power_sensor_check_expect = None
        self._power_sensor_check_cancel = None

        self._manufacturer = device_data["manufacturer"]
        self._supported_models = device_data["supportedModels"]
        self._supported_controller = device_data["supportedController"]
        self._commands_encoding = device_data["commandsEncoding"]
        self._commands = device_data["commands"]

        # Supported features
        if "off" in self._commands and self._commands["off"] is not None:
            self._support_flags = (
                self._support_flags | MediaPlayerEntityFeature.TURN_OFF
            )

        if "on" in self._commands and self._commands["on"] is not None:
            self._support_flags = self._support_flags | MediaPlayerEntityFeature.TURN_ON

        if (
            "previousChannel" in self._commands
            and self._commands["previousChannel"] is not None
        ):
            self._support_flags = (
                self._support_flags | MediaPlayerEntityFeature.PREVIOUS_TRACK
            )

        if (
            "nextChannel" in self._commands
            and self._commands["nextChannel"] is not None
        ):
            self._support_flags = (
                self._support_flags | MediaPlayerEntityFeature.NEXT_TRACK
            )

        if (
            "volumeDown" in self._commands and self._commands["volumeDown"] is not None
        ) or ("volumeUp" in self._commands and self._commands["volumeUp"] is not None):
            self._support_flags = (
                self._support_flags | MediaPlayerEntityFeature.VOLUME_STEP
            )

        if "mute" in self._commands and self._commands["mute"] is not None:
            self._support_flags = (
                self._support_flags | MediaPlayerEntityFeature.VOLUME_MUTE
            )

        if "sources" in self._commands and self._commands["sources"] is not None:
            self._support_flags = (
                self._support_flags
                | MediaPlayerEntityFeature.SELECT_SOURCE
                | MediaPlayerEntityFeature.PLAY_MEDIA
            )

            for source, new_name in config.get(CONF_SOURCE_NAMES, {}).items():
                if source in self._commands["sources"]:
                    if new_name is not None:
                        self._commands["sources"][new_name] = self._commands["sources"][
                            source
                        ]

                    del self._commands["sources"][source]

            # Sources list
            for key in self._commands["sources"]:
                self._sources_list.append(key)

        # Init exclusive lock for sending IR commands
        self._temp_lock = asyncio.Lock()

        # Init the IR/RF controller
        self._controller = get_controller(
            self.hass,
            self._supported_controller,
            self._commands_encoding,
            self._controller_data,
        )

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()

        if last_state is not None:
            self._state = last_state.state

            if self._power_sensor:
                self._on_by_remote = last_state.attributes.get("on_by_remote", False)

        if self._power_sensor:
            async_track_state_change_event(
                self.hass, self._power_sensor, self._async_power_sensor_changed
            )

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
        return MEDIA_TYPE_CHANNEL

    @property
    def source_list(self):
        return self._sources_list

    @property
    def source(self):
        if self._on_by_remote and not self._power_sensor_restore_state:
            return None
        else:
            return self._source

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return self._support_flags

    @property
    def extra_state_attributes(self):
        """Platform specific attributes."""
        return {
            "on_by_remote": self._on_by_remote,
            "device_code": self._device_code,
            "manufacturer": self._manufacturer,
            "supported_models": self._supported_models,
            "supported_controller": self._supported_controller,
            "commands_encoding": self._commands_encoding,
        }

    async def async_turn_off(self):
        """Turn the media player off."""
        await self._send_command(STATE_OFF, [])

    async def async_turn_on(self):
        """Turn the media player off."""
        await self._send_command(STATE_ON, [])

    async def async_media_previous_track(self):
        """Send previous track command."""
        await self._send_command(self._state, [["previousChannel"]])

    async def async_media_next_track(self):
        """Send next track command."""
        await self._send_command(self._state, [["nextChannel"]])

    async def async_volume_down(self):
        """Turn volume down for media player."""
        await self._send_command(self._state, [["volumeDown"]])

    async def async_volume_up(self):
        """Turn volume up for media player."""
        await self._send_command(self._state, [["volumeUp"]])

    async def async_mute_volume(self, mute):
        """Mute the volume."""
        await self._send_command(self._state, [["mute"]])

    async def async_select_source(self, source):
        """Select channel from source."""
        self._source = source
        await self._send_command(self._state, [["sources", source]])

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Support channel change through play_media service."""
        if media_type != MEDIA_TYPE_CHANNEL:
            _LOGGER.error("invalid media type")
            return
        if not media_id.isdigit():
            _LOGGER.error("media_id must be a channel number")
            return

        self._source = "Channel {}".format(media_id)
        commands = []
        for digit in media_id:
            commands.append(["sources", "Channel {}".format(digit)])
        await self._send_command(STATE_ON, commands)

    async def _send_command(self, state, commands):
        async with self._temp_lock:

            if self._power_sensor and self._state != state:
                self._async_power_sensor_check_schedule(state)

            try:
                if self._state != state:
                    if state == STATE_ON:
                        if "on" not in self._commands.keys():
                            _LOGGER.error("Missing device IR code for 'on' command.")
                        else:
                            await self._controller.send(self._commands["on"])
                    elif state == STATE_OFF:
                        if "off" not in self._commands.keys():
                            _LOGGER.error("Missing device IR code for 'off' command.")
                        else:
                            await self._controller.send(self._commands["off"])
                    await asyncio.sleep(self._delay)

                for keys in commands:
                    data = self._commands
                    for idx in range(len(keys)):
                        if not (isinstance(data, dict) and keys[idx] in data):
                            _LOGGER.error(
                                "Missing device IR code for '%s' command.", keys[idx]
                            )
                            return
                        elif idx + 1 == len(keys):
                            if not isinstance(data[keys[idx]], str):
                                _LOGGER.error(
                                    "Missing device IR code for '%s' command.",
                                    keys[idx],
                                )
                                return
                            else:
                                await self._controller.send(data[keys[idx]])
                                await asyncio.sleep(self._delay)
                        elif isinstance(data[keys[idx]], dict):
                            data = data[keys[idx]]
                        else:
                            _LOGGER.error(
                                "Missing device IR code for '%s' command.", keys[idx]
                            )
                            return

                self._state = state
                self.async_write_ha_state()

            except Exception as e:
                _LOGGER.exception(
                    "Exception raised in the in the _send_command '%s'", e
                )

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
            self._on_by_remote = True
            self._state = STATE_ON
        elif new_state.state == STATE_OFF:
            self._on_by_remote = False
            if self._state == STATE_ON:
                self._state = STATE_OFF
                # self._source = None
        self.async_write_ha_state()

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
        _LOGGER.debug("Scheduled power sensor check for '%s' state.", state)
