"""Import actual source with small HA boundary substitutes, without starting HA."""

import ast
import binascii
import importlib
import struct
from enum import IntFlag, StrEnum
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import voluptuous as vol


class HVACMode(StrEnum):
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    HEAT_COOL = "heat_cool"
    AUTO = "auto"
    DRY = "dry"
    FAN_ONLY = "fan_only"


class ClimateEntityFeature(IntFlag):
    TARGET_TEMPERATURE = 1
    FAN_MODE = 8
    SWING_MODE = 32
    TURN_OFF = 128
    TURN_ON = 256


class HomeAssistantError(Exception):
    pass


class ServiceValidationError(HomeAssistantError):
    pass


def settings(entity):
    return (
        entity.hvac_mode, entity.target_temperature, entity.fan_mode,
        entity.swing_mode, entity.last_on_operation, entity._on_by_remote,
    )


class ClimateEntity:
    async def async_added_to_hass(self):
        pass

    def async_write_ha_state(self):
        self.hass.writes.append(settings(self))


class RestoreEntity:
    async def async_get_last_state(self):
        return self.hass.last_state


def track_state_change(hass, entity_id, listener):
    hass.listeners[entity_id] = listener


def load_source():
    """Import complete modules, not copied or extracted implementations."""
    modules = {}

    def module(name, **attributes):
        result = ModuleType(name)
        result.__dict__.update(attributes)
        modules[name] = result
        return result

    for name in ("homeassistant", "homeassistant.components", "homeassistant.helpers"):
        module(name, __path__=[])
    module("homeassistant.components.climate", ClimateEntity=ClimateEntity,
           PLATFORM_SCHEMA=vol.Schema({}))
    module("homeassistant.components.climate.const",
           ClimateEntityFeature=ClimateEntityFeature, HVACMode=HVACMode,
           HVAC_MODES=list(HVACMode), ATTR_HVAC_MODE="hvac_mode")
    module("homeassistant.const", CONF_NAME="name", STATE_ON="on", STATE_OFF="off",
           STATE_UNKNOWN="unknown", STATE_UNAVAILABLE="unavailable",
           ATTR_TEMPERATURE="temperature", ATTR_ENTITY_ID="entity_id",
           PRECISION_TENTHS=0.1, PRECISION_HALVES=0.5, PRECISION_WHOLE=1)
    module("homeassistant.core", Event=dict, EventStateChangedData=dict,
           callback=lambda function: function)
    module("homeassistant.exceptions", HomeAssistantError=HomeAssistantError,
           ServiceValidationError=ServiceValidationError)
    module("homeassistant.helpers.event", async_track_state_change=track_state_change,
           async_track_state_change_event=track_state_change)
    module("homeassistant.helpers.restore_state", RestoreEntity=RestoreEntity)
    module("homeassistant.helpers.config_validation", string=str, positive_int=int,
           positive_float=float, entity_id=str, boolean=bool)

    source = Path(__file__).resolve().parents[1] / "custom_components" / "smartir"
    # Execute the actual conversion helpers without running integration startup.
    tree = ast.parse((source / "__init__.py").read_text(encoding="utf-8"))
    helper = next(node for node in tree.body
                  if isinstance(node, ast.ClassDef) and node.name == "Helper")
    namespace = {"binascii": binascii, "struct": struct}
    exec(compile(ast.Module(body=[helper], type_ignores=[]),
                 str(source / "__init__.py"), "exec"), namespace)
    # Bypass integration startup/downloads, but load unmodified climate/controller.
    module("smartir_test", __path__=[str(source)], COMPONENT_ABS_DIR=str(source),
           Helper=namespace["Helper"])
    with patch.dict("sys.modules", modules):
        climate = importlib.import_module("smartir_test.climate")
        controller = importlib.import_module("smartir_test.controller")
    return climate, controller
