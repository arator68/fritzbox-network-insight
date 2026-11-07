# Discovery architecture

The FRITZ!Box host list is the authoritative source of known MAC addresses.
The discovery manager is deliberately passive by default. MAC vendor prefixes
identify a registration owner, **not** a device type. Ethernet and WLAN describe
the connection, **not** the device type.

Optional adapters will later be responsible for SNMP, SSDP/UPnP, and mDNS
discovery. They must be explicitly enabled and configured, rate-limited, and
must not turn timeouts into claims that a protocol is unsupported. SNMPv3
credentials must be stored in Home Assistant configuration entries, never in
the repository or sensor attributes.

Evidence is passed to `classify_device` via
`detected_device_type` and `detected_device_type_source`.
A manual MAC-based override remains highest priority. Unknown is preferable
to an unsupported guess.

This first step establishes the extension point. It does **not** probe
devices or claim that a TP-Link device is necessarily a switch.
