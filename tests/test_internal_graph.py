"""Isolated regression tests for the internal topology engine.

Run with: python -m unittest discover -s tests -p 'test_internal_graph.py'
No Home Assistant runtime is required.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "custom_components" / "fritzbox_network_insight" / "topology"
PACKAGE = "_insight_topology_test"


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


package = types.ModuleType(PACKAGE)
package.__path__ = [str(BASE)]
sys.modules[PACKAGE] = package
_load_module(f"{PACKAGE}.lldp_matcher", "lldp_matcher.py")
graph_module = _load_module(f"{PACKAGE}.internal_graph", "internal_graph.py")
build_internal_graph = graph_module.build_internal_graph

ROUTER = "04:B4:FE:18:79:65"
SWITCH = "D4:D6:DF:0E:1B:54"
REPEATER = "66:B5:8D:22:C9:0C"
CLIENT = "68:F6:3B:6B:48:0A"
OTHER = "E0:28:6D:C0:51:38"


def snapshot():
    return {
        "nodes": [{"mac": mac} for mac in (ROUTER, SWITCH, REPEATER, CLIENT, OTHER)],
        "direct_links": [{
            "source_mac": SWITCH, "target_mac": ROUTER,
            "source_port_number": "1", "evidence": "lldp",
        }],
        "mesh_links": [
            {
                "source_mac": ROUTER, "target_mac": SWITCH,
                "link_type": "LAN", "link_state": "CONNECTED",
                "source_mesh_role": "master", "target_mesh_role": "unknown",
            },
            {
                "source_mac": ROUTER, "target_mac": REPEATER,
                "link_type": "WLAN", "link_state": "CONNECTED",
                "source_mesh_role": "master", "target_mesh_role": "slave",
            },
            {
                "source_mac": REPEATER, "target_mac": CLIENT,
                "link_type": "WLAN", "link_state": "CONNECTED",
                "source_mesh_role": "slave", "target_mesh_role": "unknown",
                "source_interface": "AP:5G:0",
            },
        ],
        "reachable_via_port": [{
            "source_mac": SWITCH, "target_mac": CLIENT,
            "interface_name": "gigabitEthernet 1/0/8",
        }],
    }


class InternalGraphTests(unittest.TestCase):
    def test_lldp_pair_deduplicates_mesh_lan(self):
        graph = build_internal_graph(snapshot())
        lan = [link for link in graph["links"] if link["medium"] == "lan"]
        self.assertEqual(len(lan), 1)
        self.assertEqual(lan[0]["evidence"], "lldp")
        self.assertEqual(len(lan[0]["corroboration"]), 1)

    def test_avm_only_lan_is_not_a_physical_link(self):
        data = snapshot()
        data["mesh_links"].append({
            "source_mac": ROUTER, "target_mac": OTHER,
            "link_type": "LAN", "link_state": "CONNECTED",
            "source_port_id": "LAN:1",
        })
        graph = build_internal_graph(data)
        lan = [link for link in graph["links"] if link["medium"] == "lan"]
        self.assertEqual(len(lan), 1)
        self.assertEqual(lan[0]["evidence"], "lldp")
        self.assertEqual(graph["mesh_lan_observation_count"], 1)
        self.assertEqual(graph["mesh_lan_observations"][0]["target_mac"], OTHER)
        self.assertEqual(graph["model_version"], 10)

    def test_disconnected_avm_lan_is_not_active_observation(self):
        data = snapshot()
        data["mesh_links"].append({
            "source_mac": ROUTER, "target_mac": OTHER,
            "link_type": "LAN", "link_state": "DISCONNECTED",
        })
        graph = build_internal_graph(data)
        self.assertEqual(graph["mesh_lan_observation_count"], 0)

    def test_fdb_grouped_by_port_without_cable_inference(self):
        data = snapshot()
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": CLIENT, "bridge_port": "8",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/8"},
            {"source_mac": SWITCH, "target_mac": OTHER, "bridge_port": "8",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/8"},
        ]
        graph = build_internal_graph(data)
        self.assertEqual(graph["model_version"], 10)
        self.assertEqual(graph["fdb_port_group_count"], 1)
        group = graph["fdb_port_groups"][0]
        self.assertEqual(group["reachable_macs"], sorted([CLIENT, OTHER]))
        self.assertFalse(group["direct_connection_inferred"])
        self.assertEqual(len([x for x in graph["links"] if x["medium"] == "lan"]), 1)

    def test_fdb_separates_switches_and_vlans(self):
        data = snapshot()
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": CLIENT, "bridge_port": "2", "vlan_id": "1"},
            {"source_mac": SWITCH, "target_mac": OTHER, "bridge_port": "2", "vlan_id": "2"},
            {"source_mac": ROUTER, "target_mac": CLIENT, "bridge_port": "2", "vlan_id": "1"},
        ]
        self.assertEqual(build_internal_graph(data)["fdb_port_group_count"], 3)

    def test_fdb_port_devices_include_known_identity_and_wlan_parent(self):
        data = snapshot()
        data["nodes"] = [
            {"mac": ROUTER, "name": "FRITZ!Box 7590 AX", "known_host": True},
            {"mac": SWITCH, "name": "TL-SG3428", "known_host": True},
            {"mac": REPEATER, "name": "Repeater", "known_host": True},
            {"mac": CLIENT, "name": "WLAN client", "ip_address": "192.168.178.25",
             "device_type": "phone", "known_host": True},
            {"mac": OTHER},
        ]
        data["direct_links"][0]["source_port_number"] = "gigabitEthernet 1/0/1"
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": ROUTER, "bridge_port": "49153",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/1"},
            {"source_mac": SWITCH, "target_mac": CLIENT, "bridge_port": "49153",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/1"},
        ]
        graph = build_internal_graph(data)
        group = graph["fdb_port_groups"][0]
        self.assertEqual(group["lldp_neighbors"][0]["mac"], ROUTER)
        devices = {d["mac"]: d for d in group["devices"]}
        self.assertEqual(devices[ROUTER]["connection_class"], "lldp_confirmed_lan")
        self.assertTrue(devices[ROUTER]["lldp_direct_neighbor"])
        self.assertEqual(devices[CLIENT]["name"], "WLAN client")
        self.assertEqual(devices[CLIENT]["ip_address"], "192.168.178.25")
        self.assertEqual(devices[CLIENT]["device_type"], "phone")
        self.assertEqual(devices[CLIENT]["wlan_parent_mac"], REPEATER)
        self.assertEqual(devices[CLIENT]["connection_class"], "wlan_reachable_via_port")
        self.assertFalse(devices[CLIENT]["lldp_direct_neighbor"])
        self.assertFalse(group["direct_connection_inferred"])

    def test_numeric_lldp_ports_match_real_switch_interface_labels(self):
        data = snapshot()
        data["direct_links"] = [
            {"source_mac": SWITCH, "target_mac": ROUTER, "source_port_number": "1"},
            {"source_mac": SWITCH, "target_mac": OTHER, "source_port_number": "8"},
        ]
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": ROUTER, "bridge_port": "49153",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/1"},
            {"source_mac": SWITCH, "target_mac": OTHER, "bridge_port": "49160",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/8"},
        ]
        groups = {g["bridge_port"]: g for g in build_internal_graph(data)["fdb_port_groups"]}
        self.assertEqual(groups["49153"]["lldp_neighbors"][0]["mac"], ROUTER)
        self.assertEqual(groups["49160"]["lldp_neighbors"][0]["mac"], OTHER)
        self.assertEqual(groups["49153"]["devices"][0]["connection_class"], "lldp_confirmed_lan")
        self.assertEqual(groups["49160"]["devices"][0]["connection_class"], "lldp_confirmed_lan")
        self.assertFalse(groups["49153"]["direct_connection_inferred"])

    def test_ambiguous_numeric_lldp_port_does_not_assign_neighbor(self):
        data = snapshot()
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": ROUTER, "bridge_port": "49153",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/1"},
            {"source_mac": SWITCH, "target_mac": CLIENT, "bridge_port": "999",
             "vlan_id": "1", "interface_name": "otherEthernet 2/0/1"},
        ]
        groups = build_internal_graph(data)["fdb_port_groups"]
        self.assertTrue(all(not g["lldp_neighbors"] for g in groups))

    def test_port_analysis_separates_confirmed_lldp_and_wireless(self):
        data = snapshot()
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": ROUTER, "bridge_port": "49153",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/1"},
            {"source_mac": SWITCH, "target_mac": CLIENT, "bridge_port": "49153",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/1"},
        ]
        group = build_internal_graph(data)["fdb_port_groups"][0]
        analysis = group["port_analysis"]
        self.assertEqual(analysis["classification"], "lldp_confirmed_neighbor")
        self.assertEqual(analysis["confirmed_neighbor_macs"], [ROUTER])
        self.assertEqual(analysis["wlan_reachable_count"], 1)
        self.assertEqual(analysis["fdb_only_count"], 0)
        self.assertEqual(analysis["reachable_mac_count"], 2)
        self.assertTrue(analysis["multiple_macs_observed"])
        self.assertFalse(analysis["downstream_switch_confirmed"])

    def test_port_analysis_does_not_infer_downstream_switch_from_fdb(self):
        data = snapshot()
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": OTHER, "bridge_port": "49154",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/2"},
            {"source_mac": SWITCH, "target_mac": ROUTER, "bridge_port": "49154",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/2"},
        ]
        group = build_internal_graph(data)["fdb_port_groups"][0]
        analysis = group["port_analysis"]
        self.assertEqual(analysis["classification"], "fdb_reachability_only")
        self.assertEqual(analysis["confirmed_neighbor_macs"], [])
        self.assertEqual(analysis["fdb_only_count"], 2)
        self.assertTrue(analysis["multiple_macs_observed"])
        self.assertFalse(analysis["downstream_switch_confirmed"])
        self.assertFalse(analysis["direct_device_without_lldp_confirmed"])
        self.assertFalse(group["direct_connection_inferred"])

    def test_known_switch_name_is_candidate_not_confirmed_cable(self):
        data = snapshot()
        data["nodes"] = [
            {"mac": SWITCH, "name": "TL-SG3428", "known_host": True},
            {"mac": OTHER, "name": "TL-SG1024DE-koch-local", "known_host": True},
            {"mac": CLIENT, "name": "Server-3", "known_host": True},
        ]
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": OTHER, "bridge_port": "49154",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/2"},
            {"source_mac": SWITCH, "target_mac": CLIENT, "bridge_port": "49154",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/2"},
        ]
        graph = build_internal_graph(data)
        analysis = graph["fdb_port_groups"][0]["port_analysis"]
        self.assertEqual(analysis["downstream_switch_candidates"], [
            {"mac": OTHER, "name": "TL-SG1024DE-koch-local",
             "evidence": "known_host_name", "direct_link_confirmed": False}
        ])
        self.assertFalse(analysis["downstream_switch_confirmed"])
        self.assertFalse(graph["fdb_port_groups"][0]["direct_connection_inferred"])

    def test_unknown_switch_like_mac_is_not_a_candidate(self):
        data = snapshot()
        data["nodes"] = [{"mac": OTHER, "name": "TL-SG1024DE",
                          "known_host": False}]
        data["reachable_via_port"] = [{
            "source_mac": SWITCH, "target_mac": OTHER,
            "bridge_port": "49154", "vlan_id": "1",
            "interface_name": "gigabitEthernet 1/0/2",
        }]
        analysis = build_internal_graph(data)["fdb_port_groups"][0]["port_analysis"]
        self.assertEqual(analysis["downstream_switch_candidates"], [])

    def test_network_segment_preserves_switch_candidate_and_membership(self):
        data = snapshot()
        data["nodes"] = [
            {"mac": SWITCH, "name": "TL-SG3428", "known_host": True},
            {"mac": OTHER, "name": "TL-SG1024DE-koch-local", "known_host": True},
            {"mac": CLIENT, "name": "Server-3", "known_host": True},
        ]
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": OTHER, "bridge_port": "49154",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/2"},
            {"source_mac": SWITCH, "target_mac": CLIENT, "bridge_port": "49154",
             "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/2"},
        ]
        graph = build_internal_graph(data)
        self.assertEqual(graph["model_version"], 10)
        self.assertEqual(graph["network_segment_count"], 1)
        segment = graph["network_segments"][0]
        self.assertEqual(segment["segment_id"], f"{SWITCH}:49154:1")
        self.assertEqual(segment["evidence"], "fdb_reachability")
        self.assertFalse(segment["physical_topology_confirmed"])
        self.assertEqual(segment["lldp_confirmed_neighbors"], [])
        self.assertEqual(segment["downstream_switch_candidates"][0]["mac"], OTHER)
        self.assertEqual({d["mac"] for d in segment["reachable_devices"]},
                         {OTHER, CLIENT})
        self.assertFalse(any(link["evidence"] == "fdb" for link in graph["links"]))

    def test_network_segments_remain_separate_by_vlan(self):
        data = snapshot()
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": CLIENT, "bridge_port": "2",
             "vlan_id": "1"},
            {"source_mac": SWITCH, "target_mac": OTHER, "bridge_port": "2",
             "vlan_id": "2"},
        ]
        graph = build_internal_graph(data)
        self.assertEqual(graph["network_segment_count"], 2)
        self.assertEqual({s["vlan_id"] for s in graph["network_segments"]},
                         {"1", "2"})

    def test_user_confirmed_link_is_separate_from_lldp_and_fdb(self):
        data = snapshot()
        data["direct_links"] = []
        data["mesh_links"] = []
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": OTHER,
             "bridge_port": "49154", "vlan_id": "1",
             "interface_name": "gigabitEthernet 1/0/2"},
            {"source_mac": SWITCH, "target_mac": CLIENT,
             "bridge_port": "49154", "vlan_id": "1",
             "interface_name": "gigabitEthernet 1/0/2"},
        ]
        data["manual_links"] = [{
            "source_mac": SWITCH, "target_mac": OTHER,
            "bridge_port": "49154", "vlan_id": "1",
            "confirmation": "user_confirmed",
        }]
        graph = build_internal_graph(data)
        self.assertEqual(graph["model_version"], 10)
        self.assertEqual(len(graph["links"]), 1)
        self.assertEqual(graph["links"][0]["evidence"], "user_confirmed")
        segment = graph["network_segments"][0]
        self.assertEqual(segment["user_confirmed_neighbors"], [
            {"mac": OTHER, "evidence": "user_confirmed"}
        ])
        self.assertFalse(segment["physical_topology_confirmed"])
        self.assertNotIn(CLIENT, [n["mac"] for n in
                                 segment["user_confirmed_neighbors"]])

    def test_unconfirmed_manual_observation_cannot_create_link(self):
        data = snapshot()
        data["direct_links"] = []
        data["mesh_links"] = []
        data["manual_links"] = [{
            "source_mac": SWITCH, "target_mac": OTHER,
            "confirmation": "observed",
        }]
        graph = build_internal_graph(data)
        self.assertEqual(graph["link_count"], 0)

    def test_confirmed_downstream_switch_creates_unverified_branch(self):
        data = snapshot()
        data["nodes"] = [
            {"mac": SWITCH, "name": "TL-SG3428", "known_host": True},
            {"mac": OTHER, "name": "TL-SG1024DE", "known_host": True},
            {"mac": CLIENT, "name": "Server-3", "known_host": True},
        ]
        data["direct_links"] = []
        data["mesh_links"] = []
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": OTHER,
             "bridge_port": "49154", "vlan_id": "1"},
            {"source_mac": SWITCH, "target_mac": CLIENT,
             "bridge_port": "49154", "vlan_id": "1"},
        ]
        data["manual_links"] = [{
            "source_mac": SWITCH, "target_mac": OTHER,
            "bridge_port": "49154", "vlan_id": "1",
            "confirmation": "user_confirmed",
        }]
        graph = build_internal_graph(data)
        self.assertEqual(graph["downstream_branch_count"], 1)
        branch = graph["downstream_branches"][0]
        self.assertEqual(branch["downstream_switch_mac"], OTHER)
        self.assertEqual(branch["candidate_count"], 1)
        self.assertEqual(branch["reachable_lan_candidates"][0]["mac"], CLIENT)
        self.assertFalse(branch["reachable_lan_candidates"][0]["physical_attachment_confirmed"])
        self.assertFalse(branch["candidate_direct_links_confirmed"])
        self.assertEqual(graph["link_count"], 1)

    def test_structured_graph_branch_does_not_invent_client_cable(self):
        data = snapshot()
        data["nodes"] = [
            {"mac": SWITCH, "name": "TL-SG3428", "known_host": True},
            {"mac": OTHER, "name": "TL-SG1024DE", "known_host": True},
            {"mac": CLIENT, "name": "Server-3", "known_host": True},
        ]
        data["direct_links"] = []
        data["mesh_links"] = []
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": OTHER,
             "bridge_port": "49154", "vlan_id": "1"},
            {"source_mac": SWITCH, "target_mac": CLIENT,
             "bridge_port": "49154", "vlan_id": "1"},
        ]
        data["manual_links"] = [{
            "source_mac": SWITCH, "target_mac": OTHER,
            "bridge_port": "49154", "vlan_id": "1",
            "confirmation": "user_confirmed",
        }]
        graph = build_internal_graph(data)
        self.assertEqual(graph["model_version"], 10)
        self.assertEqual(graph["graph_branch_count"], 1)
        branch = graph["graph_branches"][0]
        self.assertEqual(branch["parent_mac"], SWITCH)
        self.assertEqual(branch["switch_mac"], OTHER)
        self.assertEqual(branch["uplink"]["evidence"], "user_confirmed")
        self.assertTrue(branch["uplink"]["physical_link_confirmed"])
        self.assertEqual(branch["member_count"], 1)
        self.assertEqual(branch["members"][0]["mac"], CLIENT)
        self.assertEqual(branch["members"][0]["relationship"], "reachable_in_branch")
        self.assertFalse(branch["members"][0]["physical_link_confirmed"])
        self.assertFalse(branch["members"][0]["downstream_port_known"])
        self.assertFalse(any(
            frozenset((link["source_mac"], link["target_mac"]))
            == frozenset((OTHER, CLIENT)) for link in graph["links"]
        ))

    def test_unconfirmed_switch_does_not_create_downstream_branch(self):
        data = snapshot()
        data["nodes"] = [{"mac": OTHER, "name": "TL-SG1024DE",
                          "known_host": True}]
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": OTHER,
             "bridge_port": "49154", "vlan_id": "1"},
            {"source_mac": SWITCH, "target_mac": CLIENT,
             "bridge_port": "49154", "vlan_id": "1"},
        ]
        graph = build_internal_graph(data)
        self.assertEqual(graph["downstream_branch_count"], 0)

    def test_lan_port_memberships_keep_three_evidence_classes_separate(self):
        data = snapshot()
        data["nodes"] = [
            {"mac": SWITCH, "name": "Managed switch", "known_host": True},
            {"mac": OTHER, "name": "Other switch", "known_host": True},
            {"mac": CLIENT, "name": "Wireless client", "known_host": True},
            {"mac": ROUTER, "name": "Router", "known_host": True},
        ]
        data["direct_links"] = [{
            "source_mac": SWITCH, "target_mac": ROUTER,
            "source_port_number": "2",
        }]
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": ROUTER,
             "bridge_port": "49154", "vlan_id": "1",
             "interface_name": "gigabitEthernet 1/0/2"},
            {"source_mac": SWITCH, "target_mac": OTHER,
             "bridge_port": "49154", "vlan_id": "1",
             "interface_name": "gigabitEthernet 1/0/2"},
            {"source_mac": SWITCH, "target_mac": CLIENT,
             "bridge_port": "49154", "vlan_id": "1",
             "interface_name": "gigabitEthernet 1/0/2"},
        ]
        data["manual_links"] = [{
            "source_mac": SWITCH, "target_mac": OTHER,
            "bridge_port": "49154", "vlan_id": "1",
            "confirmation": "user_confirmed",
        }]
        graph = build_internal_graph(data)
        self.assertEqual(graph["model_version"], 10)
        self.assertEqual(graph["lan_port_membership_count"], 1)
        port = graph["lan_port_memberships"][0]
        members = {m["mac"]: m for m in port["members"]}
        self.assertEqual(members[ROUTER]["evidence"], "lldp")
        self.assertTrue(members[ROUTER]["physical_link_confirmed"])
        self.assertEqual(members[OTHER]["evidence"], "user_confirmed")
        self.assertTrue(members[OTHER]["physical_link_confirmed"])
        self.assertEqual(members[CLIENT]["relationship"], "wlan_transit")
        self.assertFalse(members[CLIENT]["physical_link_confirmed"])
        self.assertEqual(port["confirmed_neighbor_count"], 2)
        self.assertEqual(port["wlan_transit_count"], 1)
        self.assertFalse(any(
            frozenset((link["source_mac"], link["target_mac"]))
            == frozenset((SWITCH, CLIENT)) for link in graph["links"]
        ))

    def test_single_known_fdb_device_is_only_a_confirmation_candidate(self):
        data = snapshot()
        data["nodes"] = [{"mac": OTHER, "name": "SynologyNAS",
                          "known_host": True}]
        data["direct_links"] = []
        data["mesh_links"] = []
        data["reachable_via_port"] = [{
            "source_mac": SWITCH, "target_mac": OTHER,
            "bridge_port": "49155", "vlan_id": "1",
            "interface_name": "gigabitEthernet 1/0/3",
        }]
        graph = build_internal_graph(data)
        self.assertEqual(graph["model_version"], 10)
        self.assertEqual(graph["physical_link_candidate_count"], 1)
        candidate = graph["physical_link_candidates"][0]
        self.assertEqual(candidate["target_mac"], OTHER)
        self.assertEqual(candidate["status"], "requires_user_confirmation")
        self.assertFalse(candidate["physical_link_confirmed"])
        self.assertEqual(graph["link_count"], 0)

    def test_multiple_macs_or_wlan_never_suggests_direct_cable(self):
        data = snapshot()
        data["nodes"] = [
            {"mac": OTHER, "name": "NAS", "known_host": True},
            {"mac": ROUTER, "name": "Router", "known_host": True},
        ]
        data["direct_links"] = []
        data["mesh_links"] = []
        data["reachable_via_port"] = [
            {"source_mac": SWITCH, "target_mac": OTHER,
             "bridge_port": "49155", "vlan_id": "1"},
            {"source_mac": SWITCH, "target_mac": ROUTER,
             "bridge_port": "49155", "vlan_id": "1"},
        ]
        graph = build_internal_graph(data)
        self.assertEqual(graph["physical_link_candidate_count"], 0)

    def test_confirmed_single_device_no_longer_needs_confirmation(self):
        data = snapshot()
        data["nodes"] = [{"mac": OTHER, "name": "NAS", "known_host": True}]
        data["direct_links"] = []
        data["mesh_links"] = []
        data["reachable_via_port"] = [{
            "source_mac": SWITCH, "target_mac": OTHER,
            "bridge_port": "49155", "vlan_id": "1",
        }]
        data["manual_links"] = [{
            "source_mac": SWITCH, "target_mac": OTHER,
            "bridge_port": "49155", "vlan_id": "1",
            "confirmation": "user_confirmed",
        }]
        graph = build_internal_graph(data)
        self.assertEqual(graph["physical_link_candidate_count"], 0)
        self.assertEqual(graph["link_count"], 1)

    def test_unknown_fdb_device_is_not_assumed_direct(self):
        data = snapshot()
        data["reachable_via_port"] = [{
            "source_mac": SWITCH, "target_mac": OTHER,
            "bridge_port": "49155", "vlan_id": "1",
            "interface_name": "gigabitEthernet 1/0/3",
        }]
        device = build_internal_graph(data)["fdb_port_groups"][0]["devices"][0]
        self.assertEqual(device["name"], "")
        self.assertEqual(device["connection_class"], "fdb_reachable_only")
        self.assertFalse(device["lldp_direct_neighbor"])

    def test_repeater_client_attachment(self):
        graph = build_internal_graph(snapshot())
        self.assertEqual(graph["wlan_attachments"][CLIENT]["parent_mac"], REPEATER)
        self.assertNotIn(REPEATER, graph["wlan_attachments"])

    def test_fdb_is_never_a_direct_link(self):
        graph = build_internal_graph(snapshot())
        self.assertEqual(len(graph["reachability"]), 1)
        self.assertFalse(any(
            link["evidence"] == "fdb" for link in graph["links"]
        ))

    def test_ambiguous_wlan_parent_is_not_guessed(self):
        data = snapshot()
        data["mesh_links"].append({
            "source_mac": OTHER, "target_mac": CLIENT,
            "link_type": "WLAN", "link_state": "CONNECTED",
            "source_mesh_role": "slave", "target_mesh_role": "unknown",
        })
        graph = build_internal_graph(data)
        self.assertNotIn(CLIENT, graph["wlan_attachments"])
        self.assertTrue(any(
            item["reason"] == "multiple_wlan_parents"
            for item in graph["conflicts"]
        ))

    def test_disconnected_links_not_active(self):
        data = snapshot()
        data["mesh_links"][2]["link_state"] = "DISCONNECTED"
        graph = build_internal_graph(data)
        self.assertNotIn(CLIENT, graph["wlan_attachments"])

    def test_all_links_not_truncated_to_sensor_sample(self):
        data = snapshot()
        data["nodes"] += [{"mac": f"02:00:00:00:01:{i:02X}"} for i in range(40)]
        data["mesh_links"] += [{
            "source_mac": ROUTER, "target_mac": f"02:00:00:00:01:{i:02X}",
            "link_type": "WLAN", "link_state": "CONNECTED",
            "source_mesh_role": "master", "target_mesh_role": "unknown",
        } for i in range(40)]
        graph = build_internal_graph(data)
        self.assertEqual(len(graph["wlan_attachments"]), 41)
        self.assertGreater(graph["link_count"], 32)

    def test_normalizes_mac_and_preserves_node_identity(self):
        data = snapshot()
        data["nodes"][0]["mac"] = ROUTER.lower().replace(":", "-")
        graph = build_internal_graph(data)
        self.assertIn(ROUTER, graph["nodes"])
        self.assertEqual(graph["node_count"], 5)


if __name__ == "__main__":
    unittest.main()
