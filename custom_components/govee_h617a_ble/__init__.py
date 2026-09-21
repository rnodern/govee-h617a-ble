"""Govee H617A BLE integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import service
import voluptuous as vol

from .const import CONF_ADDRESS, DOMAIN, PLATFORMS
from .controller import GoveeH617AController

type GoveeH617AConfigEntry = ConfigEntry[GoveeH617AController]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the entity action once, including when no strip is loaded."""
    service.async_register_platform_entity_service(
        hass, DOMAIN, "apply_diy", entity_domain="light",
        schema={
            vol.Required("animation"): str,
            vol.Required("speed"): int,
            vol.Required("background_brightness"): int,
            vol.Required("background_rgb"): vol.Any(None, list),
            vol.Required("groups"): list,
        },
        func="async_apply_diy",
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GoveeH617AConfigEntry) -> bool:
    """Set up an H617A from a config entry."""
    entry.runtime_data = GoveeH617AController(hass, entry.data[CONF_ADDRESS])
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GoveeH617AConfigEntry) -> bool:
    """Unload an H617A config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
