"""Home Assistant integration for FRITZ!Box Network Insight."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import DOMAIN
from .fritzbox_client import (
    FritzBoxAuthenticationError,
    FritzBoxClient,
    FritzBoxConnectionError,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the FRITZ!Box connection and load the initial host list."""
    client = FritzBoxClient(
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    try:
        hosts = await hass.async_add_executor_job(client.get_hosts)
    except FritzBoxAuthenticationError as err:
        raise ConfigEntryAuthFailed("FRITZ!Box authentication failed") from err
    except FritzBoxConnectionError as err:
        raise ConfigEntryNotReady("Could not read the FRITZ!Box host list") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "hosts": hosts,
    }
    _LOGGER.debug("Loaded %d FRITZ!Box hosts", len(hosts))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the configured integration entry."""
    domain_data = hass.data.get(DOMAIN)
    if domain_data is not None:
        domain_data.pop(entry.entry_id, None)
        if not domain_data:
            hass.data.pop(DOMAIN, None)
    return True
