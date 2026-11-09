"""Evidence-preserving topology projection for a future network map.

One node per MAC. Physical links, wireless attachments, and forwarding
observations are separate relations, never interchangeable.
"""
from __future__ import annotations

from typing import Any, Mapping

from .lldp_matcher import normalize_mac


def build_topology_view(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Return a stable, JSON-serializable view of the internal topology."""
    source_nodes = graph.get("nodes") or {}
    if isinstance(source_nodes, Mapping):
        iterable = source_nodes.values()
    else:
        iterable = source_nodes
    nodes: dict[str, dict[str, Any]] = {}
    for item in iterable:
        if not isinstance(item, Mapping):
            continue
        mac = normalize_mac(item.get("mac"))
        if mac:
            nodes[mac] = {
                "id": mac, "mac": mac,
                "name": str(item.get("name") or mac),
                "ip_address": str(item.get("ip_address") or ""),
                "device_type": item.get("device_type"),
                "mesh_role": item.get("mesh_role"),
            }

    def ensure(mac: str) -> None:
        nodes.setdefault(mac, {
            "id": mac, "mac": mac, "name": mac,
            "ip_address": "", "device_type": None, "mesh_role": None,
        })

    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    physical_pairs: set[frozenset[str]] = set()
    for link in graph.get("links", []):
        if not isinstance(link, Mapping):
            continue
        source = normalize_mac(link.get("source_mac"))
        target = normalize_mac(link.get("target_mac"))
        if not source or not target or source == target:
            continue
        medium = str(link.get("medium") or "").lower()
        evidence = str(link.get("evidence") or "")
        if medium == "lan" and evidence in ("lldp", "user_confirmed"):
            kind = "confirmed_lan"
            physical_pairs.add(frozenset((source, target)))
        elif medium == "wlan" and evidence == "avm_mesh":
            kind = "mesh_wlan"
        else:
            continue
        key = (*sorted((source, target)), kind)
        if key in seen:
            continue
        seen.add(key)
        ensure(source)
        ensure(target)
        details = link.get("details") or {}
        edges.append({
            "source": source, "target": target,
            "kind": kind, "evidence": evidence,
            "physical_link_confirmed": kind == "confirmed_lan",
            "port": str(details.get("source_port_id") or
                        details.get("source_interface") or
                        details.get("source_port_number") or
                        details.get("bridge_port") or ""),
        })

    # Mesh LAN is a logical observation, never an inferred direct cable.
    mesh_lan = []
    for item in graph.get("mesh_lan_observations", []):
        if not isinstance(item, Mapping):
            continue
        source = normalize_mac(item.get("source_mac"))
        target = normalize_mac(item.get("target_mac"))
        if source and target and source != target:
            ensure(source)
            ensure(target)
            mesh_lan.append({
                "source": source, "target": target,
                "kind": "mesh_lan_observation",
                "evidence": "avm_mesh",
                "physical_link_confirmed": False,
            })

    # A downstream branch is a membership, not a direct physical edge.
    branches = []
    for branch in graph.get("graph_branches", []):
        if not isinstance(branch, Mapping):
            continue
        switch = normalize_mac(branch.get("switch_mac"))
        if not switch:
            continue
        members = []
        for item in branch.get("members", []):
            if not isinstance(item, Mapping):
                continue
            mac = normalize_mac(item.get("mac"))
            if mac and mac != switch:
                ensure(mac)
                members.append({
                    "mac": mac, "evidence": "fdb_reachability",
                    "physical_link_confirmed": False,
                    "downstream_port_known": bool(item.get("downstream_port_known")),
                })
        branches.append({
            "switch_mac": switch, "parent_mac": normalize_mac(branch.get("parent_mac")),
            "members": members,
            "evidence": "fdb_reachability",
        })

    # A standalone repeater can be in the Mesh without a known uplink.
    # Preserve it as a node rather than inventing a router-to-repeater edge.
    return {
        "schema_version": 1,
        "nodes": [nodes[k] for k in sorted(nodes)],
        "edges": sorted(edges, key=lambda x: (x["source"], x["target"], x["kind"])),
        "mesh_lan_observations": mesh_lan,
        "branches": branches,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "note": "Only LLDP/user confirmation proves direct LAN; FDB proves reachability.",
    }
