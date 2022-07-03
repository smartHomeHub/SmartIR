import json

from .abstract_controller import (
  AbstractController,
  ENC_RAW,
  ESPHOME_CONTROLLER,
)
class ESPHomeController(AbstractController):
  """Controls a ESPHome device."""
  name = ESPHOME_CONTROLLER

  @classmethod
  def toLirc(cls, command, data):
    ok = False
    if data._supported_controller == cls.name:
      if data._commands_encoding == ENC_RAW:
        command = json.loads(command) if type(command) is str else command
        ok = True
    return ok, command
  @classmethod
  def fromLirc(cls, command, data):
    return True, command

  def _decode(self, command, data):
    ok = False
    if data._commands_encoding == ENC_RAW:
      command = json.loads(command) if type(command) is str else command
      ok = True
    return ok, command

  async def _send(self, command, data):
    """Send a command."""
    service_data = {'command':  command}

    await data.hass.services.async_call(
        'esphome', data._controller_data, service_data)

ESPHomeController.register()
