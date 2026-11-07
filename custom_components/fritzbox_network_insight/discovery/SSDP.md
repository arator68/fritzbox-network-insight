# Manual SSDP discovery (experimental)

Press the device's **Geräteerkennung starten** button to send a single
unicast SSDP M-SEARCH request to its known private IPv4 address, UDP port
1900. The adapter waits up to two seconds for an HTTP 200 SSDP reply
**from that same IP**. No periodic probes or LAN-wide multicast are sent.

Results are displayed in the existing **Ergebnis Geräteerkennung** sensor:
- `responded`: at least one selected device replied to SSDP;
  attribute `protocols` includes `ssdp`.
- `no_response`: the targeted request did not yield a valid response;
  this does **not** mean SSDP is unsupported.
- `no_targets`: no known device matched the request.

This limited first stage does not download UPnP description documents, does
not identify device types/models, and does not alter MAC-based entities.
Many SSDP implementations only respond to **multicast** M-SEARCH and will
not answer this unicast probe. A future user-approved multicast mode can
improve coverage, but would send packets beyond selected devices.
