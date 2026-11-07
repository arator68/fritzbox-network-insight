"""Versioned, MAC-keyed storage for verified device identifications.

SNMP credentials and discovery result history are never stored here.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
MAC_PATTERN = re.compile(r"^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$")
ALLOWED_FIELDS = frozenset({
    "detected_device_type", "detected_device_type_source",
    "device_type_confidence", "device_manufacturer", "device_model",
})


class IdentificationStore:
    """Persist only validated identification metadata for one config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(
            hass, STORAGE_VERSION,
            f"fritzbox_network_insight.identifications.{entry_id}",
        )

    @staticmethod
    def _sanitize(records: Any) -> dict[str, dict[str, str]]:
        if not isinstance(records, dict):
            return {}
        result: dict[str, dict[str, str]] = {}
        for mac, fields in records.items():
            if not isinstance(mac, str) or not MAC_PATTERN.fullmatch(mac):
                continue
            if not isinstance(fields, dict):
                continue
            cleaned = {
                key: value
                for key, value in fields.items()
                if key in ALLOWED_FIELDS
                and isinstance(value, str)
                and 0 < len(value) <= 256
            }
            if (
                cleaned.get("detected_device_type")
                and cleaned.get("detected_device_type_source")
                and cleaned.get("device_type_confidence")
            ):
                result[mac] = cleaned
        return result

    async def async_load(self) -> dict[str, dict[str, str]]:
        """Load safely; a damaged store must not prevent HA startup."""
        try:
            data = await self._store.async_load()
        except Exception:
            _LOGGER.exception("Could not load stored device identifications")
            return {}
        if not isinstance(data, dict):
            return {}
        return self._sanitize(data.get("devices"))

    async def async_save(self, records: dict[str, dict[str, str]]) -> None:
        """Write only whitelisted metadata, never passwords."""
        await self._store.async_save({
            "devices": self._sanitize(records),
        })
