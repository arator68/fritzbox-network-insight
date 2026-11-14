"""Optional read-only TR-064 router monitoring.

Only publish values actually returned by the configured FRITZ!Box.
No topology, host classification, or device connections are modified.
"""
from __future__ import annotations

from ipaddress import ip_address
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .router_device import router_mac

# key -> (TR-064 service, action, response key, conversion, unit)
FIELDS = {
    "download_rate": ("WANCommonInterfaceConfig", "GetAddonInfos", "NewByteReceiveRate", "rate", "B/s"),
    "upload_rate": ("WANCommonInterfaceConfig", "GetAddonInfos", "NewByteSendRate", "rate", "B/s"),
    "bytes_received": ("WANCommonInterfaceConfig", "GetTotalBytesReceived", "NewTotalBytesReceived", "counter", "B"),
    "bytes_sent": ("WANCommonInterfaceConfig", "GetTotalBytesSent", "NewTotalBytesSent", "counter", "B"),
    "max_download_rate": ("WANCommonInterfaceConfig", "GetCommonLinkProperties", "NewLayer1DownstreamMaxBitRate", "counter", "bit/s"),
    "max_upload_rate": ("WANCommonInterfaceConfig", "GetCommonLinkProperties", "NewLayer1UpstreamMaxBitRate", "counter", "bit/s"),
    "external_ipv4": ("WANIPConnection", "GetExternalIPAddress", "NewExternalIPAddress", "ipv4", None),
    "uptime": ("WANIPConnection", "GetStatusInfo", "NewUptime", "counter", "s"),
    "fritz_os": ("DeviceInfo", "GetInfo", "NewSoftwareVersion", "text", None),
}

def _valid(value: Any, kind: str) -> Any | None:
    if value is None or isinstance(value, bool):
        return None
    if kind in ("counter", "rate"):
        try:
            number = int(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if number >= 0 else None
    if kind == "ipv4":
        try:
            address = ip_address(str(value).strip())
            return str(address) if address.version == 4 and not address.is_unspecified else None
        except ValueError:
            return None
    value = str(value).strip()
    return value or None

def read_router_metrics(connection: Any) -> dict[str, Any]:
    """Query supported actions individually; missing services never create values."""
    result: dict[str, Any] = {}
    responses: dict[tuple[str, str], dict[str, Any] | None] = {}
    for key, (service, action, field, kind, _unit) in FIELDS.items():
        pair = (service, action)
        if pair not in responses:
            try:
                response = connection.call_action(service, action)
                responses[pair] = response if isinstance(response, dict) else None
            except Exception:
                responses[pair] = None
        response = responses[pair]
        if response is not None:
            parsed = _valid(response.get(field), kind)
            if parsed is not None:
                result[key] = parsed
    # WAN PPP is an alternative, never a second source of duplicate sensors.
    if "external_ipv4" not in result or "uptime" not in result:
        for key, action, field, kind in (
            ("external_ipv4", "GetExternalIPAddress", "NewExternalIPAddress", "ipv4"),
            ("uptime", "GetStatusInfo", "NewUptime", "counter"),
        ):
            if key in result:
                continue
            try:
                response = connection.call_action("WANPPPConnection", action)
                parsed = _valid(response.get(field), kind) if isinstance(response, dict) else None
                if parsed is not None:
                    result[key] = parsed
            except Exception:
                pass
    return result

class FritzBoxRouterMetricSensor(CoordinatorEntity, SensorEntity):
    """One observed metric of the configured router, identified by MAC."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Any, entry: Any, mac: str, metric: str) -> None:
        super().__init__(coordinator)
        self._metric = metric
        self._mac = mac
        compact = mac.replace(":", "").lower()
        self._attr_unique_id = f"host_{compact}_router_{metric}"
        self.entity_id = f"sensor.{DOMAIN}_{compact}_{metric}"
        self._attr_translation_key = f"router_{metric}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)}, connections={("mac", mac)},
        )
        unit = FIELDS[metric][4]
        if unit:
            self._attr_native_unit_of_measurement = unit
        if metric in ("bytes_received", "bytes_sent"):
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            # Keep raw TR-064 byte counters and statistics intact. Ask Home
            # Assistant to display them in decimal GB instead of long B values.
            self._attr_suggested_unit_of_measurement = "GB"
            self._attr_suggested_display_precision = 2
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif metric in ("download_rate", "upload_rate"):
            self._attr_device_class = SensorDeviceClass.DATA_RATE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif metric in ("max_download_rate", "max_upload_rate"):
            self._attr_device_class = SensorDeviceClass.DATA_RATE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif metric == "uptime":
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self) -> bool:
        return super().available and self._metric in getattr(self.coordinator.client, "router_metrics", {})

    @property
    def native_value(self) -> Any:
        return getattr(self.coordinator.client, "router_metrics", {}).get(self._metric)
