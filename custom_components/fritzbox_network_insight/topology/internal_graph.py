"""Internal evidence-based network topology graph.

No UI entities are created here.  LLDP and AVM Mesh describe links; FDB
describes reachability only.  Never infer an intermediate switch or cable.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from .lldp_matcher import normalize_mac


def build_internal_graph(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Build a deterministic graph from the complete combined topology snapshot."""
    nodes = {
        mac: dict(node)
        for node in snapshot.get("nodes", [])
        if isinstance(node, dict)
        if (mac := normalize_mac(node.get("mac")))
    }
    links: list[dict[str, Any]] = []
    reachability: list[dict[str, Any]] = []
    mesh_lan_observations: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    confirmed_pairs: set[frozenset[str]] = set()
    wireless_attachments: dict[str, set[str]] = defaultdict(set)

    def add_link(source: str, target: str, *, medium: str,
                 evidence: str, state: str | None,
                 details: Mapping[str, Any]) -> None:
        pair = frozenset((source, target))
        key = (tuple(sorted(pair)), medium, evidence,
               str(details.get("source_interface_uid") or details.get("source_port_number") or ""),
               str(details.get("target_interface_uid") or ""))
        if key in seen:
            return
        seen.add(key)
        links.append({
            "source_mac": source,
            "target_mac": target,
            "medium": medium,
            "evidence": evidence,
            "state": state,
            "details": dict(details),
        })

    # LLDP-confirmed direct physical links take precedence for LAN topology.
    for item in snapshot.get("direct_links", []):
        if not isinstance(item, dict):
            continue
        source = normalize_mac(item.get("source_mac"))
        target = normalize_mac(item.get("target_mac"))
        if not source or not target or source == target:
            continue
        confirmed_pairs.add(frozenset((source, target)))
        add_link(source, target, medium="lan", evidence="lldp",
                 state=None, details=item)

    for item in snapshot.get("mesh_links", []):
        if not isinstance(item, dict):
            continue
        source = normalize_mac(item.get("source_mac"))
        target = normalize_mac(item.get("target_mac"))
        if not source or not target or source == target:
            continue
        medium = str(item.get("link_type") or "").strip().lower()
        if medium not in ("lan", "wlan"):
            conflicts.append({"reason": "unknown_mesh_medium", "link": dict(item)})
            continue
        state = str(item.get("link_state") or "").upper()
        if state and state != "CONNECTED":
            # Keep historical/disconnected evidence outside the active graph.
            continue
        if medium == "lan" and frozenset((source, target)) in confirmed_pairs:
            # LLDP already proves this pair; retain the mesh evidence on the
            # matching edge rather than creating a second physical cable.
            for link in links:
                if link["medium"] == "lan" and frozenset((
                    link["source_mac"], link["target_mac"]
                )) == frozenset((source, target)):
                    link.setdefault("corroboration", []).append(dict(item))
            continue
        if medium == "lan":
            # AVM reports logical LAN reachability through downstream switches.
            # Without LLDP this is NOT a confirmed direct physical cable.
            mesh_lan_observations.append(dict(item))
            continue
        add_link(source, target, medium=medium, evidence="avm_mesh",
                 state=state or None, details=item)
        if medium == "wlan":
            source_role = str(item.get("source_mesh_role") or "").lower()
            target_role = str(item.get("target_mesh_role") or "").lower()
            # AVM node-link direction is used only when one endpoint is a
            # known master/slave and the other is a non-mesh client.
            if source_role in ("master", "slave") and target_role not in ("master", "slave"):
                wireless_attachments[target].add(source)
            elif target_role in ("master", "slave") and source_role not in ("master", "slave"):
                wireless_attachments[source].add(target)

    # FDB entries describe forwarding reachability, not a direct connection.
    for item in snapshot.get("reachable_via_port", []):
        if not isinstance(item, dict):
            continue
        source = normalize_mac(item.get("source_mac"))
        target = normalize_mac(item.get("target_mac"))
        if source and target and source != target:
            reachability.append(dict(item))

    # FDB is forwarding reachability per switch/bridge port, not a cable.
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for observation in reachability:
        switch = normalize_mac(observation.get("source_mac"))
        target = normalize_mac(observation.get("target_mac"))
        port = str(observation.get("bridge_port") or "")
        vlan = str(observation.get("vlan_id") or "")
        if not switch or not target or not port:
            continue
        key = (switch, port, vlan)
        group = groups.setdefault(key, {
            "switch_mac": switch, "bridge_port": port, "vlan_id": vlan,
            "interface_names": set(), "reachable_macs": set(),
        })
        group["reachable_macs"].add(target)
        if observation.get("interface_name"):
            group["interface_names"].add(str(observation["interface_name"]))
    fdb_port_groups = [
        {"switch_mac": g["switch_mac"], "bridge_port": g["bridge_port"],
         "vlan_id": g["vlan_id"], "interface_names": sorted(g["interface_names"]),
         "reachable_macs": sorted(g["reachable_macs"]),
         "direct_connection_inferred": False}
        for _, g in sorted(groups.items())
    ]

    attachments: dict[str, dict[str, Any]] = {}
    for client, parents in sorted(wireless_attachments.items()):
        if len(parents) == 1:
            attachments[client] = {
                "parent_mac": next(iter(parents)),
                "evidence": "avm_mesh",
                "medium": "wlan",
            }
        else:
            conflicts.append({
                "reason": "multiple_wlan_parents",
                "client_mac": client,
                "candidate_parent_macs": sorted(parents),
            })

    # Enrich learned MACs with existing identities and independent WLAN evidence.
    # Never convert a forwarding-table observation into a direct cable.
    for group in fdb_port_groups:
        source = group["switch_mac"]
        interface_names = set(group["interface_names"])
        neighbors = set()
        for link in links:
            if link["evidence"] != "lldp" or link["source_mac"] != source:
                continue
            local_port = str(link["details"].get("source_port_number") or "")
            if local_port and local_port in interface_names:
                neighbors.add(link["target_mac"])
        group["lldp_neighbors"] = [
            {"mac": mac, "name": str(nodes.get(mac, {}).get("name") or "")}
            for mac in sorted(neighbors)
        ]
        devices = []
        for mac in group["reachable_macs"]:
            node = nodes.get(mac, {})
            wireless = attachments.get(mac)
            devices.append({
                "mac": mac,
                "name": str(node.get("name") or ""),
                "ip_address": str(node.get("ip_address") or ""),
                "device_type": node.get("device_type"),
                "known_host": bool(node.get("known_host")),
                "wlan_parent_mac": wireless["parent_mac"] if wireless else None,
                "wlan_parent_name": str(nodes.get(wireless["parent_mac"], {}).get("name") or "") if wireless else "",
                "wlan_evidence": wireless["evidence"] if wireless else None,
                "lldp_direct_neighbor": mac in neighbors,
                "connection_class": (
                    "lldp_confirmed_lan" if mac in neighbors
                    else "wlan_reachable_via_port" if wireless
                    else "fdb_reachable_only"
                ),
            })
        group["devices"] = devices

    return {
        "nodes": nodes,
        "links": links,
        "reachability": reachability,
        "fdb_port_groups": fdb_port_groups,
        "mesh_lan_observations": mesh_lan_observations,
        "wlan_attachments": attachments,
        "conflicts": conflicts,
        "node_count": len(nodes),
        "link_count": len(links),
        "wlan_attachment_count": len(attachments),
        "reachability_count": len(reachability),
        "fdb_port_group_count": len(fdb_port_groups),
        "mesh_lan_observation_count": len(mesh_lan_observations),
        "conflict_count": len(conflicts),
        "model_version": 4,
    }
