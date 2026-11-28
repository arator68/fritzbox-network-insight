"""Read-only TP-Link Easy Smart discovery packet codec.

Wire format verified against a TL-SG1024DE v7 discovery exchange.
No login or configuration commands are implemented.
"""
from __future__ import annotations

from dataclasses import dataclass
from ipaddress import IPv4Address
import struct

SEND_PORT = 29808
RECEIVE_PORT = 29809
_HEADER = struct.Struct("!BB6s6sHIHHHHI")
_END = b"\xff\xff\x00\x00"
# Protocol's fixed initial permutation, not a device credential.
_KEY = bytes([
    191,155,227,202,99,162,79,104,49,18,190,164,30,76,189,131,
    23,52,86,106,207,125,126,169,196,28,172,58,188,132,160,3,
    36,120,144,168,12,231,116,44,41,97,108,213,42,198,32,148,
    218,107,247,112,204,14,66,68,91,224,206,235,33,130,203,178,
    1,134,199,78,249,123,7,145,73,208,209,100,74,115,72,118,
    8,22,243,147,64,96,5,87,60,113,233,152,31,219,143,174,
    232,153,245,158,254,70,170,75,77,215,211,59,71,133,214,157,
    151,6,46,81,94,136,166,210,4,43,241,29,223,176,67,63,
    186,137,129,40,248,255,55,15,62,183,222,105,236,197,127,54,
    179,194,229,185,37,90,237,184,25,156,173,26,187,220,2,225,
    0,240,50,251,212,253,167,17,193,205,177,21,181,246,82,226,
    38,101,163,182,242,92,20,11,95,13,230,16,121,124,109,195,
    117,39,98,239,84,56,139,161,47,201,51,135,250,10,19,150,
    45,111,27,24,142,80,85,83,234,138,216,57,93,65,154,141,
    122,34,140,128,238,88,89,9,146,171,149,53,102,61,114,69,
    217,175,103,228,35,180,252,200,192,165,159,221,244,110,119,48,
])


@dataclass(frozen=True)
class DiscoveryIdentity:
    mac: str
    model: str
    ip: str | None
    hardware: str | None
    firmware: str | None


def transform(packet: bytes) -> bytes:
    """Apply the symmetric wire encoding."""
    state = bytearray(_KEY)
    result = bytearray(packet)
    j = 0
    for k, value in enumerate(packet):
        i = (k + 1) & 255
        j = (j + state[i]) & 255
        state[i], state[j] = state[j], state[i]
        result[k] = value ^ state[(state[i] + state[j]) & 255]
    return bytes(result)


def build_request(host_mac: bytes, sequence: int) -> bytes:
    if len(host_mac) != 6 or not 0 <= sequence <= 65535:
        raise ValueError("Invalid discovery request identity")
    return transform(_HEADER.pack(
        1, 0, bytes(6), host_mac, sequence, 0,
        _HEADER.size + len(_END), 0, 0, 0, 0,
    ) + _END)


def parse_response(packet: bytes, host_mac: bytes, sequence: int) -> DiscoveryIdentity:
    """Validate a reply to our request; ignore unknown length-delimited fields."""
    raw = transform(packet)
    if len(raw) < _HEADER.size + 4 or not raw.endswith(_END):
        raise ValueError("Invalid discovery packet")
    version, op, mac, host, seq, error, length, offset, flag, token, checksum = _HEADER.unpack_from(raw)
    if (version != 1 or op != 2 or host != host_mac or seq != sequence
            or error or offset or length != len(raw)
            or mac == bytes(6) or mac[0] & 1):
        raise ValueError("Unmatched or invalid discovery response")
    fields = {}
    pos = _HEADER.size
    end = len(raw) - 4
    while pos < end:
        if end - pos < 4:
            raise ValueError("Truncated TLV header")
        kind, size = struct.unpack_from("!HH", raw, pos)
        pos += 4
        if kind == 65535 or pos + size > end:
            raise ValueError("Invalid TLV length")
        if kind in (1, 3, 4, 7, 8):
            if kind in fields:
                raise ValueError("Duplicate identity field")
            fields[kind] = raw[pos:pos + size]
        pos += size
    if fields.get(3) != mac:
        raise ValueError("MAC mismatch")
    def string(kind: int) -> str | None:
        value = fields.get(kind, b"").split(b"\x00", 1)[0].decode("ascii").strip()
        return value or None
    model = string(1)
    if not model:
        raise ValueError("Missing model")
    ip = str(IPv4Address(fields[4])) if 4 in fields else None
    return DiscoveryIdentity(mac.hex(":"), model, ip, string(8), string(7))
