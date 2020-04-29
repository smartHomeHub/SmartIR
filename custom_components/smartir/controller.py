import asyncio
from base64 import b64encode
import binascii
import logging
import re

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import split_entity_id
from . import Helper

_LOGGER = logging.getLogger(__name__)

BROADLINK_CONTROLLER = 'Broadlink'
XIAOMI_CONTROLLER = 'Xiaomi'
MQTT_CONTROLLER = 'MQTT'

ENC_BASE64 = 'Base64'
ENC_HEX = 'Hex'
ENC_PRONTO = 'Pronto'
ENC_RAW = 'Raw'
ENC_SENDIR = 'SENDIR'
ENC_GC = 'GlobalCache'

BROADLINK_COMMANDS_ENCODING = [
    ENC_BASE64, ENC_HEX, ENC_PRONTO, ENC_RAW]

XIAOMI_COMMANDS_ENCODING = [
    ENC_PRONTO, ENC_RAW]

MQTT_COMMANDS_ENCODING = [ENC_RAW, ENC_BASE64, ENC_HEX, ENC_PRONTO, ENC_SENDIR, ENC_GC]


class Controller():
    def __init__(self, hass, controller, encoding, controller_data):
        controller = self.getActualController(controller_data,controller)
        _LOGGER.info("SmartIR Controller %s", controller)
        if controller not in [
                BROADLINK_CONTROLLER, XIAOMI_CONTROLLER, MQTT_CONTROLLER]:
            raise Exception("The controller is not supported.")

        if controller == BROADLINK_CONTROLLER:
            if encoding not in BROADLINK_COMMANDS_ENCODING:
                raise Exception("The encoding is not supported "
                                "by the Broadlink controller.")

        if controller == XIAOMI_CONTROLLER:
            if encoding not in XIAOMI_COMMANDS_ENCODING:
                raise Exception("The encoding is not supported "
                                "by the Xiaomi controller.")

        if controller == MQTT_CONTROLLER:
            if encoding not in MQTT_COMMANDS_ENCODING:
                raise Exception("The encoding is not supported "
                                "by the mqtt controller.")

        self.hass = hass
        self._controller = controller
        self._encoding = encoding
        self._controller_data = controller_data

    def isBroadlinkController(self,controller_data):
        isTrue = False
        _LOGGER.debug("Controller_Data %s", controller_data)
        return isTrue

    def isXIAOMIController(self,controller_data):
        isTrue = False
        _LOGGER.debug("Controller_Data %s", controller_data)
        return isTrue

    def isMQTTController(self,controller_data):
        isTrue = False
        pattern = re.compile('cmnd\/\w+\/irsend')
        _LOGGER.debug("Controller_Data %s", controller_data)
        match = pattern.match(controller_data)
        if match:
            print('Match found: ', match.group())
            isTrue = True
        else:
            print('No match')
        return isTrue

    def getActualController(self,controller_data,supported_controller):
        actual_controller = None
        try:
            _LOGGER.debug("Controller_Data %s", controller_data)
            if self.isBroadlinkController(controller_data) is True:
                actual_controller = BROADLINK_CONTROLLER
            elif self.isXIAOMIController(controller_data) is True:
                actual_controller = XIAOMI_CONTROLLER
            elif self.isMQTTController(controller_data) is True:
                actual_controller = MQTT_CONTROLLER
        except:
            raise Exception("Error while detecting "
                            "actual controller")
        _LOGGER.debug("Detected Controller %s", actual_controller)
        if actual_controller in supported_controller:
            supported_controller = actual_controller
        else:
            supported_controller = None
        _LOGGER.debug("Supported Controller %s", supported_controller)   
        return supported_controller

    async def send(self, command):
        if self._controller == BROADLINK_CONTROLLER:
            if self._encoding == ENC_HEX:
                try:
                    command = binascii.unhexlify(command)
                    command = b64encode(command).decode('utf-8')
                except:
                    raise Exception("Error while converting "
                                    "Hex to Base64 encoding")

            if self._encoding == ENC_PRONTO:
                try:
                    command = command.replace(' ', '')
                    command = bytearray.fromhex(command)
                    command = Helper.pronto2lirc(command)
                    command = Helper.lirc2broadlink(command)
                    command = b64encode(command).decode('utf-8')
                except:
                    raise Exception("Error while converting "
                                    "Pronto to Base64 encoding")

            if self._encoding == ENC_RAW:
                try:
                    command = Helper.raw2b64broadlink(command)
                except:
                    raise Exception("Error while converting "
                                    "Broadlink Base64 to Raw encoding")
            service_data = {
                'host': self._controller_data,
                'packet': command
            }

            await self.hass.services.async_call(
                'broadlink', 'send', service_data)

        if self._controller == XIAOMI_CONTROLLER:
            service_data = {
                ATTR_ENTITY_ID: self._controller_data,
                'command':  self._encoding.lower() + ':' + command
            }

            await self.hass.services.async_call(
               'remote', 'send_command', service_data)

        if self._controller == MQTT_CONTROLLER:

            _LOGGER.debug("Encoding %s", self._encoding)
            if self._encoding == ENC_GC:
                try:
                    command = command.replace(' ', '')
                    command = Helper.gc2lirc(command)
                    command = Helper.lirc2broadlink(command)
                    command = b64encode(command).decode('utf-8')
                except:
                    raise Exception("Error while converting "
                                    "GlobalCache to Broadlink Base64 encoding")

            if self._encoding == ENC_HEX:
                try:
                    command = binascii.unhexlify(command)
                    command = b64encode(command).decode('utf-8')
                except:
                    raise Exception("Error while converting "
                                    "Hex to Broadlink Base64 encoding")

            if self._encoding == ENC_PRONTO:
                try:
                    command = command.replace(' ', '')
                    command = bytearray.fromhex(command)
                    command = Helper.pronto2lirc(command)
                    command = Helper.lirc2broadlink(command)
                    command = b64encode(command).decode('utf-8')
                except:
                    raise Exception("Error while converting "
                                    "Pronto to Broadlink Base64 encoding")

            if self._encoding != ENC_RAW:
                try:
                    _LOGGER.debug("Command as Broadlink Base64: %s", command)
                    command = Helper.b64broadlink2raw(command)
                except:
                    raise Exception("Error while converting "
                                    "Broadlink Base64 to Raw encoding")

            _LOGGER.debug("Sending Payload %s", command)

            service_data = {
                'topic': self._controller_data,
                'payload': command
            }

            await self.hass.services.async_call(
               'mqtt', 'publish', service_data)
