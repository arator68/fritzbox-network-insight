"""Bounded, unicast SSDP M-SEARCH for explicitly selected known IPv4 hosts.

This is a conservative probe: many UPnP devices respond only to multicast
M-SEARCH. No response is therefore NOT proof that SSDP is unsupported.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Mapping
from typing import Any

from . import DiscoveryEvidence


class SsdpDiscoveryAdapter:
    """Try SSDP on the selected host without scanning the whole LAN."""

    name = "ssdp"
    _TIMEOUT = 2.0

    async def async_discover(
        self, host: Mapping[str, Any]
    ) -> DiscoveryEvidence | None:
        ip_text = str(host.get("ip_address") or "")
        try:
            address = ipaddress.ip_address(ip_text)
        except ValueError:
            return None
        if not isinstance(address, ipaddress.IPv4Address):
            return None
        if not address.is_private or address.is_loopback or address.is_link_local:
            return None

        message = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {ip_text}:1900\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 1\r\n"
            "ST: ssdp:all\r\n"
            "\r\n"
        ).encode("ascii")

        loop = asyncio.get_running_loop()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setblocking(False)
            sock.bind(("0.0.0.0", 0))
            try:
                await loop.sock_sendto(sock, message, (ip_text, 1900))
                deadline = loop.time() + self._TIMEOUT
                while True:
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        return None
                    data, peer = await asyncio.wait_for(
                        loop.sock_recvfrom(sock, 8192), timeout=remaining
                    )
                    if peer[0] != ip_text:
                        continue
                    first_line = data.split(b"\r\n", 1)[0].upper()
                    if not first_line.startswith(b"HTTP/1.1 200"):
                        continue
                    return DiscoveryEvidence(source="ssdp", protocol="ssdp")
            except (OSError, TimeoutError):
                return None
