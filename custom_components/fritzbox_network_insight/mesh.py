"""Read AVM Mesh topology and retain only explicit, resolved node links.

The parser follows the node_interfaces/node_links schema already used by the
older FRITZ!Box Network Map integration. Mesh links are *reported* by AVM,
not independently verified physical links.
"""
from __future__ import annotations

import json
import logging
from urllib.parse import urljoin, urlparse
from urllib.request import (
    HTTPDigestAuthHandler, HTTPPasswordMgrWithDefaultRealm, build_opener,
)

from fritzconnection import FritzConnection

from .topology.lldp_matcher import normalize_mac

_LOGGER = logging.getLogger(__name__)


def fetch_mesh(host: str, username: str, password: str, timeout: int = 10) -> dict:
    """Blocking TR-064 mesh fetch; call only in HA's executor."""
    connection = FritzConnection(
        address=host, user=username, password=password, timeout=timeout,
    )
    result = connection.call_action("Hosts1", "X_AVM-DE_GetMeshListPath")
    path = result.get("NewX_AVM-DE_MeshListPath")
    if not isinstance(path, str) or not path:
        raise ValueError("AVM did not return a MeshListPath")
    base = f"http://{host}:49000/"
    url = urljoin(base, path)
    parsed = urlparse(url)
    # Do not send credentials to a URL outside the configured FRITZ!Box.
    if parsed.scheme not in ("http", "https") or parsed.hostname != host:
        raise ValueError("MeshListPath points outside the configured FRITZ!Box")
    manager = HTTPPasswordMgrWithDefaultRealm()
    manager.add_password(None, url, username, password)
    opener = build_opener(HTTPDigestAuthHandler(manager))
    with opener.open(url, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("nodes"), list):
        raise ValueError("Unexpected AVM mesh JSON structure")
    return payload


def parse_mesh(payload: dict, hosts: dict[str, dict]) -> dict:
    """Resolve explicit node_links by UID and match node interface MAC aliases."""
    raw_nodes = payload.get("nodes", [])
    nodes: dict[str, dict] = {}
    refs: dict[str, str] = {}
    aliases: dict[str, str] = {}
    for index, raw in enumerate(raw_nodes):
        if not isinstance(raw, dict):
            continue
        uid = str(raw.get("uid") or f"node-{index}")
        if uid in nodes:
            continue
        interfaces = [
            item for item in raw.get("node_interfaces", [])
            if isinstance(item, dict)
        ] if isinstance(raw.get("node_interfaces"), list) else []
        macs = []
        for value in [raw.get("device_mac_address")] + [
            item.get("mac_address") for item in interfaces
        ]:
            mac = normalize_mac(value)
            if mac and mac not in macs:
                macs.append(mac)
        # Prefer a host MAC on the same AVM node. Never join by hostname.
        canonical = next((mac for mac in macs if mac in hosts), None)
        if canonical is None:
            canonical = normalize_mac(raw.get("device_mac_address"))
        if canonical is None:
            continue
        nodes[uid] = {
            "uid": uid, "mac": canonical,
            "name": raw.get("name") or raw.get("device_name"),
            "mesh_role": raw.get("mesh_role"),
            "interfaces": interfaces,
        }
        refs[uid.upper()] = uid
        for mac in macs:
            aliases[mac] = canonical

    links = []
    seen = set()
    unresolved = 0
    for uid, node in nodes.items():
        for interface in node["interfaces"]:
            raw_links = interface.get("node_links", [])
            if not isinstance(raw_links, list):
                continue
            for raw_link in raw_links:
                if not isinstance(raw_link, dict):
                    continue
                first = refs.get(str(raw_link.get("node_1_uid") or "").upper())
                second = refs.get(str(raw_link.get("node_2_uid") or "").upper())
                if not first or not second:
                    unresolved += 1
                    continue
                source, target = nodes[first]["mac"], nodes[second]["mac"]
                if source == target:
                    continue
                key = tuple(sorted((source, target))) + (str(raw_link.get("uid") or ""),)
                if key in seen:
                    continue
                seen.add(key)
                links.append({
                    "source_mac": source, "target_mac": target,
                    "source_node_uid": first, "target_node_uid": second,
                    "source_mesh_role": nodes[first]["mesh_role"],
                    "target_mesh_role": nodes[second]["mesh_role"],
                    "link_type": raw_link.get("type"),
                    "link_state": raw_link.get("state"),
                    "evidence": "avm_mesh",
                    "connection": "reported_by_avm",
                })
    return {
        "nodes": [{k: v for k, v in node.items() if k != "interfaces"} for node in nodes.values()],
        "links": links, "aliases": aliases,
        "unresolved_link_count": unresolved,
    }
