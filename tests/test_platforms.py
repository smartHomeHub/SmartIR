"""Smoke tests that every SmartIR platform still creates its entities.

Each test drives the platform's ``async_setup_platform`` the same way Home
Assistant does for a YAML entry::

    fan:
      - platform: smartir
        name: Bedroom fan
        unique_id: bedroom_fan
        device_code: 1000
        controller_data: remote.bedroom_remote
"""
import asyncio
from unittest.mock import MagicMock

import pytest

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.fan import FanEntity
from homeassistant.components.light import LightEntity
from homeassistant.components.media_player import MediaPlayerEntity

PLATFORMS = {
    "climate": (ClimateEntity, "Lounge AC"),
    "fan": (FanEntity, "Bedroom fan"),
    "light": (LightEntity, "Bedroom light"),
    "media_player": (MediaPlayerEntity, "Living room TV"),
}


def _config(name):
    return {
        "name": name,
        "unique_id": name.lower().replace(" ", "_"),
        "device_code": 1000,
        "controller_data": "remote.lounge_ac_remote",
        "delay": 0.5,
        "power_sensor": None,
        "temperature_sensor": None,
        "humidity_sensor": None,
        "power_sensor_restore_state": False,
        "device_class": "tv",
        "source_names": {"HDMI1": "HDMI 1", "HDMI2": "HDMI 2"},
    }


@pytest.mark.parametrize("platform", sorted(PLATFORMS))
def test_platform_creates_entity(platform):
    module = pytest.importorskip("custom_components.smartir.%s" % platform)
    entity_class, name = PLATFORMS[platform]

    hass = MagicMock()
    hass.config.units.temperature_unit = "°C"
    hass.states.get.return_value = None

    added = []
    asyncio.run(module.async_setup_platform(hass, _config(name), added.extend))

    assert len(added) == 1, "%s platform did not add an entity" % platform
    entity = added[0]
    assert isinstance(entity, entity_class)
    assert entity.name == name
    assert entity.unique_id == name.lower().replace(" ", "_")
