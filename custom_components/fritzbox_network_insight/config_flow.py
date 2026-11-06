"""Config flow for FRITZ!Box Network Insight."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .fritzbox_client import (
    FritzBoxAuthenticationError,
    FritzBoxClient,
    FritzBoxConnectionError,
)

_LOGGER = logging.getLogger(__name__)


def _validate_connection(
    host: str, username: str, password: str
) -> None:
    """Perform a real TR-064 host-list request to validate connectivity."""
    FritzBoxClient(host, username, password).get_hosts()


async def _async_validate(
    hass: HomeAssistant, data: dict[str, str]
) -> str | None:
    try:
        await hass.async_add_executor_job(
            _validate_connection,
            data[CONF_HOST],
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
        )
    except FritzBoxAuthenticationError:
        return "invalid_auth"
    except FritzBoxConnectionError:
        return "cannot_connect"
    except Exception:  # Defensive boundary for library/parser failures.
        _LOGGER.exception("Unexpected error while validating FRITZ!Box")
        return "cannot_connect"
    return None


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one FRITZ!Box connection."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            data = {
                CONF_HOST: host,
                CONF_USERNAME: user_input[CONF_USERNAME].strip(),
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            await self.async_set_unique_id(host.casefold())
            self._abort_if_unique_id_configured()

            error = await _async_validate(self.hass, data)
            if error is None:
                return self.async_create_entry(
                    title=host,
                    data=data,
                )
            errors["base"] = error

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default="fritz.box"): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
