# FRITZ!Box Network Insight

A Home Assistant custom integration for network device discovery, identification and topology analysis.

> **Project status:** Planning and architecture phase. The integration is not yet installable and no release is available.

## Planned capabilities

- Discover network devices through FRITZ!Box data and additional supported sources.
- Use the MAC address as the stable device identity.
- Identify manufacturers locally through an updateable OUI database.
- Collect observations from managed switches through SNMP and, where supported, LLDP.
- Discover AVM routers and repeaters and represent them as separate Home Assistant devices.
- Preserve observations from different sources instead of silently overwriting conflicting information.
- Distinguish proven, probable and unknown network connections.
- Retain device history across Home Assistant restarts.
- Create entities dynamically from information that is actually available.
- Provide German and English translations.

These are planned requirements, not implemented features.

## Development status

The project is currently in the specification phase. The detailed requirements and module interfaces will be documented and reviewed before implementation begins.

## Branch strategy

- `main`: released and approved versions.
- `develop`: current integration and testing branch.
- `feature/*`: isolated development of individual features.

Changes are reviewed against the agreed requirements before they are merged into `main`.

## Installation

Installation instructions will be added when the integration is ready for testing and a first release is available.

## Lizenz / License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
