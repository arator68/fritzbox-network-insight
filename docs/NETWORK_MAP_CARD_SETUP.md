# Standalone Network Insight Map (prototype)

This branch adds **only a Lovelace map**. It does not change topology calculations, discovery, sensors, or existing entity IDs.

## Resource

After installing this branch and restarting Home Assistant, add the following JavaScript module under Settings → Dashboards → Resources:

`/fritzbox_network_insight/fritz-network-insight-map-card.js`

Then add a manual card:

```yaml
type: custom:fritz-network-insight-map-card
design: lcars
height: 620
refresh_seconds: 60
```

If more than one FRITZ!Box configuration entry is present, set `entry_id` to select one.

## Data

The card reads the **existing** read-only service `fritzbox_network_insight.topology_view` using Home Assistant's websocket service response. It does not use truncated topology sensor attributes. The display only draws `confirmed_lan` edges with `physical_link_confirmed=true` and `mesh_wlan` edges with `evidence=avm_mesh`. Unassigned devices remain visible in a separate list; FDB reachability is never drawn as a physical cable.

## Limitations / testing

This is an **initial independent frontend implementation**, not a byte-for-byte port of the original 0.7.29 JS. The original styling inspired the LCARS/cyber themes; layout and interactions still need comparison against the uploaded reference. Browser integration and HA runtime tests are pending. Do not merge before a Home Assistant installation test.

## Current-device filtering (PR #48 update)

The existing read-only `topology_view` response now exposes the already-computed `known_host` flag from the internal graph. The card renders only `known_host: true` nodes and only links whose endpoints both occur in that current-host list. Saved LLDP/FDB-only identities are not shown as current devices. Component positions are grouped by reported device type; no graph traversal or physical topology inference runs in the frontend. The card does not remove Home Assistant device-registry entries or delete historical evidence.
