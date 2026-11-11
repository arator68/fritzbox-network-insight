"""Internal evidence-based network topology graph.

No UI entities are created here.  LLDP and AVM Mesh describe links; FDB
describes reachability only.  Never infer an intermediate switch or cable.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from .lldp_matcher import normalize_mac
from .device_connections import resolve_device_connections


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

    # Resolve LLDP's local port number against the FDB interface label.
    # On this switch, LLDP uses a numeric port (1/8), whereas FDB exposes
    # gigabitEthernet 1/0/1 or 1/0/8. The bridge-port ID (49153/49160)
    # is NOT the LLDP port number and must never be compared directly.
    # Only use a unique interface match for the same reporting switch.
    def matches_lldp_interface(details: Mapping[str, Any], name: str) -> bool:
        port_id = str(details.get("source_port_id") or "").strip()
        port_number = str(details.get("source_port_number") or "").strip()
        if port_id and port_id == name:
            return True
        if port_number and port_number == name:
            return True
        # Match a numeric LLDP port to the terminal physical interface
        # component, e.g. "8" to "gigabitEthernet 1/0/8".
        if port_number.isdecimal() and "/" in name:
            return name.rsplit("/", 1)[-1] == port_number
        return False

    # Enrich learned MACs with existing identities and independent WLAN evidence.
    # Never convert a forwarding-table observation into a direct cable.
    for group in fdb_port_groups:
        source = group["switch_mac"]
        interface_names = set(group["interface_names"])
        neighbors = set()
        for link in links:
            if link["evidence"] != "lldp" or link["source_mac"] != source:
                continue
            candidate_groups = [
                candidate for candidate in fdb_port_groups
                if candidate["switch_mac"] == source
                and any(
                    matches_lldp_interface(link["details"], name)
                    for name in candidate["interface_names"]
                )
            ]
            if len(candidate_groups) == 1 and candidate_groups[0] is group:
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

        # Port-level evidence summary. Multiple learned MAC addresses mean
        # reachability through this port, NOT proof of a downstream switch.
        confirmed = [d["mac"] for d in devices if d["lldp_direct_neighbor"]]
        wireless = [d["mac"] for d in devices
                    if d["connection_class"] == "wlan_reachable_via_port"]
        fdb_only = [d["mac"] for d in devices
                    if d["connection_class"] == "fdb_reachable_only"]
        # A recognizable device name is an identity hint, not physical
        # evidence. Keep candidates separate from confirmed LLDP neighbors.
        # Restrict to known hosts with a switch-like name; unknown MACs and
        # generic device names must not become invented switches.
        switch_candidates = [
            {"mac": d["mac"], "name": d["name"],
             "evidence": "known_host_name", "direct_link_confirmed": False}
            for d in devices
            if d["known_host"]
            and d["mac"] not in confirmed
            and frozenset((source, d["mac"])) not in confirmed_pairs
            and d["connection_class"] == "fdb_reachable_only"
            and any(token in d["name"].lower()
                    for token in ("switch", "tl-sg", "dgs-", "netgear gs"))
        ]
        group["port_analysis"] = {
            "classification": (
                "lldp_confirmed_neighbor" if confirmed
                else "fdb_reachability_only"
            ),
            "confirmed_neighbor_macs": confirmed,
            "downstream_switch_candidates": switch_candidates,
            "wlan_reachable_count": len(wireless),
            "fdb_only_count": len(fdb_only),
            "reachable_mac_count": len(devices),
            "multiple_macs_observed": len(devices) > 1,
            "downstream_switch_confirmed": False,
            "direct_device_without_lldp_confirmed": False,
        }

    # Uniform, evidence-preserving LAN inventory for every observed port.
    # These are port observations, not automatically inferred cables.
    lan_port_memberships: list[dict[str, Any]] = []
    for group in fdb_port_groups:
        lldp_macs = {neighbor["mac"] for neighbor in group["lldp_neighbors"]}
        members: list[dict[str, Any]] = []
        for device in group["devices"]:
            mac = device["mac"]
            if mac in lldp_macs:
                relation, evidence, confirmed = "confirmed_neighbor", "lldp", True
            elif device["connection_class"] == "wlan_reachable_via_port":
                relation, evidence, confirmed = "wlan_transit", "avm_mesh", False
            else:
                relation, evidence, confirmed = "reachable_via_port", "fdb_reachability", False
            members.append({
                "mac": mac,
                "name": device["name"],
                "ip_address": device["ip_address"],
                "relationship": relation,
                "evidence": evidence,
                "physical_link_confirmed": confirmed,
                "wlan_parent_mac": device["wlan_parent_mac"],
            })
        lan_port_memberships.append({
            "switch_mac": group["switch_mac"],
            "bridge_port": group["bridge_port"],
            "vlan_id": group["vlan_id"],
            "interface_names": list(group["interface_names"]),
            "members": members,
            "member_count": len(members),
            "confirmed_neighbor_count": sum(
                m["physical_link_confirmed"] for m in members
            ),
            "wlan_transit_count": sum(
                m["relationship"] == "wlan_transit" for m in members
            ),
            "fdb_only_count": sum(
                m["relationship"] == "reachable_via_port" for m in members
            ),
        })

    # Suggest only unambiguous, single-MAC, non-WLAN FDB observations for
    # operator verification. A suggestion never creates a physical link.
    physical_link_candidates: list[dict[str, Any]] = []
    for group in fdb_port_groups:
        if len(group["devices"]) != 1:
            continue
        device = group["devices"][0]
        if device["connection_class"] != "fdb_reachable_only":
            continue
        if group["lldp_neighbors"]:
            continue
        if not device["known_host"]:
            continue
        physical_link_candidates.append({
            "source_mac": group["switch_mac"],
            "target_mac": device["mac"],
            "target_name": device["name"],
            "target_ip_address": device["ip_address"],
            "bridge_port": group["bridge_port"],
            "vlan_id": group["vlan_id"],
            "interface_names": list(group["interface_names"]),
            "evidence": "fdb_reachability",
            "status": "requires_user_confirmation",
            "physical_link_confirmed": False,
            "reason": "single_known_lan_mac_on_port",
        })

    # History is independent of the latest FDB snapshot and never claims online status.
    port_history: list[dict[str, Any]] = []
    observed_keys = {
        (group["switch_mac"], device["mac"], group["vlan_id"])
        for group in fdb_port_groups for device in group["devices"]
    }
    for record in snapshot.get("port_history", []):
        if not isinstance(record, dict):
            continue
        source = normalize_mac(record.get("source_mac"))
        target = normalize_mac(record.get("target_mac"))
        if not source or not target or source == target:
            continue
        pair = frozenset((source, target))
        matching = [
            link for link in links
            if link["medium"] == "lan"
            and link["evidence"] == "lldp"
            and frozenset((link["source_mac"], link["target_mac"])) == pair
            and link.get("state") != "needs_review"
        ]
        port_history.append({
            "source_mac": source,
            "target_mac": target,
            "target_name": str(nodes.get(target, {}).get("name") or ""),
            "bridge_port": str(record.get("bridge_port") or ""),
            "vlan_id": str(record.get("vlan_id") or ""),
            "interface_name": str(record.get("interface_name") or ""),
            "last_seen": str(record.get("last_seen") or ""),
            "last_observation_evidence": str(record.get("evidence") or ""),
            "present_in_saved_fdb_snapshot": (
                source, target, str(record.get("vlan_id") or "")
            ) in observed_keys,
            "online_confirmed": False,
            "physical_link_confirmed": bool(matching),
            "physical_evidence": matching[0]["evidence"] if matching else None,
            "status": "last_observed",
        })

    # Represent each observed switch/bridge/VLAN port as a segment.
    # Membership is forwarding reachability, not a physical wiring claim.
    # Keep LLDP-proven neighbors distinct from identity-based candidates.
    network_segments = []
    for group in fdb_port_groups:
        analysis = group["port_analysis"]
        network_segments.append({
            "segment_id": (
                f'{group["switch_mac"]}:{group["bridge_port"]}:{group["vlan_id"]}'
            ),
            "reporting_switch_mac": group["switch_mac"],
            "bridge_port": group["bridge_port"],
            "vlan_id": group["vlan_id"],
            "interface_names": list(group["interface_names"]),
            "evidence": "fdb_reachability",
            "physical_topology_confirmed": False,
            "lldp_confirmed_neighbors": list(group["lldp_neighbors"]),
            "downstream_switch_candidates": list(
                analysis["downstream_switch_candidates"]
            ),
            "reachable_devices": list(group["devices"]),
            "reachable_mac_count": analysis["reachable_mac_count"],
        })

    graph = {
        "nodes": nodes,
        "links": links,
        "reachability": reachability,
        "fdb_port_groups": fdb_port_groups,
        "network_segments": network_segments,
        "downstream_branches": [],
        "graph_branches": [],
        "graph_branch_count": 0,
        "lan_port_memberships": lan_port_memberships,
        "lan_port_membership_count": len(lan_port_memberships),
        "physical_link_candidates": physical_link_candidates,
        "physical_link_candidate_count": len(physical_link_candidates),
        "port_history": port_history,
        "port_history_count": len(port_history),
        "downstream_branch_count": 0,
        "mesh_lan_observations": mesh_lan_observations,
        "wlan_attachments": attachments,
        "conflicts": conflicts,
        "node_count": len(nodes),
        "link_count": len(links),
        "wlan_attachment_count": len(attachments),
        "reachability_count": len(reachability),
        "fdb_port_group_count": len(fdb_port_groups),
        "network_segment_count": len(network_segments),
        "mesh_lan_observation_count": len(mesh_lan_observations),
        "conflict_count": len(conflicts),
        "model_version": 12,
    }
    graph["device_connections"] = resolve_device_connections(graph)
    graph["device_connection_count"] = len(graph["device_connections"])
    return graph
