# FRITZ!Box Network Insight

A Home Assistant custom integration for discovering devices reported by a FRITZ!Box and preparing a reliable foundation for network topology analysis.

## Current development status

The `develop` branch is a **development build**, not a stable release. The integration currently includes:

- TR-064 device discovery, MAC-based device identity, device status and metadata (including DNS names, manufacturer/OUI and device classification).
- WLAN metrics, AVM Mesh observations and repeater TR-064 WLAN data collection. Repeater raw responses are retained **in memory only** as the latest successful snapshot; no raw-data history or Home Assistant `.storage` persistence.
- Targeted Home Assistant action `fritzbox_network_insight.repeater_client_raw_diagnostics` to inspect captured fields for a selected MAC address.
- SNMP/LLDP/FDB-based switch observations and port telemetry. FDB reachability must **not** be interpreted as a verified direct cable connection.
- German/English translations and existing entity-name/ID preservation.

**Merged:** PR #39 (WLAN metadata and repeater raw diagnostics), 11 November 2026.

**In progress:** [PR #40 – Device Connection Details](https://github.com/arator68/fritzbox-network-insight/pull/40), a separate draft feature awaiting Home Assistant validation. LAN port metrics and throughput measurements are planned for a subsequent feature.

For verified observations, limitations, next steps and historical notes, see [Development Status](docs/DEVELOPMENT_STATUS.md).

## Installation for development

1. Select the `develop` branch on GitHub and download its ZIP archive.
2. Copy only `custom_components/fritzbox_network_insight` into the Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration** and search for **FRITZ!Box Network Insight**.
5. Enter the FRITZ!Box address and a user account permitted to access the FRITZ!Box application/TR-064 interface.

Do not publish or share the FRITZ!Box password or unredacted diagnostic logs.

## Branch strategy

- `main`: released and approved versions.
- `develop`: current integration and testing branch.
- `feature/*`: isolated development of individual features.

Feature branches are reviewed through pull requests targeting `develop`. Only approved releases are merged into `main`.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

### Language support and existing entity names

FRITZ!Box Network Insight provides German and English translations for entity names and enum states via Home Assistant's native `translation_key` mechanism. **Entity names are resolved in the Home Assistant backend language when the entity is first registered.** Changing only a user's frontend/profile language does not rename already registered entities; this is Home Assistant's documented behavior. Translated enum states (for example, `not_started`) can still appear in the selected frontend language.

To verify translated names for newly created entities, set the **Home Assistant system language** before creating them. Existing entity names and entity IDs are deliberately not rewritten by this integration: user customizations and automation references must remain intact. Do not delete or recreate entities merely to test a language switch.
