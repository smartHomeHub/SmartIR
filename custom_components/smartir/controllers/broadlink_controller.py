from base64 import b64encode
import binascii

from homeassistant.const import ATTR_ENTITY_ID
from .abstract_controller import (
  AbstractController,
  ENC_BASE64, ENC_HEX, ENC_PRONTO,
  BROADLINK_CONTROLLER,
)
from .. import Helper

class BroadlinkController(AbstractController):
  """Controls a Broadlink device."""
  name = BROADLINK_CONTROLLER

  @classmethod
  def toLirc(cls, command, data):
    ok = False
    if data._supported_controller == cls.name:
      if data._commands_encoding == ENC_HEX:
        command = binascii.unhexlify(command)
        ok = True
      elif data._commands_encoding == ENC_PRONTO:
        command = command.replace(' ', '')
        command = bytearray.fromhex(command)
        command = Helper.pronto2lirc(command)
        ok = True
      elif data._commands_encoding == ENC_BASE64:
        ok = True
    if ok and type(command) is not list:
      command = Helper.broadlink2lirc(command)
    return ok, command

  @classmethod
  def fromLirc(cls, command, data):
    command = Helper.lirc2broadlink(command)
    command = b64encode(command).decode('utf-8')
    return True, command

  def _decode(self, command, data):
    ok = False
    if data._commands_encoding == ENC_HEX:
      command = binascii.unhexlify(command)
      command = b64encode(command).decode('utf-8')
      ok = True
    elif data._commands_encoding == ENC_PRONTO:
      command = command.replace(' ', '')
      command = bytearray.fromhex(command)
      command = Helper.pronto2lirc(command)
      command = Helper.lirc2broadlink(command)
      command = b64encode(command).decode('utf-8')
      ok = True
    elif data._commands_encoding == ENC_BASE64:
      ok = True

    return ok, command

  async def _send(self, command, data):
      service_data = {
        ATTR_ENTITY_ID: data._controller_data,
        'command':  command,
        'delay_secs': data._delay
      }

      await data.hass.services.async_call(
        'remote', 'send_command', service_data)


  async def send(self, command, data):
    commands = []

    if not isinstance(command, list):
      command = [command]

    for _command in command:
      commands.append('b64:' + self.decode(_command, data))
    await self._send(commands, data)

BroadlinkController.register()
