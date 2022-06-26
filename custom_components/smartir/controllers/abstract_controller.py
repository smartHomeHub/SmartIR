from abc import ABC, abstractmethod
import logging

BROADLINK_CONTROLLER = 'Broadlink'
XIAOMI_CONTROLLER = 'Xiaomi'
MQTT_CONTROLLER = 'MQTT'
LOOKIN_CONTROLLER = 'LOOKin'
ESPHOME_CONTROLLER = 'ESPHome'

ENC_BASE64 = 'Base64'
ENC_HEX = 'Hex'
ENC_PRONTO = 'Pronto'
ENC_RAW = 'Raw'

_LOGGER = logging.getLogger(__name__)

def get_controller(name):
  return AbstractController.get(name)

def to_lirc(command, data):
  Controller = AbstractController.controllers[data._supported_controller]
  return Controller.toLirc(command, data)

# Singleton Controller Class
class AbstractController(ABC):
  controllers = {}
  name = "None" # the Controller Name to register
  def __new__(cls, *args, **kwargs):
    # if not hasattr(cls, 'instance'): # this will check attr derived in given class
    if 'instance' not in cls.__dict__:
      cls.instance = super(AbstractController, cls).__new__(cls, *args, **kwargs)
    return cls.instance

  @classmethod
  def toLirc(cls, command, data):
    return False, command
  @classmethod
  def fromLirc(cls, command, data):
    return False, command

  def _decode(self, command, data):
    """decode a command."""
    return True, command

  def decode(self, command, data):
    ok = False
    if data._supported_controller == self.name:
      ok, command = self._decode(command, data)
    else:
      ok, command = to_lirc(command, data)
      if ok:
        ok, command = self.fromLirc(command, data)

    if not ok:
      raise Exception("The {controller}'s {encoding} encoding is not supported "
                      "by {me} controller.".format(
                        controller = data._supported_controller,
                        encoding = data._commands_encoding,
                        me = self.name)
                      )
    return command

  @abstractmethod
  async def _send(self, command, data):
    """Send a command."""
    pass

  async def send(self, command, data):
    """Send a command."""
    await self._send(self.decode(command, data), data)


  @classmethod
  def register(cls):
    if 'name' not in cls.__dict__:
      raise Exception("Missing Controller Name to register")
    _LOGGER.debug("register AbstractController.controllers= %s", AbstractController.controllers)
    cls.controllers[cls.name] = cls

  @staticmethod
  def get(name):
    _LOGGER.debug("get AbstractController.controllers= %s", AbstractController.controllers)
    return AbstractController.controllers[name]()
