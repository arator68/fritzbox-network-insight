# Network Map 0.7.29 – Portierung (in Arbeit)

Ausgangsbasis: alte `fritz-network-map-card.js` aus der vom Nutzer bereitgestellten ZIP-Datei Version 0.7.29.

## Bestätigte vollständige Datenquelle

Die bestehende Integration stellt bereits den read-only Dienst `fritzbox_network_insight.topology_view` bereit (`__init__.py`), der `build_topology_view(selected.get_internal_topology_graph())` aufruft. Er liefert **alle** Knoten und nachgewiesenen Kanten, nicht nur die begrenzten Sensor-Attribute.

Schema: `nodes: [{id, mac, name, ip_address, device_type, mesh_role}]`, `edges: [{source, target, kind, evidence, physical_link_confirmed, port}]`; außerdem `mesh_lan_observations` und `branches`.

## Unveränderliche Regeln

- Nur die grafische Karte portieren, nicht das Network Center.
- Keine Änderungen an der bestehenden Topologie, Sensorik, LLDP/FDB, Erkennung oder am Datenmodell.
- Knoten über MAC zuordnen.
- `confirmed_lan` nur für bestätigte LAN-Verbindungen, `mesh_wlan` für AVM-Mesh-WLAN.
- FDB-Reichweite und Mesh-LAN-Beobachtungen nicht als direkte Kabelverbindungen darstellen.
- Kein statisches Eintragen von Verbindungen.
- Frontend muss die vollständige Antwort des bestehenden read-only Dienstes verarbeiten, statt die gekürzten `nodes_sample`-/`direct_links`-Attribute auszulesen.

Dieser Branch ist die isolierte Arbeitsgrundlage. **Die Karte ist noch nicht in die Integration eingebunden.**
