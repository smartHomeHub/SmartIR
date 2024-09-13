from abc import ABC, abstractmethod
from base64 import b64encode
import ipaddress
import binascii
import requests
import struct
import json

from .controller_const import (
    BROADLINK_CONTROLLER,
    XIAOMI_CONTROLLER,
    MQTT_CONTROLLER,
    LOOKIN_CONTROLLER,
    ESPHOME_CONTROLLER,
    ZHA_CONTROLLER,
    UFOR11_CONTROLLER,
    ENC_HEX,
    ENC_PRONTO,
    BROADLINK_COMMANDS_ENCODING,
    XIAOMI_COMMANDS_ENCODING,
    MQTT_COMMANDS_ENCODING,
    LOOKIN_COMMANDS_ENCODING,
    ESPHOME_COMMANDS_ENCODING,
    ZHA_COMMANDS_ENCODING,
    UFOR11_COMMANDS_ENCODING,
    CONTROLLER_CONF,
)

from homeassistant.const import ATTR_ENTITY_ID


def get_controller(hass, controller, encoding, controller_data):
    """Return a controller compatible with the specification provided."""
    controllers = {
        BROADLINK_CONTROLLER: BroadlinkController,
        XIAOMI_CONTROLLER: XiaomiController,
        MQTT_CONTROLLER: MQTTController,
        LOOKIN_CONTROLLER: LookinController,
        ESPHOME_CONTROLLER: ESPHomeController,
        ZHA_CONTROLLER: ZHAController,
        UFOR11_CONTROLLER: UFOR11Controller,
    }

    # check controller compatibility
    if controller not in controllers:
        raise Exception("The controller is not supported.")

    if controller_data["controller_type"] != controller:
        raise Exception(
            "Configured controller is not supported by the device data file."
        )

    return controllers[controller](hass, controller, encoding, controller_data)


def get_controller_schema(vol, cv):
    """Return a controller schema."""
    schema = vol.Any(
        vol.Schema(
            {
                vol.Required(CONTROLLER_CONF["CONTROLLER_TYPE"]): vol.Equal(
                    BROADLINK_CONTROLLER
                ),
                vol.Required(CONTROLLER_CONF["REMOTE_ENTITY"]): cv.entity_id,
                vol.Optional(CONTROLLER_CONF["NUM_REPEATS"]): cv.positive_int,
                vol.Optional(CONTROLLER_CONF["DELAY_SECS"]): cv.positive_float,
            }
        ),
        vol.Schema(
            {
                vol.Required(CONTROLLER_CONF["CONTROLLER_TYPE"]): vol.Equal(
                    XIAOMI_CONTROLLER
                ),
                vol.Required(CONTROLLER_CONF["REMOTE_ENTITY"]): cv.entity_id,
            }
        ),
        vol.Schema(
            {
                vol.Required(CONTROLLER_CONF["CONTROLLER_TYPE"]): vol.Equal(
                    MQTT_CONTROLLER
                ),
                vol.Required(CONTROLLER_CONF["MQTT_TOPIC"]): cv.string,
            }
        ),
        vol.Schema(
            {
                vol.Required(CONTROLLER_CONF["CONTROLLER_TYPE"]): vol.Equal(
                    UFOR11_CONTROLLER
                ),
                vol.Required(CONTROLLER_CONF["MQTT_TOPIC"]): cv.string,
            }
        ),
        vol.Schema(
            {
                vol.Required(CONTROLLER_CONF["CONTROLLER_TYPE"]): vol.Equal(
                    LOOKIN_CONTROLLER
                ),
                vol.Required(CONTROLLER_CONF["REMOTE_HOST"]): vol.All(
                    ipaddress.ip_address, cv.string
                ),
            }
        ),
        vol.Schema(
            {
                vol.Required(CONTROLLER_CONF["CONTROLLER_TYPE"]): vol.Equal(
                    ESPHOME_CONTROLLER
                ),
                vol.Required(CONTROLLER_CONF["ESPHOME_SERVICE"]): cv.string,
            }
        ),
        vol.Schema(
            {
                vol.Required(CONTROLLER_CONF["CONTROLLER_TYPE"]): vol.Equal(
                    ZHA_CONTROLLER
                ),
                vol.Required(CONTROLLER_CONF["ZHA_IEEE"]): cv.string,
                vol.Required(CONTROLLER_CONF["ZHA_ENDPOINT_ID"]): cv.positive_int,
                vol.Required(CONTROLLER_CONF["ZHA_CLUSTER_ID"]): cv.positive_int,
                vol.Required(CONTROLLER_CONF["ZHA_CLUSTER_TYPE"]): cv.string,
                vol.Required(CONTROLLER_CONF["ZHA_COMMAND"]): cv.positive_int,
                vol.Required(CONTROLLER_CONF["ZHA_COMMAND_TYPE"]): cv.string,
            }
        ),
    )

    return schema


class AbstractController(ABC):
    """Representation of a controller."""

    def __init__(self, hass, controller, encoding, controller_data):
        self.hass = hass
        self._controller = controller
        self._encoding = encoding
        self._controller_data = controller_data

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
            ATTR_ENTITY_ID: self._controller_data[CONTROLLER_CONF["REMOTE_ENTITY"]],
            "command": commands,
        }
        if CONTROLLER_CONF["DELAY_SECS"] in self._controller_data:
            service_data["delay_secs"] = self._controller_data[
                CONTROLLER_CONF["DELAY_SECS"]
            ]
        if CONTROLLER_CONF["NUM_REPEATS"] in self._controller_data:
            service_data["num_repeats"] = self._controller_data[
                CONTROLLER_CONF["NUM_REPEATS"]
            ]

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
            ATTR_ENTITY_ID: self._controller_data[CONTROLLER_CONF["REMOTE_ENTITY"]],
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
        service_data = {
            "topic": self._controller_data[CONTROLLER_CONF["MQTT_TOPIC"]],
            "payload": command,
        }

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
        url = (
            "http://"
            + self._controller_data[CONTROLLER_CONF["REMOTE_HOST"]]
            + "/commands/ir/"
            + encoding
            + "/"
            + command
        )
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
            "esphome",
            self._controller_data[CONTROLLER_CONF["ESPHOME_SERVICE"]],
            service_data,
        )


class ZHAController(AbstractController):
    """Controls a ZHA device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in ZHA_COMMANDS_ENCODING:
            raise Exception(
                "The encoding is not supported " "by the ESPHome controller."
            )

    async def send(self, command):
        """Send a command."""
        service_data = {
            "ieee": self._controller_data[CONTROLLER_CONF["ZHA_IEEE"]],
            "endpoint_id": self._controller_data[CONTROLLER_CONF["ZHA_ENDPOINT_ID"]],
            "cluster_id": self._controller_data[CONTROLLER_CONF["ZHA_CLUSTER_ID"]],
            "cluster_type": self._controller_data[CONTROLLER_CONF["ZHA_CLUSTER_TYPE"]],
            "command": self._controller_data[CONTROLLER_CONF["ZHA_COMMAND"]],
            "command_type": self._controller_data[CONTROLLER_CONF["ZHA_COMMAND_TYPE"]],
            "params": {"code": command},
        }
        await self.hass.services.async_call(
            "zha", "issue_zigbee_cluster_command", service_data
        )


class UFOR11Controller(MQTTController):
    """Controls a UFO-R11 device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in UFOR11_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported by the UFO-R11 controller.")

    async def send(self, command):
        """Send a command."""
        service_data = {
            "topic": self._controller_data[CONTROLLER_CONF["MQTT_TOPIC"]],
            "payload": json.dumps({"ir_code_to_send": command}),
        }

        await self.hass.services.async_call("mqtt", "publish", service_data)


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
