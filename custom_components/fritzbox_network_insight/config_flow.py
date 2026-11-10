"""Config flow for FRITZ!Box Network Insight."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import normalize_mac
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

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return SnmpOptionsFlow()

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


class SnmpOptionsFlow(config_entries.OptionsFlow):
    """Configure one SNMPv3 device by MAC; retain other configured devices."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        hosts = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        choices = {
            mac: f"{host.get('name') or mac} ({mac})"
            for mac, host in sorted((hosts.data or {}).items())
        } if hosts is not None else {}
        if not choices:
            return self.async_abort(reason="no_devices")
        if user_input is not None and user_input.get("mac") == "__repeater_diagnostics__":
            return await self.async_step_repeater_diagnostics()
        if user_input is not None and not all(user_input.get(k) for k in ("snmp_username", "auth_password", "priv_password")):
            return self.async_show_form(step_id="init", errors={"base": "required"}, data_schema=self._init_schema(choices))
        if user_input is not None:
            mac = user_input["mac"]
            devices = dict(self.config_entry.options.get("snmp_devices", {}))
            devices[mac] = {
                "username": user_input["snmp_username"],
                "auth_password": user_input["auth_password"],
                "priv_password": user_input["priv_password"],
            }
            return self.async_create_entry(
                title="", data={**self.config_entry.options, "snmp_devices": devices}
            )
        return self.async_show_form(step_id="init", data_schema=self._init_schema(choices))

    @staticmethod
    def _init_schema(choices: dict[str, str]) -> vol.Schema:
        return vol.Schema({
            vol.Required("mac"): vol.In({**choices, "__repeater_diagnostics__": "Configure repeater WLAN diagnostics"}),
            vol.Optional("snmp_username"): str,
            vol.Optional("auth_password"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional("priv_password"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        })


    async def async_step_repeater_diagnostics(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Opt in to read-only WLAN diagnostics from one repeater."""
        if user_input is not None:
            host = user_input["host"].strip()
            if not host:
                return self.async_show_form(step_id="repeater_diagnostics", errors={"base": "invalid_host"},
                                            data_schema=self._repeater_schema())
            target_mac = normalize_mac(user_input["target_mac"])
            if target_mac is None:
                return self.async_show_form(step_id="repeater_diagnostics", errors={"base": "invalid_mac"}, data_schema=self._repeater_schema())
            config = {
                "target_mac": target_mac,
                "host": host,
                "username": user_input["username"].strip(),
                "password": user_input["password"],
            }
            return self.async_create_entry(
                title="", data={**self.config_entry.options, "repeater_wlan_diagnostics": config}
            )
        return self.async_show_form(
            step_id="repeater_diagnostics", data_schema=self._repeater_schema()
        )

    @staticmethod
    def _repeater_schema() -> vol.Schema:
        return vol.Schema({
            vol.Required("host"): str,
            vol.Required("target_mac"): str,
            vol.Required("username"): str,
            vol.Required("password"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        })
