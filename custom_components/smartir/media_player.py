import asyncio
import logging

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaType,
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

    device_data = await async_load_device_data(device_code, "media_player")

    async_add_entities(
        [
            SmartIRMediaPlayer(
                hass,
                config,
                device_data,
            )
        ],
        True,
    )


class SmartIRMediaPlayer(MediaPlayerEntity, RestoreEntity):

    def __init__(self, hass, config, device_data):

        self.hass = hass

        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)

        self._controller_data = config.get(CONF_CONTROLLER_DATA)
        self._delay = config.get(CONF_DELAY, DEFAULT_DELAY)

        self._supported_controller = device_data["supportedController"]
        self._commands_encoding = device_data["commandsEncoding"]

        self._commands = device_data["commands"]

        self._state = STATE_OFF
        self._source = None
        self._sources_list = []

        self._support_flags = 0

        if "off" in self._commands:
            self._support_flags |= MediaPlayerEntityFeature.TURN_OFF

        if "on" in self._commands:
            self._support_flags |= MediaPlayerEntityFeature.TURN_ON

        if "previousChannel" in self._commands:
            self._support_flags |= MediaPlayerEntityFeature.PREVIOUS_TRACK

        if "nextChannel" in self._commands:
            self._support_flags |= MediaPlayerEntityFeature.NEXT_TRACK

        if "volumeDown" in self._commands or "volumeUp" in self._commands:
            self._support_flags |= MediaPlayerEntityFeature.VOLUME_STEP

        if "mute" in self._commands:
            self._support_flags |= MediaPlayerEntityFeature.VOLUME_MUTE

        if "sources" in self._commands:

            self._support_flags |= (
                MediaPlayerEntityFeature.SELECT_SOURCE
                | MediaPlayerEntityFeature.PLAY_MEDIA
            )

            self._sources_list = list(self._commands["sources"].keys())

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
            self._state = last_state.state

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def source_list(self):
        return self._sources_list

    @property
    def source(self):
        return self._source

    @property
    def supported_features(self):
        return self._support_flags

    async def async_turn_on(self):

        await self.send_command(self._commands["on"])

        self._state = STATE_ON

        self.async_write_ha_state()

    async def async_turn_off(self):

        await self.send_command(self._commands["off"])

        self._state = STATE_OFF

        self.async_write_ha_state()

    async def async_media_previous_track(self):

        await self.send_command(self._commands["previousChannel"])

    async def async_media_next_track(self):

        await self.send_command(self._commands["nextChannel"])

    async def async_volume_down(self):

        await self.send_command(self._commands["volumeDown"])

    async def async_volume_up(self):

        await self.send_command(self._commands["volumeUp"])

    async def async_mute_volume(self, mute):

        await self.send_command(self._commands["mute"])

    async def async_select_source(self, source):

        self._source = source

        await self.send_command(self._commands["sources"][source])

        self.async_write_ha_state()

    async def async_play_media(self, media_type, media_id, **kwargs):

        if media_type != MediaType.CHANNEL:
            return

        for digit in media_id:
            await self.send_command(
                self._commands["sources"].get(f"Channel {digit}")
            )

    async def send_command(self, command):

        async with self._temp_lock:

            try:

                await self._controller.send(command)

            except Exception as e:

                _LOGGER.exception(e)