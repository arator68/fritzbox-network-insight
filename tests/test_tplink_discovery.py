"""Regression tests for the Easy Smart discovery wire format."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
import socket

PATH = Path(__file__).resolve().parents[1] / "custom_components/fritzbox_network_insight/discovery/tplink_discovery.py"
spec = importlib.util.spec_from_file_location("tplink_discovery_test_module", PATH)
codec = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = codec
spec.loader.exec_module(codec)

HOST = bytes.fromhex("2ccf67ef3b60")
SEQ = 394
# Decoded reply captured during the read-only Linux discovery test.
REPLY = bytes.fromhex(
    "0102ec750cc268f72ccf67ef3b60018a0000000000b900000000000000000000"
    "0001000c544c2d5347313032344445000002000c544c2d534731303234444500"
    "00030006ec750cc268f70007001f312e302e30204275696c642032303233303631"
    "362052656c2e33343230350000080010544c2d534731303234444520372e3000"
    "000900010100040004c0a8b23100050004ffffff0000060004c0a8b201"
    "000d000101000e000100000f0004001c00000010000100ffff0000"
)


class TestEasySmartDiscovery(unittest.TestCase):
    def test_request(self):
        self.assertEqual(codec.transform(codec.build_request(HOST, SEQ)).hex(),
                         "01000000000000002ccf67ef3b60018a00000000002400000000000000000000ffff0000")

    def test_captured_reply_with_unknown_fields(self):
        identity = codec.parse_response(codec.transform(REPLY), HOST, SEQ)
        self.assertEqual(identity.mac, "ec:75:0c:c2:68:f7")
        self.assertEqual(identity.model, "TL-SG1024DE")
        self.assertEqual(identity.ip, "192.168.178.49")
        self.assertEqual(identity.hardware, "TL-SG1024DE 7.0")
        self.assertEqual(identity.firmware, "1.0.0 Build 20230616 Rel.34205")

    def test_wrong_sequence(self):
        with self.assertRaises(ValueError):
            codec.parse_response(codec.transform(REPLY), HOST, SEQ + 1)

    def test_wrong_host(self):
        with self.assertRaises(ValueError):
            codec.parse_response(codec.transform(REPLY), bytes(6), SEQ)

    def test_truncated_reply(self):
        with self.assertRaises(ValueError):
            codec.parse_response(codec.transform(REPLY[:-1]), HOST, SEQ)

    def test_mac_mismatch(self):
        raw = REPLY.replace(bytes.fromhex("00030006ec750cc268f7"),
                            bytes.fromhex("00030006ec750cc268f8"))
        with self.assertRaises(ValueError):
            codec.parse_response(codec.transform(raw), HOST, SEQ)


    def test_broadcast_transport(self):
        sender, receiver = MagicMock(), MagicMock()
        sender.__enter__.return_value = sender
        receiver.__enter__.return_value = receiver
        receiver.recvfrom.side_effect = [
            (b"invalid", ("192.0.2.1", 29808)),
            (codec.transform(REPLY), ("192.168.178.49", 29808)),
            (codec.transform(REPLY), ("192.168.178.49", 29808)),
            socket.timeout(),
        ]
        with patch.object(codec.socket, "socket", side_effect=[sender, receiver]), patch.object(codec.secrets, "randbelow", return_value=SEQ):
            result = codec.discover_switches("192.168.178.2", HOST)
        sender.bind.assert_called_once_with(("192.168.178.2", 29809))
        receiver.bind.assert_called_once_with(("255.255.255.255", 29809))
        sender.sendto.assert_called_once_with(codec.build_request(HOST, SEQ), ("255.255.255.255", 29808))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].model, "TL-SG1024DE")

    def test_socket_failure_is_not_empty_success(self):
        with patch.object(codec.socket, "socket", side_effect=OSError("bind failed")):
            with self.assertRaises(OSError):
                codec.discover_switches("192.168.178.2", HOST)
