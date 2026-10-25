"""Tests for the Modbus driver descriptors this package advertises."""

import pytest
from scietex.hal.serial.gateway.drivers import (
    ENTRY_POINT_GROUP,
    verify_driver,
)

from scietex.hal.vacuum_gauge.modbus_drivers import (
    erstevak_rs485_v1,
    thyracont_rs485_v1,
)


def test_thyracont_descriptor_points_at_the_v1_bundle():
    assert thyracont_rs485_v1.name == "thyracont_rs485_v1"
    assert thyracont_rs485_v1.label == "Thyracont RS485 V1"
    assert thyracont_rs485_v1.device_type == "Vacuum Gauge"
    assert thyracont_rs485_v1.framer.endswith("ThyracontASCIIFramer")
    assert thyracont_rs485_v1.decoder.endswith("ThyracontDecodePDU")
    assert thyracont_rs485_v1.pdus == [
        "scietex.hal.vacuum_gauge.thyracont.rs485.v1.request.ThyracontRequest"
    ]
    assert thyracont_rs485_v1.translator.endswith("ThyracontV1Translator")


def test_erstevak_descriptor_shares_the_v1_bundle():
    assert erstevak_rs485_v1.name == "erstevak_rs485_v1"
    assert erstevak_rs485_v1.label == "Erstevak RS485 V1"
    assert erstevak_rs485_v1.framer == thyracont_rs485_v1.framer
    assert erstevak_rs485_v1.translator == thyracont_rs485_v1.translator


@pytest.mark.parametrize("driver", [thyracont_rs485_v1, erstevak_rs485_v1])
def test_descriptors_verify(driver):
    assert verify_driver(driver) is None


def test_descriptors_are_declared_as_entry_points():
    """The declarations are install-time; skip when metadata is stale."""
    from importlib.metadata import entry_points

    declared = {entry.name for entry in entry_points(group=ENTRY_POINT_GROUP)}
    if not declared:
        pytest.skip("installed metadata carries no scietex.modbus.drivers group")
    assert {"thyracont_rs485_v1", "erstevak_rs485_v1"} <= declared
