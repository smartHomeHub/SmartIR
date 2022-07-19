from homeassistant.const import ATTR_ENTITY_ID
from .abstract_controller import (
  AbstractController,
  ENC_PRONTO, ENC_RAW,
  XIAOMI_CONTROLLER
)

class XiaomiController(AbstractController):
  """Controls a Xiaomi device."""
  name = XIAOMI_CONTROLLER

  def _decode(self, command, data):
    ok = False
    if data._commands_encoding in [ENC_PRONTO, ENC_RAW]:
      command = data._commands_encoding.lower() + ':' + command
      ok = True
    return ok, command

  async def _send(self, command, data):
    """Send a command."""

    service_data = {
      ATTR_ENTITY_ID: data._controller_data,
      'command':  command
    }

    await data.hass.services.async_call(
      'remote', 'send_command', service_data)

XiaomiController.register()
