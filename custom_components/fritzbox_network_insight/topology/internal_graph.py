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

    return {
        "nodes": nodes,
        "links": links,
        "reachability": reachability,
        "wlan_attachments": attachments,
        "conflicts": conflicts,
        "node_count": len(nodes),
        "link_count": len(links),
        "wlan_attachment_count": len(attachments),
        "reachability_count": len(reachability),
        "conflict_count": len(conflicts),
        "model_version": 1,
    }
