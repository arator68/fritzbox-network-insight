"""Regression tests for the pure device detail model."""
import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight"
PACKAGE = "fritzbox_network_insight"
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT)]
    sys.modules[PACKAGE] = package

def _load(name):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

_load("device")
model = _load("device_details")


def test_identity_and_source_provenance():
    details = model.build_device_details(
        "d4:d6:df:0e:1b:54",
        {"snmp": {"device_type": "switch", "port": 1},
         "avm_mesh": {"device_type": "unknown", "name": "SG3428"}},
    )
    assert details.mac == "D4:D6:DF:0E:1B:54"
    assert [x.source for x in details.values("device_type")] == ["snmp", "avm_mesh"]
    assert details.values("port")[0].value == 1


def test_missing_values_omitted_but_false_and_zero_retained():
    details = model.build_device_details(
        "04:B4:FE:18:79:65",
        {"tr064": {"wifi_signal": None, "name": " ", "online": False, "speed": 0}},
    )
    assert not details.available("wifi_signal")
    assert not details.available("name")
    assert details.values("online")[0].value is False
    assert details.values("speed")[0].value == 0


def test_invalid_identity_and_missing_source_rejected():
    import pytest
    with pytest.raises(ValueError):
        model.build_device_details("invalid", {"tr064": {"name": "x"}})
    with pytest.raises(ValueError):
        model.build_device_details("04:B4:FE:18:79:65", {"": {"name": "x"}})
