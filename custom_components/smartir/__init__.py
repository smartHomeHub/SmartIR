import aiofiles
import aiohttp
import asyncio
from base64 import encodebytes
import binascii
from bisect import bisect
from distutils.version import StrictVersion
import io
from itertools import islice
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

                    if StrictVersion(last_version) <= StrictVersion(VERSION):
                        if notify_if_latest:
                            hass.components.persistent_notification.async_create(
                                "You're already using the latest version!",
                                title='SmartIR')
                        return

                    if StrictVersion(current_ha_version) < StrictVersion(min_ha_version):
                        hass.components.persistent_notification.async_create(
                            "There is a new version of SmartIR integration, but it is **incompatible** "
                            "with your system. Please first update Home Assistant.", title='SmartIR')
                        return

                    if do_update is False:
                        hass.components.persistent_notification.async_create(
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
                        hass.components.persistent_notification.async_create(
                            "There was an error updating one or more files of SmartIR. "
                            "Please check the logs for more information.", title='SmartIR')
                    else:
                        hass.components.persistent_notification.async_create(
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

    @staticmethod
    def broadlink2tuya(data, compression_level = 2):
        """
        Convert Broadlink remote codes into a format
        that can be used in Tuya's IR Blasters (ZS06, ZS08, TS1201, UFO-R11).

        Based on:
        * @vills (https://gist.github.com/vills/590c154b377ac50acab079328e4ddaf9)
        * @mildsunrise (https://gist.github.com/mildsunrise/1d576669b63a260d2cff35fda63ec0b5)
        * @elupus (https://github.com/elupus/irgen)
        (thank you!)
        """
        def decode_broadlink(data):
            """Generate raw values from broadlink data."""
            v = iter(data)
            code = next(v)
            next(v)  # repeat

            assert code == 0x26  # IR

            length = int.from_bytes(islice(v, 2), byteorder="little")
            assert length >= 3  # a At least trailer

            def decode_iter(x):
                while True:
                    try:
                        d = next(x)
                    except StopIteration:
                        return
                    if d == 0:
                        d = int.from_bytes(islice(x, 2), byteorder="big")

                    ms = int(round(d * 8192 / 269, 0))

                    # skip last time interval
                    if ms > 65535:
                        return

                    yield ms

            yield from decode_iter(islice(v, length))

            rem = list(v)
            if any(rem):
                _LOGGER.warning("Ignored extra data: %s", rem)

        def encode_tuya(signal, compression_level):
            """
            Encodes an IR signal
            into an IR code string for a Tuya blaster.
            """

            def compress(out: io.FileIO, data: bytes, level=2):
                """
                Takes a byte string and outputs a compressed "Tuya stream".
                Implemented compression levels:
                0 - copy over (no compression, 3.1% overhead)
                1 - eagerly use first length-distance pair found (linear)
                2 - eagerly use best length-distance pair found
                3 - optimal compression (n^3)
                """
                def emit_literal_block(out: io.FileIO, data: bytes):
                    length = len(data) - 1
                    assert 0 <= length < (1 << 5)
                    out.write(bytes([length]))
                    out.write(data)

                def emit_literal_blocks(out: io.FileIO, data: bytes):
                    for i in range(0, len(data), 32):
                        emit_literal_block(out, data[i : i + 32])

                def emit_distance_block(out: io.FileIO, length: int, distance: int):
                    distance -= 1
                    assert 0 <= distance < (1 << 13)
                    length -= 2
                    assert length > 0
                    block = bytearray()
                    if length >= 7:
                        assert length - 7 < (1 << 8)
                        block.append(length - 7)
                        length = 7
                    block.insert(0, length << 5 | distance >> 8)
                    block.append(distance & 0xFF)
                    out.write(block)

                if level == 0:
                    return emit_literal_blocks(out, data)

                W = 2**13  # window size
                L = 255 + 9  # maximum length

                def distance_candidates():
                    return range(1, min(pos, W) + 1)

                def find_length_for_distance(start: int) -> int:
                    length = 0
                    limit = min(L, len(data) - pos)
                    while length < limit and data[pos + length] == data[start + length]:
                        length += 1
                    return length

                def find_length_candidates():
                    return ((find_length_for_distance(pos - d), d) for d in distance_candidates())

                def find_length_cheap():
                    return next((c for c in find_length_candidates() if c[0] >= 3), None)

                def find_length_max():
                    return max(find_length_candidates(), key=lambda c: (c[0], -c[1]), default=None)

                if level >= 2:
                    suffixes = []
                    next_pos = 0

                    def key(n):
                        return data[n:]

                    def find_idx(n):
                        return bisect(suffixes, key(n), key=key)

                    def distance_candidates():
                        nonlocal next_pos
                        while next_pos <= pos:
                            if len(suffixes) == W:
                                suffixes.pop(find_idx(next_pos - W))
                            suffixes.insert(idx := find_idx(next_pos), next_pos)
                            next_pos += 1
                        idxs = (idx + i for i in (+1, -1))  # try +1 first
                        return (pos - suffixes[i] for i in idxs if 0 <= i < len(suffixes))

                if level <= 2:
                    find_length = {1: find_length_cheap, 2: find_length_max}[level]
                    block_start = pos = 0
                    while pos < len(data):
                        if (c := find_length()) and c[0] >= 3:
                            emit_literal_blocks(out, data[block_start:pos])
                            emit_distance_block(out, c[0], c[1])
                            pos += c[0]
                            block_start = pos
                        else:
                            pos += 1
                    emit_literal_blocks(out, data[block_start:pos])
                    return

                # use topological sort to find shortest path
                predecessors = [(0, None, None)] + [None] * len(data)

                def put_edge(cost, length, distance):
                    npos = pos + length
                    cost += predecessors[pos][0]
                    current = predecessors[npos]
                    if not current or cost < current[0]:
                        predecessors[npos] = cost, length, distance

                for pos in range(len(data)):
                    if c := find_length_max():
                        for length in range(3, c[0] + 1):
                            put_edge(2 if length < 9 else 3, length, c[1])
                    for bit_length in range(1, min(32, len(data) - pos) + 1):
                        put_edge(1 + bit_length, bit_length, 0)

                # reconstruct path, emit blocks
                blocks = []
                pos = len(data)
                while pos > 0:
                    _, length, distance = predecessors[pos]
                    pos -= length
                    blocks.append((pos, length, distance))
                for pos, length, distance in reversed(blocks):
                    if not distance:
                        emit_literal_block(out, data[pos : pos + length])
                    else:
                        emit_distance_block(out, length, distance)

            payload = b"".join(struct.pack("<H", t) for t in signal)
            compress(out := io.BytesIO(), payload, compression_level)
            payload = out.getvalue()
            return encodebytes(payload).decode("ascii").replace("\n", "")

        raw_data = list(decode_broadlink(data))

        _LOGGER.info("Raw data: %s", raw_data)

        tuya_data = encode_tuya(raw_data, compression_level=compression_level)

        _LOGGER.info("Tuya code: %s", tuya_data)

        return tuya_data
