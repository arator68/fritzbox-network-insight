"""Resolve DNS names independently of FRITZ!Box device labels.

Uses the DNS resolver configured for the Home Assistant host. A reverse
(PTR) record is only accepted if a forward lookup resolves back to the IP.
"""
from __future__ import annotations

import ipaddress
import socket


def resolve_dns_name(ip_address: str) -> str | None:
    """Return a forward-confirmed PTR hostname, or None if not resolvable."""
    try:
        address = ipaddress.ip_address(ip_address)
        reverse_name, _, _ = socket.gethostbyaddr(str(address))
        name = reverse_name.rstrip(".").strip()
        if not name:
            return None
        results = socket.getaddrinfo(name, None, family=socket.AF_INET if address.version == 4 else socket.AF_INET6, type=socket.SOCK_STREAM)
        if any(ipaddress.ip_address(item[4][0]) == address for item in results):
            return name
    except (OSError, ValueError, UnicodeError):
        return None
    return None
