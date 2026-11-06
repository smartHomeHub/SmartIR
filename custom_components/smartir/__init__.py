import aiofiles
import aiohttp
import asyncio
import binascii
import re
import json
import logging
import os.path
import requests
import struct
import voluptuous as vol

from aiohttp import ClientSession
from homeassistant.const import (
    ATTR_FRIENDLY_NAME, __version__ as current_ha_version)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

_VERSION_RE = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def _version_tuple(version):
    """Return a comparable tuple for a version string.

    ``distutils.version.StrictVersion`` was removed from the standard
    library in Python 3.12, which made the whole integration fail to
    import (``ModuleNotFoundError: No module named 'distutils'``).
    """
    match = _VERSION_RE.match(str(version).strip().lstrip("vV"))
    if match is None:
        return (0, 0, 0)
    return tuple(int(part) if part is not None else 0 for part in match.groups())


def _notify(hass, message, title="SmartIR"):
    """Create a persistent notification.

    ``hass.components.persistent_notification`` is deprecated, the
    component module has to be imported and called directly instead.
    """
    from homeassistant.components import persistent_notification

    persistent_notification.async_create(hass, message, title=title)


DOMAIN = 'smartir'
VERSION = '1.18.2'
MANIFEST_URL = (
    "https://raw.githubusercontent.com/"
    "smartHomeHub/SmartIR/{}/"
    "custom_components/smartir/manifest.json")
REMOTE_BASE_URL = (
    "https://raw.githubusercontent.com/"
    "smartHomeHub/SmartIR/{}/"
    "custom_components/smartir/")
COMPONENT_ABS_DIR = os.path.dirname(
    os.path.abspath(__file__))

CONF_CHECK_UPDATES = 'check_updates'
CONF_UPDATE_BRANCH = 'update_branch'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_CHECK_UPDATES, default=True): cv.boolean,
        vol.Optional(CONF_UPDATE_BRANCH, default='master'): vol.In(
            ['master', 'rc'])
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Set up the SmartIR component."""
    conf = config.get(DOMAIN)

    if conf is None:
        return True

    check_updates = conf[CONF_CHECK_UPDATES]
    update_branch = conf[CONF_UPDATE_BRANCH]

    async def _check_updates(service):
        await _update(hass, update_branch)

    async def _update_component(service):
        await _update(hass, update_branch, True)

    hass.services.async_register(DOMAIN, 'check_updates', _check_updates)
    hass.services.async_register(DOMAIN, 'update_component', _update_component)

    if check_updates:
        await _update(hass, update_branch, False, False)

    return True

async def _update(hass, branch, do_update=False, notify_if_latest=True):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(MANIFEST_URL.format(branch)) as response:
                if response.status == 200:
                    
                    data = await response.json(content_type='text/plain')
                    min_ha_version = data['homeassistant']
                    last_version = data['updater']['version']
                    release_notes = data['updater']['releaseNotes']

                    if _version_tuple(last_version) <= _version_tuple(VERSION):
                        if notify_if_latest:
                            _notify(hass, 
                                "You're already using the latest version!", 
                                title='SmartIR')
                        return

                    if _version_tuple(current_ha_version) < _version_tuple(min_ha_version):
                        _notify(hass, 
                            "There is a new version of SmartIR integration, but it is **incompatible** "
                            "with your system. Please first update Home Assistant.", title='SmartIR')
                        return

                    if do_update is False:
                        _notify(hass, 
                            "A new version of SmartIR integration is available ({}). "
                            "Call the ``smartir.update_component`` service to update "
                            "the integration. \n\n **Release notes:** \n{}"
                            .format(last_version, release_notes), title='SmartIR')
                        return

                    # Begin update
                    files = data['updater']['files']
                    has_errors = False

                    for file in files:
                        try:
                            source = REMOTE_BASE_URL.format(branch) + file
                            dest = os.path.join(COMPONENT_ABS_DIR, file)
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            await Helper.downloader(source, dest)
                        except Exception:
                            has_errors = True
                            _LOGGER.error("Error updating %s. Please update the file manually.", file)

                    if has_errors:
                        _notify(hass, 
                            "There was an error updating one or more files of SmartIR. "
                            "Please check the logs for more information.", title='SmartIR')
                    else:
                        _notify(hass, 
                            "Successfully updated to {}. Please restart Home Assistant."
                            .format(last_version), title='SmartIR')
    except Exception:
       _LOGGER.error("An error occurred while checking for updates.")

class Helper():
    @staticmethod
    async def downloader(source, dest):
        async with aiohttp.ClientSession() as session:
            async with session.get(source) as response:
                if response.status == 200:
                    async with aiofiles.open(dest, mode='wb') as f:
                        await f.write(await response.read())
                else:
                    raise Exception("File not found")

    @staticmethod
    def pronto2lirc(pronto):
        codes = [int(binascii.hexlify(pronto[i:i+2]), 16) for i in range(0, len(pronto), 2)]

        if codes[0]:
            raise ValueError("Pronto code should start with 0000")
        if len(codes) != 4 + 2 * (codes[2] + codes[3]):
            raise ValueError("Number of pulse widths does not match the preamble")

        frequency = 1 / (codes[1] * 0.241246)
        return [int(round(code / frequency)) for code in codes[4:]]

    @staticmethod
    def lirc2broadlink(pulses):
        array = bytearray()

        for pulse in pulses:
            pulse = int(pulse * 269 / 8192)

            if pulse < 256:
                array += bytearray(struct.pack('>B', pulse))
            else:
                array += bytearray([0x00])
                array += bytearray(struct.pack('>H', pulse))

        packet = bytearray([0x26, 0x00])
        packet += bytearray(struct.pack('<H', len(array)))
        packet += array
        packet += bytearray([0x0d, 0x05])

        # Add 0s to make ultimate packet size a multiple of 16 for 128-bit AES encryption.
        remainder = (len(packet) + 4) % 16
        if remainder:
            packet += bytearray(16 - remainder)
        return packet