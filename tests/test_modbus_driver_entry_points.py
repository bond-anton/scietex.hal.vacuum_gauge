"""Tests for the Modbus driver descriptors this package advertises."""

import pytest
from scietex.hal.serial.gateway.drivers import (
    ENTRY_POINT_GROUP,
    verify_driver,
)

from scietex.hal.vacuum_gauge.modbus_drivers import (
    erstevak_rs485_v1,
    erstevak_rs485_v2,
    thyracont_rs485_v1,
    thyracont_rs485_v2,
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


def test_thyracont_v2_descriptor_points_at_the_v2_bundle():
    assert thyracont_rs485_v2.name == "thyracont_rs485_v2"
    assert thyracont_rs485_v2.label == "Thyracont RS485 V2"
    assert thyracont_rs485_v2.device_type == "Vacuum Gauge"
    assert thyracont_rs485_v2.framer.endswith("rs485.v2.framer.ThyracontASCIIFramer")
    assert thyracont_rs485_v2.decoder.endswith("rs485.v2.decoder.ThyracontDecodePDU")
    assert thyracont_rs485_v2.pdus == [
        "scietex.hal.vacuum_gauge.thyracont.rs485.v2.request.ThyracontRequest"
    ]
    assert thyracont_rs485_v2.translator.endswith("ThyracontV2Translator")


def test_erstevak_v2_descriptor_shares_the_v2_bundle():
    assert erstevak_rs485_v2.name == "erstevak_rs485_v2"
    assert erstevak_rs485_v2.label == "Erstevak RS485 V2"
    assert erstevak_rs485_v2.framer == thyracont_rs485_v2.framer
    assert erstevak_rs485_v2.decoder == thyracont_rs485_v2.decoder
    assert erstevak_rs485_v2.pdus == thyracont_rs485_v2.pdus
    assert erstevak_rs485_v2.translator == thyracont_rs485_v2.translator


def test_v2_bundle_is_distinct_from_v1():
    """V2 is a different wire protocol, so it must not reuse the V1 classes."""
    assert thyracont_rs485_v2.framer != thyracont_rs485_v1.framer
    assert thyracont_rs485_v2.decoder != thyracont_rs485_v1.decoder
    assert thyracont_rs485_v2.pdus != thyracont_rs485_v1.pdus
    assert thyracont_rs485_v2.translator != thyracont_rs485_v1.translator


@pytest.mark.parametrize(
    "driver",
    [thyracont_rs485_v1, erstevak_rs485_v1, thyracont_rs485_v2, erstevak_rs485_v2],
)
def test_descriptors_verify(driver):
    assert verify_driver(driver) is None


def test_descriptors_are_declared_as_entry_points():
    """The declarations are install-time; skip when metadata is stale."""
    from importlib.metadata import entry_points

    declared = {entry.name for entry in entry_points(group=ENTRY_POINT_GROUP)}
    if not declared:
        pytest.skip("installed metadata carries no scietex.modbus.drivers group")
    assert {
        "thyracont_rs485_v1",
        "erstevak_rs485_v1",
        "thyracont_rs485_v2",
        "erstevak_rs485_v2",
    } <= declared
