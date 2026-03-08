from __future__ import annotations

import aiofiles
import json
import logging
import os
from collections import defaultdict
from typing import Any

from .const import PLATFORMS

_LOGGER = logging.getLogger(__name__)
COMPONENT_ABS_DIR = os.path.dirname(os.path.abspath(__file__))


def get_codes_dir(platform: str) -> str:
    return os.path.join(COMPONENT_ABS_DIR, "codes", platform)


async def async_load_device_data(device_code: int | str, platform: str) -> dict[str, Any]:
    path = os.path.join(get_codes_dir(platform), f"{device_code}.json")
    async with aiofiles.open(path, mode="r") as jfile:
        return json.loads(await jfile.read())


def load_catalog(platform: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    directory = get_codes_dir(platform)
    if not os.path.isdir(directory):
        return items

    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".json"):
            continue
        code = filename[:-5]
        path = os.path.join(directory, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as err:
            _LOGGER.warning("Skipping invalid SmartIR code file %s: %s", filename, err)
            continue

        manufacturer = data.get("manufacturer", "Unknown")
        models = data.get("supportedModels") or ["Unknown"]
        model_label = ", ".join(models[:3])
        if len(models) > 3:
            model_label += "…"
        label = f"{code} — {manufacturer} — {model_label}"
        items.append({
            "code": code,
            "manufacturer": manufacturer,
            "models": models,
            "label": label,
            "supported_controller": data.get("supportedController"),
            "commands_encoding": data.get("commandsEncoding"),
        })
    return items


def get_manufacturers(platform: str) -> list[str]:
    return sorted({item["manufacturer"] for item in load_catalog(platform)})


def get_models_for_manufacturer(platform: str, manufacturer: str) -> list[dict[str, Any]]:
    return [item for item in load_catalog(platform) if item["manufacturer"] == manufacturer]


def infer_title(data: dict[str, Any]) -> str:
    platform = data.get("platform", "device")
    name = data.get("name")
    if name:
        return name
    return f"SmartIR {platform.replace('_', ' ').title()} {data.get('device_code', '')}".strip()
    
import struct
import binascii


class Helper:

    @staticmethod
    def pronto2lirc(pronto):

        codes = [
            int(binascii.hexlify(pronto[i:i + 2]), 16)
            for i in range(0, len(pronto), 2)
        ]

        if codes[0]:
            raise ValueError("Pronto code should start with 0000")

        if len(codes) != 4 + 2 * (codes[2] + codes[3]):
            raise ValueError("Number of pulse widths does not match")

        frequency = 1 / (codes[1] * 0.241246)

        return [int(round(code / frequency)) for code in codes[4:]]

    @staticmethod
    def lirc2broadlink(pulses):

        array = bytearray()

        for pulse in pulses:

            pulse = int(pulse * 269 / 8192)

            if pulse < 256:
                array += bytearray(struct.pack(">B", pulse))
            else:
                array += bytearray([0x00])
                array += bytearray(struct.pack(">H", pulse))

        packet = bytearray([0x26, 0x00])
        packet += bytearray(struct.pack("<H", len(array)))
        packet += array
        packet += bytearray([0x0D, 0x05])

        remainder = (len(packet) + 4) % 16

        if remainder:
            packet += bytearray(16 - remainder)

        return packet
