import asyncio
from base64 import b64encode
import binascii
import logging

from homeassistant.core import split_entity_id
from . import Helper

BROADLINK_CONTROLLER = 'Broadlink'
MQTT_CONTROLLER = 'MQTT'
XIAOMI_CONTROLLER = 'Xiaomi'

ENC_BASE64 = 'Base64'
ENC_HEX = 'Hex'
ENC_PRONTO = 'Pronto'
ENC_RAW = 'Raw'

BROADLINK_COMMANDS_ENCODING = [
    ENC_BASE64, ENC_HEX, ENC_PRONTO]

MQTT_COMMANDS_ENCODING = [ENC_RAW]

class Controller():
    def __init__(self, hass, controller, encoding, service, topic=None):
        if controller not in [
            BROADLINK_CONTROLLER, XIAOMI_CONTROLLER, MQTT_CONTROLLER]:
            raise Exception("The controller is not supported.")

        if controller == BROADLINK_CONTROLLER:
            if encoding not in BROADLINK_COMMANDS_ENCODING:
                raise Exception("The encoding is not supported "
                                "by the Broadlink controller.")

        if controller == XIAOMI_CONTROLLER:
            raise Exception("The Xiaomi IR controller "
                            "is not yet supported.")

        if controller == MQTT_CONTROLLER:
            if encoding not in MQTT_COMMANDS_ENCODING:
                raise Exception("The encoding is not supported "
                                "by the mqtt controller.")

            if not topic:
                raise Exception("controller_command_topic must be "
                                "specified for mqtt controllers.")

        self.hass = hass
        self._service_domain = split_entity_id(service)[0]
        self._service_name = split_entity_id(service)[1]
        self._command_topic = topic
        self._controller = controller
        self._encoding = encoding

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

            service_data = {
                'packet': command
            }

            await self.hass.services.async_call(
                self._service_domain, self._service_name, 
                service_data) 
                

        if self._controller == MQTT_CONTROLLER:
            service_data = {
                'topic': self._command_topic,
                'payload': command
            }

            await self.hass.services.async_call(
                self._service_domain, self._service_name, 
                service_data)