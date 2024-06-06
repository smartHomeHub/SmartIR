import asyncio
import logging

import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntity, PLATFORM_SCHEMA
from homeassistant.components.media_player.const import (
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_NEXT_TRACK,
    SUPPORT_VOLUME_STEP,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_SELECT_SOURCE,
    MEDIA_TYPE_CHANNEL,
)
from homeassistant.const import CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, Event, EventStateChangedData
from homeassistant.helpers.event import async_track_state_change_event
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType
from . import DeviceData
from .controller import get_controller

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "SmartIR Media Player"
DEFAULT_DEVICE_CLASS = "tv"
DEFAULT_DELAY = 0.5

CONF_UNIQUE_ID = "unique_id"
CONF_DEVICE_CODE = "device_code"
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"
CONF_POWER_SENSOR = "power_sensor"
CONF_SOURCE_NAMES = "source_names"
CONF_DEVICE_CLASS = "device_class"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_DEVICE_CODE): cv.positive_int,
        vol.Required(CONF_CONTROLLER_DATA): cv.string,
        vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): cv.string,
        vol.Optional(CONF_POWER_SENSOR): cv.entity_id,
        vol.Optional(CONF_SOURCE_NAMES): dict,
        vol.Optional(CONF_DEVICE_CLASS, default=DEFAULT_DEVICE_CLASS): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant, config: ConfigType, async_add_entities, discovery_info=None
):
    """Set up the IR Media Player platform."""
    _LOGGER.debug("Setting up the smartir media player platform")
    if not (
        device_data := await DeviceData.load_file(
            config.get(CONF_DEVICE_CODE),
            "media_player",
            [
                "manufacturer",
                "supportedModels",
                "supportedController",
                "commandsEncoding",
            ],
            hass,
        )
    ):
        _LOGGER.error("Smartir media player device data init failed!")
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

        self._manufacturer = device_data["manufacturer"]
        self._supported_models = device_data["supportedModels"]
        self._supported_controller = device_data["supportedController"]
        self._commands_encoding = device_data["commandsEncoding"]
        self._commands = device_data["commands"]

        self._state = STATE_OFF
        self._sources_list = []
        self._source = None
        self._support_flags = 0

        self._device_class = config.get(CONF_DEVICE_CLASS)

        # Supported features
        if "off" in self._commands and self._commands["off"] is not None:
            self._support_flags = self._support_flags | SUPPORT_TURN_OFF

        if "on" in self._commands and self._commands["on"] is not None:
            self._support_flags = self._support_flags | SUPPORT_TURN_ON

        if (
            "previousChannel" in self._commands
            and self._commands["previousChannel"] is not None
        ):
            self._support_flags = self._support_flags | SUPPORT_PREVIOUS_TRACK

        if (
            "nextChannel" in self._commands
            and self._commands["nextChannel"] is not None
        ):
            self._support_flags = self._support_flags | SUPPORT_NEXT_TRACK

        if (
            "volumeDown" in self._commands and self._commands["volumeDown"] is not None
        ) or ("volumeUp" in self._commands and self._commands["volumeUp"] is not None):
            self._support_flags = self._support_flags | SUPPORT_VOLUME_STEP

        if "mute" in self._commands and self._commands["mute"] is not None:
            self._support_flags = self._support_flags | SUPPORT_VOLUME_MUTE

        if "sources" in self._commands and self._commands["sources"] is not None:
            self._support_flags = (
                self._support_flags | SUPPORT_SELECT_SOURCE | SUPPORT_PLAY_MEDIA
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

        last_state = await self.async_get_last_state()

        if last_state is not None:
            self._state = last_state.state

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
        if self._on_by_remote:
            return STATE_UNKNOWN
        return self._source

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return self._support_flags

    @property
    def extra_state_attributes(self):
        """Platform specific attributes."""
        return {
            "device_code": self._device_code,
            "manufacturer": self._manufacturer,
            "supported_models": self._supported_models,
            "supported_controller": self._supported_controller,
            "commands_encoding": self._commands_encoding,
        }

    async def async_turn_off(self):
        """Turn the media player off."""
        if not "off" in self._commands.keys():
            _LOGGER.error("Missing device IR code for 'off' command.")
            return

        await self._controller.send(self._commands["off"])
        self._state = STATE_OFF
        self._source = None
        self.async_write_ha_state()

    async def async_turn_on(self):
        """Turn the media player off."""
        if not "on" in self._commands.keys():
            _LOGGER.error("Missing device IR code for 'on' command.")
            return

        await self.send_command(self._commands["on"])
        self._state = STATE_ON
        self.async_write_ha_state()

    async def async_media_previous_track(self):
        """Send previous track command."""
        if not "previousChannel" in self._commands.keys():
            _LOGGER.error("Missing device IR code for 'previousChannel' command.")
            return

        await self.send_command(self._commands["previousChannel"])
        self.async_write_ha_state()

    async def async_media_next_track(self):
        """Send next track command."""
        if not "nextChannel" in self._commands.keys():
            _LOGGER.error("Missing device IR code for 'nextChannel' command.")
            return

        await self.send_command(self._commands["nextChannel"])
        self.async_write_ha_state()

    async def async_volume_down(self):
        """Turn volume down for media player."""
        if not "volumeDown" in self._commands.keys():
            _LOGGER.error("Missing device IR code for 'volumeDown' command.")
            return

        await self.send_command(self._commands["volumeDown"])
        self.async_write_ha_state()

    async def async_volume_up(self):
        """Turn volume up for media player."""
        if "volumeUp" in self._commands.keys():
            _LOGGER.error("Missing device IR code for 'volumeUp' command.")
            return

        await self.send_command(self._commands["volumeUp"])
        self.async_write_ha_state()

    async def async_mute_volume(self, mute):
        """Mute the volume."""
        if not "mute" in self._commands.keys():
            _LOGGER.error("Missing device IR code for 'mute' command.")
            return

        await self.send_command(self._commands["mute"])
        self.async_write_ha_state()

    async def async_select_source(self, source):
        """Select channel from source."""
        if not (
            "sources" in self._commands.keys()
            and isinstance(self._commands["sources"], dict)
            and source in self._commands["sources"].keys()
        ):
            _LOGGER.error(
                "Missing device IR code for 'sources' source '%s' command.", source
            )
            return

        await self.send_command(self._commands["sources"][source])
        self._source = source
        self.async_write_ha_state()

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Support channel change through play_media service."""
        if self._state == STATE_OFF:
            await self.async_turn_on()

        if media_type != MEDIA_TYPE_CHANNEL:
            _LOGGER.error("invalid media type")
            return
        if not media_id.isdigit():
            _LOGGER.error("media_id must be a channel number")
            return

        self._source = "Channel {}".format(media_id)
        for digit in media_id:
            source = "Channel {}".format(digit)
            if not (
                "sources" in self._commands.keys()
                and isinstance(self._commands["sources"], dict)
                and source in self._commands["sources"].keys()
            ):
                _LOGGER.error(
                    "Missing device IR code for 'sources' source '%s' command.", source
                )
                return
            await self.send_command(self._commands["sources"][source])
        self.async_write_ha_state()

    async def send_command(self, command):
        async with self._temp_lock:
            try:
                await self._controller.send(command)
            except Exception as e:
                _LOGGER.exception(e)

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
            self.async_write_ha_state()
        elif new_state.state == STATE_OFF:
            self._on_by_remote = False
            if self._state != STATE_OFF:
                self._state = STATE_OFF
                self._source = None
            self.async_write_ha_state()
