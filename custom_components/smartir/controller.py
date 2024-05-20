from abc import ABC, abstractmethod
from base64 import b64encode
import binascii
import requests
import logging
import struct
import json

from homeassistant.const import ATTR_ENTITY_ID

_LOGGER = logging.getLogger(__name__)

BROADLINK_CONTROLLER = "Broadlink"
XIAOMI_CONTROLLER = "Xiaomi"
MQTT_CONTROLLER = "MQTT"
LOOKIN_CONTROLLER = "LOOKin"
ESPHOME_CONTROLLER = "ESPHome"

ENC_BASE64 = "Base64"
ENC_HEX = "Hex"
ENC_PRONTO = "Pronto"
ENC_RAW = "Raw"

BROADLINK_COMMANDS_ENCODING = [ENC_BASE64, ENC_HEX, ENC_PRONTO]
XIAOMI_COMMANDS_ENCODING = [ENC_PRONTO, ENC_RAW]
MQTT_COMMANDS_ENCODING = [ENC_RAW]
LOOKIN_COMMANDS_ENCODING = [ENC_PRONTO, ENC_RAW]
ESPHOME_COMMANDS_ENCODING = [ENC_RAW]


def get_controller(hass, controller, encoding, controller_data, delay):
    """Return a controller compatible with the specification provided."""
    controllers = {
        BROADLINK_CONTROLLER: BroadlinkController,
        XIAOMI_CONTROLLER: XiaomiController,
        MQTT_CONTROLLER: MQTTController,
        LOOKIN_CONTROLLER: LookinController,
        ESPHOME_CONTROLLER: ESPHomeController,
    }
    try:
        return controllers[controller](
            hass, controller, encoding, controller_data, delay
        )
    except KeyError:
        raise Exception("The controller is not supported.")


class AbstractController(ABC):
    """Representation of a controller."""

    def __init__(self, hass, controller, encoding, controller_data, delay):
        self.check_encoding(encoding)
        self.hass = hass
        self._controller = controller
        self._encoding = encoding
        self._controller_data = controller_data
        self._delay = delay

    @abstractmethod
    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        pass

    @abstractmethod
    async def send(self, command):
        """Send a command."""
        pass


class BroadlinkController(AbstractController):
    """Controls a Broadlink device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in BROADLINK_COMMANDS_ENCODING:
            raise Exception(
                "The encoding is not supported " "by the Broadlink controller."
            )

    async def send(self, command):
        """Send a command."""
        commands = []

        if not isinstance(command, list):
            command = [command]

        for _command in command:
            if self._encoding == ENC_HEX:
                try:
                    _command = binascii.unhexlify(_command)
                    _command = b64encode(_command).decode("utf-8")
                except:
                    raise Exception("Error while converting " "Hex to Base64 encoding")

            if self._encoding == ENC_PRONTO:
                try:
                    _command = _command.replace(" ", "")
                    _command = bytearray.fromhex(_command)
                    _command = Helper.pronto2lirc(_command)
                    _command = Helper.lirc2broadlink(_command)
                    _command = b64encode(_command).decode("utf-8")
                except:
                    raise Exception(
                        "Error while converting " "Pronto to Base64 encoding"
                    )

            commands.append("b64:" + _command)

        service_data = {
            ATTR_ENTITY_ID: self._controller_data,
            "command": commands,
            "delay_secs": self._delay,
        }

        await self.hass.services.async_call("remote", "send_command", service_data)


class XiaomiController(AbstractController):
    """Controls a Xiaomi device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in XIAOMI_COMMANDS_ENCODING:
            raise Exception(
                "The encoding is not supported " "by the Xiaomi controller."
            )

    async def send(self, command):
        """Send a command."""
        service_data = {
            ATTR_ENTITY_ID: self._controller_data,
            "command": self._encoding.lower() + ":" + command,
        }

        await self.hass.services.async_call("remote", "send_command", service_data)


class MQTTController(AbstractController):
    """Controls a MQTT device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in MQTT_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported " "by the mqtt controller.")

    async def send(self, command):
        """Send a command."""
        service_data = {"topic": self._controller_data, "payload": command}

        await self.hass.services.async_call("mqtt", "publish", service_data)


class LookinController(AbstractController):
    """Controls a Lookin device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in LOOKIN_COMMANDS_ENCODING:
            raise Exception(
                "The encoding is not supported " "by the LOOKin controller."
            )

    async def send(self, command):
        """Send a command."""
        encoding = self._encoding.lower().replace("pronto", "prontohex")
        url = f"http://{self._controller_data}/commands/ir/" f"{encoding}/{command}"
        await self.hass.async_add_executor_job(requests.get, url)


class ESPHomeController(AbstractController):
    """Controls a ESPHome device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in ESPHOME_COMMANDS_ENCODING:
            raise Exception(
                "The encoding is not supported " "by the ESPHome controller."
            )

    async def send(self, command):
        """Send a command."""
        service_data = {"command": json.loads(command)}

        await self.hass.services.async_call(
            "esphome", self._controller_data, service_data
        )


class Helper:
    """Static shared functions."""

    @staticmethod
    def pronto2lirc(pronto):
        codes = [
            int(binascii.hexlify(pronto[i : i + 2]), 16)
            for i in range(0, len(pronto), 2)
        ]

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
                array += bytearray(struct.pack(">B", pulse))
            else:
                array += bytearray([0x00])
                array += bytearray(struct.pack(">H", pulse))

        packet = bytearray([0x26, 0x00])
        packet += bytearray(struct.pack("<H", len(array)))
        packet += array
        packet += bytearray([0x0D, 0x05])

        # Add 0s to make ultimate packet size a multiple of 16 for 128-bit AES encryption.
        remainder = (len(packet) + 4) % 16
        if remainder:
            packet += bytearray(16 - remainder)
        return packet
