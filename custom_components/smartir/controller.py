from abc import ABC, abstractmethod
import asyncio
from base64 import b64encode, b64decode
import binascii
from homeassistant.components.zha.websocket_api import (
        IEEE_SCHEMA
)
import homeassistant.helpers.config_validation as cv
import requests
from typing import Any
import voluptuous as vol
from zha.application.const import (
    ATTR_IEEE,
    ATTR_CLUSTER_ID,
    ATTR_CLUSTER_TYPE,
    ATTR_COMMAND,
    ATTR_COMMAND_TYPE,
    ATTR_ENDPOINT_ID,
    ATTR_MANUFACTURER,
    ATTR_PARAMS,

    CLUSTER_COMMAND_SERVER,
    CLUSTER_TYPE_IN,
    CLUSTER_TYPE_OUT
)
from zigpy.types.named import EUI64
import logging
import json

from homeassistant.const import ATTR_ENTITY_ID
from . import Helper

_LOGGER = logging.getLogger(__name__)

BROADLINK_CONTROLLER = 'Broadlink'
XIAOMI_CONTROLLER = 'Xiaomi'
MQTT_CONTROLLER = 'MQTT'
LOOKIN_CONTROLLER = 'LOOKin'
ESPHOME_CONTROLLER = 'ESPHome'
ZHA_TUYA_BROADLINK_CONTROLLER = 'ZHATuyaBroadlink'

ENC_BASE64 = 'Base64'
ENC_HEX = 'Hex'
ENC_PRONTO = 'Pronto'
ENC_RAW = 'Raw'

BROADLINK_COMMANDS_ENCODING = [ENC_BASE64, ENC_HEX, ENC_PRONTO]
XIAOMI_COMMANDS_ENCODING = [ENC_PRONTO, ENC_RAW]
MQTT_COMMANDS_ENCODING = [ENC_RAW]
LOOKIN_COMMANDS_ENCODING = [ENC_PRONTO, ENC_RAW]
ESPHOME_COMMANDS_ENCODING = [ENC_RAW]
ZHA_TUYA_BROADLINK_COMMANDS_ENCODING = [ENC_BASE64, ENC_HEX, ENC_PRONTO, ENC_RAW]

CONF_ZHA_TUYA_BROADLINK_IEEE = "tuya-broadlink-ieee"
CONF_ENDPOINT_ID = ATTR_ENDPOINT_ID
CONF_CLUSTER_ID = ATTR_CLUSTER_ID
CONF_CLUSTER_TYPE = ATTR_CLUSTER_TYPE
CONF_COMMAND = ATTR_COMMAND
CONF_COMMAND_TYPE = ATTR_COMMAND_TYPE
CONF_MANUFACTURER = ATTR_MANUFACTURER

ZHA_TUYA_BROADLINK_SERVICE_DATA_DEFAULTS = {
    ATTR_ENDPOINT_ID: 1,
    ATTR_CLUSTER_ID: 0xe004,
    ATTR_CLUSTER_TYPE: CLUSTER_TYPE_IN,
    ATTR_COMMAND: 2,
    ATTR_COMMAND_TYPE: CLUSTER_COMMAND_SERVER,
    ATTR_PARAMS: {}
}

# allow the renaming of configuration attributes for future evolutions (ie. ZHA, not tuya)
ZHA_TUYA_BROADLINK_SERVICE_DATA_FROM_CONF = {
    CONF_ZHA_TUYA_BROADLINK_IEEE: ATTR_IEEE,
    CONF_ENDPOINT_ID: ATTR_ENDPOINT_ID,
    CONF_CLUSTER_ID: ATTR_CLUSTER_ID,
    CONF_CLUSTER_TYPE: ATTR_CLUSTER_TYPE,
    CONF_COMMAND: ATTR_COMMAND,
    CONF_COMMAND_TYPE: ATTR_COMMAND_TYPE,
    CONF_MANUFACTURER: ATTR_MANUFACTURER
}

ZHA_TUYA_BROADLINK_CONTROLLER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZHA_TUYA_BROADLINK_IEEE): vol.All(cv.string, EUI64.convert, repr),
        vol.Optional(CONF_ENDPOINT_ID): cv.positive_int,
        vol.Optional(CONF_CLUSTER_ID): cv.positive_int,
        vol.Optional(CONF_CLUSTER_TYPE): vol.Any(
            CLUSTER_TYPE_IN, CLUSTER_TYPE_OUT
        ),
        vol.Optional(CONF_COMMAND): cv.positive_int,
        vol.Optional(CONF_COMMAND_TYPE): vol.Any(CLUSTER_COMMAND_SERVER),
        vol.Optional(CONF_MANUFACTURER): vol.All(
            vol.Coerce(int), vol.Range(min=-1)
        ),
    },
)

CONTROLLER_DATA_SCHEMA = vol.Union(
    ZHA_TUYA_BROADLINK_CONTROLLER_DATA_SCHEMA,
    vol.Schema(cv.string),
    msg=f"""value should be a string
or a dictionary with at least the '{CONF_ZHA_TUYA_BROADLINK_IEEE}' device address\n"""
)

def cv_controller_data(value: Any) -> Any:
    """Validate a controller_data."""
    value = CONTROLLER_DATA_SCHEMA(value)
    _LOGGER.debug("Valid 'controller_data' value is: %s", str(value))
    return value

def get_controller(hass, controller, encoding, controller_data, delay):
    """Return a controller compatible with the specification provided."""
    controllers = {
        BROADLINK_CONTROLLER: BroadlinkController,
        XIAOMI_CONTROLLER: XiaomiController,
        MQTT_CONTROLLER: MQTTController,
        LOOKIN_CONTROLLER: LookinController,
        ESPHOME_CONTROLLER: ESPHomeController,
        ZHA_TUYA_BROADLINK_CONTROLLER: ZHATuyaBroadlinkController
    }
    try:
        if controller in (BROADLINK_CONTROLLER, ZHA_TUYA_BROADLINK_CONTROLLER):
            if isinstance(controller_data, dict) and CONF_ZHA_TUYA_BROADLINK_IEEE in controller_data:
                controller = ZHA_TUYA_BROADLINK_CONTROLLER
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

    @abstractmethod
    async def send(self, command):
        """Send a command."""
        pass


class BroadlinkController(AbstractController):
    """Controls a Broadlink device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in BROADLINK_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported "
                            "by the Broadlink controller.")

    async def send(self, command):
        """Send a command."""
        commands = []

        if not isinstance(command, list):
            command = [command]

        for _command in command:
            if self._encoding == ENC_HEX:
                try:
                    _command = binascii.unhexlify(_command)
                    _command = b64encode(_command).decode('utf-8')
                except:
                    raise Exception("Error while converting "
                                    "Hex to Base64 encoding")

            if self._encoding == ENC_PRONTO:
                try:
                    _command = _command.replace(' ', '')
                    _command = bytearray.fromhex(_command)
                    _command = Helper.pronto2lirc(_command)
                    _command = Helper.lirc2broadlink(_command)
                    _command = b64encode(_command).decode('utf-8')
                except:
                    raise Exception("Error while converting "
                                    "Pronto to Base64 encoding")

            commands.append('b64:' + _command)

        service_data = {
            ATTR_ENTITY_ID: self._controller_data,
            'command':  commands,
            'delay_secs': self._delay
        }

        await self.hass.services.async_call(
            'remote', 'send_command', service_data)


class XiaomiController(AbstractController):
    """Controls a Xiaomi device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in XIAOMI_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported "
                            "by the Xiaomi controller.")

    async def send(self, command):
        """Send a command."""
        service_data = {
            ATTR_ENTITY_ID: self._controller_data,
            'command':  self._encoding.lower() + ':' + command
        }

        await self.hass.services.async_call(
            'remote', 'send_command', service_data)


class MQTTController(AbstractController):
    """Controls a MQTT device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in MQTT_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported "
                            "by the mqtt controller.")

    async def send(self, command):
        """Send a command."""
        service_data = {
            'topic': self._controller_data,
            'payload': command
        }

        await self.hass.services.async_call(
            'mqtt', 'publish', service_data)


class LookinController(AbstractController):
    """Controls a Lookin device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in LOOKIN_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported "
                            "by the LOOKin controller.")

    async def send(self, command):
        """Send a command."""
        encoding = self._encoding.lower().replace('pronto', 'prontohex')
        url = f"http://{self._controller_data}/commands/ir/" \
                f"{encoding}/{command}"
        await self.hass.async_add_executor_job(requests.get, url)


class ESPHomeController(AbstractController):
    """Controls a ESPHome device."""

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in ESPHOME_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported "
                            "by the ESPHome controller.")

    async def send(self, command):
        """Send a command."""
        service_data = {'command':  json.loads(command)}

        await self.hass.services.async_call(
            'esphome', self._controller_data, service_data)


class ZHATuyaBroadlinkController(AbstractController):
    """Controls a Zigbee 3.0 Tuya device using ZHA."""

    def __init__(self, hass, controller, encoding, controller_data, delay):
        super().__init__(hass, controller, encoding, controller_data, delay)

        self._service_data = dict(ZHA_TUYA_BROADLINK_SERVICE_DATA_DEFAULTS)
        for kc, v in self._controller_data.items():
            ks = ZHA_TUYA_BROADLINK_SERVICE_DATA_FROM_CONF[kc]
            self._service_data[ks] = v 

    def check_encoding(self, encoding):
        """Check if the encoding is supported by the controller."""
        if encoding not in ZHA_TUYA_BROADLINK_COMMANDS_ENCODING:
            raise Exception("The encoding is not supported "
                            "by the ZHATuya Broadlink controller.")

    async def send(self, command):
        """Send a command."""
        if not isinstance(command, list):
            command = [command]

        service_data = dict(self._service_data)

        for _command in command:
            if self._encoding == ENC_BASE64:
                try:
                    _command = b64decode(_command)
                    _command = Helper.broadlink2tuya(_command)
                except:
                    raise Exception("Error while converting "
                                    "Base64 to Tuya encoding")

            if self._encoding == ENC_HEX:
                try:
                    _command = binascii.unhexlify(_command)
                    _command = Helper.broadlink2tuya(_command)
                except:
                    raise Exception("Error while converting "
                                    "Hex to Tuya encoding")

            if self._encoding == ENC_PRONTO:
                try:
                    _command = _command.replace(' ', '')
                    _command = bytearray.fromhex(_command)
                    _command = Helper.pronto2lirc(_command)
                    _command = Helper.lirc2broadlink(_command)
                    _command = Helper.broadlink2tuya(_command)
                except:
                    raise Exception("Error while converting "
                                    "Pronto to Tuya encoding")

            service_data[ATTR_PARAMS]['code'] = _command

            _LOGGER.debug("Calling service 'zha.issue_zigbee_cluster_command'\nwith 'service_data': %s",
                          str(service_data))

            await self.hass.services.async_call(
                'zha', 'issue_zigbee_cluster_command', service_data)
            await asyncio.sleep(self._delay)
