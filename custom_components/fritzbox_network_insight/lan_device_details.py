"""Join existing FDB reachability with observed switch IF-MIB telemetry.

This enriches device details only. It neither creates nor changes topology edges.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from .device import normalize_mac
from .device_details import DeviceDetails


def add_lan_port_details(
    devices: Mapping[str, DeviceDetails],
    discovery_results: Mapping[str, Mapping[str, Any]],
    fdb_observations: Mapping[str, list[Mapping[str, Any]]],
) -> None:
    """Attach port measurements only when the switch and interface match."""
    for switch_mac, discovery in discovery_results.items():
        source = normalize_mac(switch_mac)
        if source is None or discovery.get("port_telemetry_status") != "ok":
            continue
        try:
            ports = json.loads(discovery.get("port_telemetry", "[]"))
        except (TypeError, ValueError):
            continue
        if not isinstance(ports, list):
            continue
        by_index = {
            str(port["if_index"]): port
            for port in ports
            if isinstance(port, dict)
            and isinstance(port.get("if_index"), int)
            and isinstance(port.get("interface_name"), str)
        }
        for observation in fdb_observations.get(source, ()):
            if not isinstance(observation, Mapping):
                continue
            if observation.get("connection") != "reachable_via_port":
                continue
            target = normalize_mac(observation.get("target_mac"))
            if target is None or target not in devices:
                continue
            port = by_index.get(str(observation.get("if_index") or ""))
            if port is None:
                continue
            # Match the interface identity from the same FDB observation.
            name = observation.get("interface_name")
            if name and name != port["interface_name"]:
                continue
            value = {
                "switch_mac": source,
                "if_index": port["if_index"],
                "interface_name": port["interface_name"],
                "bridge_port": observation.get("bridge_port"),
                "vlan_id": observation.get("vlan_id"),
                "connection": "reachable_via_port",
                "evidence": "fdb",
            }
            for key in ("reported_speed_mbps", "speed_source", "oper_status"):
                if key in port:
                    value[key] = port[key]
            devices[target].add(
                "lan_switch_port",
                value,
                source="snmp_v3_if_mib+fdb",
                observed_at=discovery.get("last_run"),
            )
