# FRITZ!Box Network Insight

A Home Assistant custom integration for discovering devices reported by a FRITZ!Box and preparing a reliable foundation for network topology analysis.

## Current development status

The `develop` branch contains an early, manually installable development version. It is **not a stable release**.

Implemented in the current development line:

- Configure one FRITZ!Box through the Home Assistant UI.
- Validate credentials by making a live TR-064 host-list request.
- Read the FRITZ!Box host list through the TR-064 Hosts service.
- Normalize MAC addresses and use them as stable device identities.
- Poll the host list every 60 seconds.
- Create one overview sensor with the number of hosts in the latest scan.
- Create one status sensor per discovered MAC address.
- Expose available host metadata (name, IP address, active state and interface type) as sensor attributes.
- Log successful scan counts at INFO level and individual device details at DEBUG level.

The integration currently reports the hosts returned by the FRITZ!Box. It does not yet determine physical switch-port topology, prove LLDP links, or retain historical last-seen information across restarts. Those capabilities require later development phases and additional data sources.

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
