"""Home Assistant integration for FRITZ!Box Network Insight."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import FritzBoxDataUpdateCoordinator
from .fritzbox_client import (
    FritzBoxAuthenticationError,
    FritzBoxClient,
    FritzBoxConnectionError,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the FRITZ!Box connection and its sensor platform."""
    client = FritzBoxClient(
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    coordinator = FritzBoxDataUpdateCoordinator(hass, client, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except FritzBoxAuthenticationError as err:
        raise ConfigEntryAuthFailed("FRITZ!Box authentication failed") from err
    except Exception as err:
        # DataUpdateCoordinator wraps connection errors as UpdateFailed.
        raise ConfigEntryNotReady(
            "Could not complete the initial FRITZ!Box host scan"
        ) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _LOGGER.info(
        "FRITZ!Box Network Insight initialized for %s with %d device(s)",
        entry.data[CONF_HOST],
        len(coordinator.data or {}),
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the configured integration entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_data = hass.data.get(DOMAIN)
        if domain_data is not None:
            domain_data.pop(entry.entry_id, None)
            if not domain_data:
                hass.data.pop(DOMAIN, None)
    return unload_ok
