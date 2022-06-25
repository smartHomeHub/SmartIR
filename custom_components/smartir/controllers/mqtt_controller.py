from base64 import b64encode
import binascii
import json

from homeassistant.const import ATTR_ENTITY_ID
from .abstract_controller import (
  AbstractController,
  ENC_RAW,
  BROADLINK_CONTROLLER, ESPHOME_CONTROLLER, MQTT_CONTROLLER
)
from . import to_lirc

class MQTTController(AbstractController):
  """Controls a MQTT device."""
  name = MQTT_CONTROLLER

  @classmethod
  def toLirc(cls, command, data):
    ok = False
    if data._supported_controller == cls.name:
      if data._commands_encoding == ENC_RAW:
        command = json.loads(command) if type(command) is str else command
        if type(command) is list:
          ok = True
        elif type(command) is dict and command["protocol_name"] == "Raw":
          command = list(map(int, command["Raw"].split(",")))
          ok = True
    return ok, command

  @classmethod
  def fromLirc(cls, command, data):
    command = { "raw": ','.join(list(map(str, command))), "protocol_name": "Raw"}
    return True, command

  def _decode(self, command, data):
    ok = data._commands_encoding == ENC_RAW
    return ok, command

  async def _send(self, command, data):
    """Send a command."""

    service_data = {
        'topic': data._controller_data,
        'payload': command
    }

    await data.hass.services.async_call(
        'mqtt', 'publish', service_data)

MQTTController.register()
