import requests

from .abstract_controller import (
  AbstractController,
  ENC_PRONTO, ENC_RAW,
  LOOKIN_CONTROLLER
)

class LookinController(AbstractController):
  """Controls a Lookin device."""
  name = LOOKIN_CONTROLLER

  def _decode(self, command, data):
    ok = False
    if data._commands_encoding in [ENC_PRONTO, ENC_RAW]:
      encoding = data._commands_encoding.lower().replace('pronto', 'prontohex')
      command = f"http://{data._controller_data}/commands/ir/" \
              f"{encoding}/{command}"
      ok = True
    return ok, command

  async def _send(self, command, data):
    """Send a command."""
    await data.hass.async_add_executor_job(requests.get, command)


LookinController.register()
