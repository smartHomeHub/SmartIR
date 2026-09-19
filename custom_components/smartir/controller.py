from abc import ABC, abstractmethod
from base64 import b64decode, b64encode
import binascii
from copy import deepcopy
import struct
import requests
import logging
import json

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import ServiceValidationError
from . import Helper

_LOGGER = logging.getLogger(__name__)

BROADLINK_CONTROLLER = 'Broadlink'
XIAOMI_CONTROLLER = 'Xiaomi'
MQTT_CONTROLLER = 'MQTT'
LOOKIN_CONTROLLER = 'LOOKin'
ESPHOME_CONTROLLER = 'ESPHome'

ENC_BASE64 = 'Base64'
ENC_HEX = 'Hex'
ENC_PRONTO = 'Pronto'
ENC_RAW = 'Raw'

BROADLINK_COMMANDS_ENCODING = [ENC_BASE64, ENC_HEX, ENC_PRONTO]
XIAOMI_COMMANDS_ENCODING = [ENC_PRONTO, ENC_RAW]
MQTT_COMMANDS_ENCODING = [ENC_RAW]
LOOKIN_COMMANDS_ENCODING = [ENC_PRONTO, ENC_RAW]
ESPHOME_COMMANDS_ENCODING = [ENC_RAW]


def _command_string(command):
    """Require the string payload used by an IR controller."""
    if not isinstance(command, str) or not command:
        raise ServiceValidationError("IR command must be a nonempty string")
    return command


def _pronto_bytes(command):
    """Validate hexadecimal words without imposing a controller's Pronto dialect."""
    try:
        raw = bytearray.fromhex(_command_string(command).replace(' ', ''))
        if len(raw) < 8 or len(raw) % 2:
            raise ValueError("Invalid Pronto header")
        return raw
    except ValueError as err:
        raise ServiceValidationError("Invalid Pronto command") from err


def _pronto_pulses(command):
    """Convert the raw Pronto format supported by the Broadlink helper."""
    raw = _pronto_bytes(command)
    try:
        return Helper.pronto2lirc(raw)
    except (ValueError, IndexError, ZeroDivisionError) as err:
        raise ServiceValidationError("Invalid Broadlink Pronto command") from err


def get_controller(hass, controller, encoding, controller_data, delay):
    """Return a controller compatible with the specification provided."""
    controllers = {
        BROADLINK_CONTROLLER: BroadlinkController,
        XIAOMI_CONTROLLER: XiaomiController,
        MQTT_CONTROLLER: MQTTController,
        LOOKIN_CONTROLLER: LookinController,
        ESPHOME_CONTROLLER: ESPHomeController
    }
    try:
        return controllers[controller](hass, controller, encoding, controller_data, delay)
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

    async def send(self, command):
        """Prepare a command and await its controller handler."""
        await self.send_prepared(self.prepare(command))

    @abstractmethod
    def prepare(self, command):
        """Validate and convert a command without external side effects."""
        pass

    @abstractmethod
    async def send_prepared(self, prepared):
        """Send the payload returned by prepare, without converting it again."""
        pass


class BroadlinkController(AbstractController):
    """Controls a Broadlink device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in BROADLINK_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported "
                            "by the Broadlink controller.")

    def prepare(self, command):
        """Build the remote service payload before any command is sent."""
        commands = []

        if not isinstance(command, list):
            command = [command]
        if not command:
            raise ServiceValidationError("IR command list must not be empty")

        for _command in command:
            _command_string(_command)
            if self._encoding == ENC_HEX:
                try:
                    _command = binascii.unhexlify(_command)
                    _command = b64encode(_command).decode('utf-8')
                except (ValueError, binascii.Error) as err:
                    raise ServiceValidationError("Invalid Hex command") from err

            elif self._encoding == ENC_PRONTO:
                pulses = _pronto_pulses(_command)
                try:
                    _command = Helper.lirc2broadlink(pulses)
                    _command = b64encode(_command).decode('utf-8')
                except (ValueError, OverflowError, struct.error) as err:
                    raise ServiceValidationError("Invalid Pronto pulse widths") from err

            else:
                try:
                    # Match HA Broadlink's permissive decoding and missing padding.
                    if not b64decode(_command + '=' * (-len(_command) % 4)):
                        raise ValueError("Empty decoded command")
                except (ValueError, binascii.Error) as err:
                    raise ServiceValidationError("Invalid Base64 command") from err

            commands.append('b64:' + _command)

        return {
            ATTR_ENTITY_ID: self._controller_data,
            'command':  commands,
            'delay_secs': self._delay
        }

    async def send_prepared(self, prepared):
        """Await the remote handler; it may suppress device-level errors."""
        await self.hass.services.async_call(
            'remote', 'send_command', prepared, blocking=True)


class XiaomiController(AbstractController):
    """Controls a Xiaomi device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in XIAOMI_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported "
                            "by the Xiaomi controller.")

    def prepare(self, command):
        """Validate the command while preserving the remote payload."""
        _command_string(command)
        if self._encoding == ENC_PRONTO:
            _pronto_bytes(command)
        return {
            ATTR_ENTITY_ID: self._controller_data,
            'command':  self._encoding.lower() + ':' + command
        }

    async def send_prepared(self, prepared):
        """Await the remote service handler."""
        await self.hass.services.async_call(
            'remote', 'send_command', prepared, blocking=True)


class MQTTController(AbstractController):
    """Controls a MQTT device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in MQTT_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported "
                            "by the mqtt controller.")

    def prepare(self, command):
        """Keep MQTT's opaque payload unchanged."""
        if isinstance(command, (list, dict)):
            raise ServiceValidationError("MQTT publish payload must be a scalar")
        return {
            'topic': self._controller_data,
            'payload': deepcopy(command)
        }

    async def send_prepared(self, prepared):
        """Await the publish service handler."""
        await self.hass.services.async_call(
            'mqtt', 'publish', prepared, blocking=True)


class LookinController(AbstractController):
    """Controls a Lookin device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in LOOKIN_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported "
                            "by the LOOKin controller.")

    def prepare(self, command):
        """Build the request URL without performing HTTP I/O."""
        _command_string(command)
        if self._encoding == ENC_PRONTO:
            _pronto_bytes(command)
        encoding = self._encoding.lower().replace('pronto', 'prontohex')
        return f"http://{self._controller_data}/commands/ir/" \
                f"{encoding}/{command}"

    async def send_prepared(self, prepared):
        """Await the HTTP response and surface HTTP errors."""
        response = await self.hass.async_add_executor_job(requests.get, prepared)
        response.raise_for_status()


class ESPHomeController(AbstractController):
    """Controls a ESPHome device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in ESPHOME_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported "
                            "by the ESPHome controller.")
    
    def prepare(self, command):
        """Parse JSON without imposing a device-specific ESPHome argument schema."""
        try:
            payload = json.loads(_command_string(command))
        except ValueError as err:
            raise ServiceValidationError("Invalid ESPHome command JSON") from err
        return {'command': payload}

    async def send_prepared(self, prepared):
        """Await the ESPHome service handler."""
        await self.hass.services.async_call(
            'esphome', self._controller_data, prepared, blocking=True)