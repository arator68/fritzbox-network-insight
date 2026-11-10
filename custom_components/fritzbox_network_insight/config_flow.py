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
from .wlan_details import fetch_wlan_devices
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
    """Separate management screens for repeater and SNMP settings."""

    def _label(self, de, en):
        return de if self.hass.config.language.lower().startswith("de") else en

    def _repeater_name(self, address):
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if coordinator is not None:
            for device in (coordinator.data or {}).values():
                if address in (device.get("ip"), device.get("ip_address"), device.get("ipv4_address")):
                    return device.get("name") or device.get("hostname") or address
        return address

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return await getattr(self, "async_step_" + user_input["section"])()
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("section"): vol.In({
                    "repeaters": self._label("Repeater verwalten", "Manage repeaters"),
                    "snmp": self._label("SNMP-Geräte verwalten", "Manage SNMP devices"),
                    "fritzbox": self._label("FRITZ!Box-Verbindung", "FRITZ!Box connection"),
                }),
            }),
        )

    async def async_step_fritzbox(self, user_input=None):
        """Existing FRITZ!Box credentials remain managed per integration entry."""
        if user_input is not None:
            return await self.async_step_init()
        return self.async_show_form(
            step_id="fritzbox",
            data_schema=vol.Schema({vol.Required("back", default=True): bool}),
        )

    def _repeater_configs(self):
        """Read new options or migrate the existing single-repeater configuration."""
        configs = dict(self.config_entry.options.get("repeaters", {}))
        old = self.config_entry.options.get("repeater_wlan_diagnostics", {})
        if isinstance(old, dict) and old.get("host") and old["host"] not in configs:
            configs[old["host"]] = {
                "host": old["host"],
                "username": old.get("username", "dslf-config"),
                "password": old.get("password", ""),
                "enabled": True,
            }
        return configs

    def _discovered_repeaters(self):
        """Offer plausible Mesh repeaters without automatically trusting credentials.

        Mesh slaves may also be FRITZ!Boxes, so never enroll every slave.
        """
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        candidates = {}
        if coordinator is None:
            return candidates
        for device in (coordinator.data or {}).values():
            name = str(device.get("name") or device.get("hostname") or "")
            kind = str(device.get("device_type") or "").lower()
            role = str(device.get("mesh_role") or "").lower()
            address = device.get("ip_address") or device.get("ipv4_address") or device.get("ip")
            if not address:
                continue
            if kind in ("repeater", "wifi_repeater", "wlan_repeater") or (
                role == "slave" and "repeater" in name.lower()
            ):
                candidates[address] = name or address
        return candidates

    async def async_step_repeater_discovery(self, user_input=None):
        configured = self._repeater_configs()
        candidates = {
            address: name for address, name in self._discovered_repeaters().items()
            if address not in configured
        }
        if not candidates:
            return self.async_show_form(
                step_id="repeater_discovery",
                data_schema=vol.Schema({vol.Required("back", default=True): bool}),
                errors={"base": "no_repeaters_found"},
            )
        if user_input is not None:
            self._editing_repeater_host = None
            self._discovered_repeater_address = user_input["host"]
            return await self.async_step_repeater_edit()
        return self.async_show_form(
            step_id="repeater_discovery",
            data_schema=vol.Schema({
                vol.Required("host"): vol.In({
                    address: f"{name} ({address})" for address, name in sorted(candidates.items())
                }),
            }),
        )

    async def async_step_repeaters(self, user_input=None):
        configs = self._repeater_configs()
        if user_input is not None:
            action = user_input["action"]
            if action == "__discover__":
                return await self.async_step_repeater_discovery()
            if action == "__add__":
                self._editing_repeater_host = None
                return await self.async_step_repeater_edit()
            if action == "__back__":
                return await self.async_step_init()
            if action.startswith("edit:"):
                return await self.async_step_repeater_edit(host=action[5:])
            if action.startswith("test:"):
                return await self.async_step_repeater_test(host=action[5:])
            if action.startswith("toggle:"):
                host = action[7:]
                configs[host] = {**configs[host], "enabled": not configs[host].get("enabled", True)}
            elif action.startswith("remove:"):
                configs.pop(action[7:], None)
            return self.async_create_entry(
                title="", data={
                    **self.config_entry.options,
                    "repeaters": configs,
                    "repeater_wlan_diagnostics": {},
                },
            )
        actions = {"__discover__": self._label("Erkannte Repeater übernehmen", "Set up discovered repeaters"),
                   "__add__": self._label("Repeater hinzufügen", "Add repeater"),
                   "__back__": self._label("Zurück", "Back")}
        for host, config in sorted(configs.items()):
            enabled = config.get("enabled", True)
            state = self._label("aktiviert", "enabled") if enabled else self._label("deaktiviert", "disabled")
            name = self._repeater_name(host)
            display = f"{name} ({host})" if name != host else host
            actions[f"edit:{host}"] = f"{self._label('Bearbeiten', 'Edit')}: {display} ({state})"
            actions[f"test:{host}"] = f"{self._label('Verbindung testen', 'Test connection')}: {display}"
            actions[f"toggle:{host}"] = f"{self._label('Deaktivieren', 'Disable') if enabled else self._label('Aktivieren', 'Enable')}: {display}"
            actions[f"remove:{host}"] = f"{self._label('Entfernen', 'Remove')}: {display}"
        return self.async_show_form(
            step_id="repeaters",
            data_schema=vol.Schema({vol.Required("action"): vol.In(actions)}),
        )

    async def async_step_repeater_test(self, user_input=None, host=None):
        """Verify saved credentials by reading the repeater's WLAN client list."""
        if host is not None:
            self._testing_repeater_host = host
        host = getattr(self, "_testing_repeater_host", None)
        config = self._repeater_configs().get(host, {})
        schema = vol.Schema({vol.Required("back", default=True): bool})
        if user_input is not None:
            return await self.async_step_repeaters()
        if not all(config.get(k) for k in ("host", "username", "password")):
            return self.async_show_form(step_id="repeater_test",
                                        data_schema=schema, errors={"base": "required"})
        try:
            clients = await self.hass.async_add_executor_job(
                fetch_wlan_devices, config["host"], config["username"],
                config["password"], 10,
            )
        except Exception:
            _LOGGER.warning("Repeater connection test failed for %s", host, exc_info=True)
            return self.async_show_form(step_id="repeater_test",
                                        data_schema=schema, errors={"base": "cannot_connect"})
        return self.async_show_form(
            step_id="repeater_test", data_schema=schema,
            description_placeholders={"host": host, "count": str(len(clients))},
        )

    async def async_step_repeater_edit(self, user_input=None, host=None):
        if host is not None:
            self._editing_repeater_host = host
        host = getattr(self, "_editing_repeater_host", None)
        configs = self._repeater_configs()
        current = configs.get(host, {}) if host else {}
        if user_input is not None:
            address = user_input["host"].strip()
            username = user_input["username"].strip()
            if not address or not username:
                return self.async_show_form(
                    step_id="repeater_edit",
                    data_schema=self._repeater_schema(current, host or getattr(self, "_discovered_repeater_address", None)),
                    errors={"base": "required"},
                )
            password = user_input.get("password") or current.get("password", "")
            if not password:
                return self.async_show_form(
                    step_id="repeater_edit",
                    data_schema=self._repeater_schema(current, host),
                    errors={"base": "required"},
                )
            if host and host != address:
                configs.pop(host, None)
            self._discovered_repeater_address = None
            configs[address] = {
                "host": address,
                "username": username,
                "password": password,
                "enabled": user_input.get("enabled", True),
            }
            return self.async_create_entry(
                title="", data={
                    **self.config_entry.options,
                    "repeaters": configs,
                    "repeater_wlan_diagnostics": {},
                },
            )
        return self.async_show_form(
            step_id="repeater_edit",
            data_schema=self._repeater_schema(current, host),
        )

    @staticmethod
    def _repeater_schema(current, host):
        return vol.Schema({
            vol.Required("host", default=host or ""): str,
            vol.Required("username", default=current.get("username", "dslf-config")): str,
            vol.Optional("password"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required("enabled", default=current.get("enabled", True)): bool,
        })

    async def async_step_snmp(self, user_input=None):
        """Keep the existing SNMP configuration independent of repeaters."""
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        hosts = (coordinator.data or {}) if coordinator is not None else {}
        choices = {
            mac: f"{host.get('name') or mac} ({mac})"
            for mac, host in sorted(hosts.items())
        }
        if not choices:
            return self.async_abort(reason="no_devices")
        if user_input is not None:
            if not all(user_input.get(k) for k in ("snmp_username", "auth_password", "priv_password")):
                return self.async_show_form(
                    step_id="snmp", data_schema=self._snmp_schema(choices),
                    errors={"base": "required"},
                )
            devices = dict(self.config_entry.options.get("snmp_devices", {}))
            devices[user_input["mac"]] = {
                "username": user_input["snmp_username"],
                "auth_password": user_input["auth_password"],
                "priv_password": user_input["priv_password"],
            }
            return self.async_create_entry(
                title="", data={**self.config_entry.options, "snmp_devices": devices},
            )
        return self.async_show_form(step_id="snmp", data_schema=self._snmp_schema(choices))

    @staticmethod
    def _snmp_schema(choices):
        password = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        )
        return vol.Schema({
            vol.Required("mac"): vol.In(choices),
            vol.Required("snmp_username"): str,
            vol.Required("auth_password"): password,
            vol.Required("priv_password"): password,
        })
