"""Extensible, passive-first device discovery coordination.

Protocol probes are opt-in adapters. Merely discovering an IP address never
authorizes scanning it or assuming it supports SNMP, SSDP or mDNS.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class DiscoveryEvidence:
    """One explicitly sourced claim about a network device."""

    source: str
    device_type: str | None = None
    model: str | None = None
    protocol: str | None = None


class DiscoveryAdapter(Protocol):
    """Interface for future optional protocol-specific discovery adapters."""

    @property
    def name(self) -> str:
        """Return a stable protocol adapter name."""

    async def async_discover(
        self, host: Mapping[str, Any]
    ) -> DiscoveryEvidence | None:
        """Return evidence or None; never infer support from lack of response."""


class DiscoveryManager:
    """Combine trusted evidence without network probes by default."""

    def __init__(
        self, adapters: Iterable[DiscoveryAdapter] = (), *, active_enabled: bool = False
    ) -> None:
        self._adapters = tuple(adapters)
        self._active_enabled = active_enabled

    async def async_enrich(self, host: dict[str, Any]) -> dict[str, Any]:
        """Enrich a copy of a host record with explicit protocol evidence."""
        enriched = dict(host)
        # A FRITZ!Box Ethernet/WLAN interface is not evidence of device type.
        # Vendor OUI alone is also not sufficient for classification.
        if not self._active_enabled:
            return enriched

        for adapter in self._adapters:
            try:
                evidence = await adapter.async_discover(enriched)
            except Exception:
                # Optional discovery must not break primary host collection.
                continue
            if evidence is None:
                continue
            if evidence.device_type and not enriched.get("detected_device_type"):
                enriched["detected_device_type"] = evidence.device_type
                enriched["detected_device_type_source"] = evidence.source
            if evidence.model and not enriched.get("detected_model"):
                enriched["detected_model"] = evidence.model
                enriched["detected_model_source"] = evidence.source
        return enriched
