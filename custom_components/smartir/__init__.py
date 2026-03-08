from __future__ import annotations

import logging

from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up SmartIR component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up SmartIR from a config entry."""

    platform = entry.data.get("platform")

    if platform not in PLATFORMS:
        _LOGGER.error("Unsupported SmartIR platform: %s", platform)
        return False

    await hass.config_entries.async_forward_entry_setups(entry, [platform])

    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload SmartIR config entry."""

    platform = entry.data.get("platform")

    return await hass.config_entries.async_unload_platforms(entry, [platform])