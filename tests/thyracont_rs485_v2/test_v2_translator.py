"""
Tests for the scietex.hal.vacuum_gauge.thyracont.rs485.v2.translator module.

This module tests the ThyracontV2Translator gateway plugin: mapping standard
Modbus FC03 reads onto Thyracont V2 vendor commands and mapping ASCII vendor
responses back into two-register float32 responses.
"""

import struct

import pytest
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersRequest,
    ReadHoldingRegistersResponse,
    WriteSingleRegisterRequest,
)

# pylint: disable=ungrouped-imports
from scietex.hal.serial.gateway import GatewayError

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import AccessCode
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.request import ThyracontRequest
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.translator import ThyracontV2Translator
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import AccessCode
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.request import ThyracontRequest
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.translator import ThyracontV2Translator


def _registers_to_float(registers: list[int]) -> float:
    """Reassemble a big-endian two-register float32 value."""
    high, low = registers
    return struct.unpack(">f", struct.pack(">HH", high, low))[0]


def _vendor_response(data: str) -> ThyracontRequest:
    """Build a fake successful (STREAMING) vendor response for the given data."""
    return ThyracontRequest(access_code=AccessCode.STREAMING, command="MV", data=data.encode())


# Tests for to_vendor
def test_to_vendor_pressure():
    """An FC03 read of address 0 maps to the 'MV' command."""
    translator = ThyracontV2Translator()
    request = ReadHoldingRegistersRequest(address=0, count=2)
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "MV"
    assert vendor.function_code == AccessCode.READ.value
    assert vendor.data == ""


def test_to_vendor_operating_hours():
    """An FC03 read of address 2 maps to the 'OH' command."""
    translator = ThyracontV2Translator()
    request = ReadHoldingRegistersRequest(address=2, count=2)
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "OH"


def test_to_vendor_wear():
    """An FC03 read of address 6 maps to 'PM' with Pirani sensor data."""
    translator = ThyracontV2Translator()
    request = ReadHoldingRegistersRequest(address=6, count=2)
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "PM"
    assert vendor.data == "1"


# Tests for to_standard
def test_to_standard_pressure():
    """A pressure response is returned as two float32 registers."""
    translator = ThyracontV2Translator()
    translator.to_vendor(ReadHoldingRegistersRequest(address=0, count=2))
    response = translator.to_standard(_vendor_response("1.234e2"))
    assert isinstance(response, ReadHoldingRegistersResponse)
    assert len(response.registers) == 2
    assert _registers_to_float(response.registers) == pytest.approx(123.4)


def test_to_standard_operating_hours():
    """A gauge operating-hours response decodes to hours (divided by 4)."""
    translator = ThyracontV2Translator()
    translator.to_vendor(ReadHoldingRegistersRequest(address=2, count=2))
    response = translator.to_standard(_vendor_response("400"))
    assert isinstance(response, ReadHoldingRegistersResponse)
    assert _registers_to_float(response.registers) == pytest.approx(100.0)


def test_to_standard_cathode_hours():
    """A cathode operating-hours response decodes the cathode field."""
    translator = ThyracontV2Translator()
    translator.to_vendor(ReadHoldingRegistersRequest(address=4, count=2))
    response = translator.to_standard(_vendor_response("400C800"))
    assert isinstance(response, ReadHoldingRegistersResponse)
    assert _registers_to_float(response.registers) == pytest.approx(200.0)


def test_to_standard_wear():
    """A Pirani wear response decodes the wear percentage."""
    translator = ThyracontV2Translator()
    translator.to_vendor(ReadHoldingRegistersRequest(address=6, count=2))
    response = translator.to_standard(_vendor_response("W100A400"))
    assert isinstance(response, ReadHoldingRegistersResponse)
    assert _registers_to_float(response.registers) == pytest.approx(100.0)


def test_to_standard_hours_since_zero():
    """A Pirani wear response decodes the hours-since-zero-adjustment field."""
    translator = ThyracontV2Translator()
    translator.to_vendor(ReadHoldingRegistersRequest(address=8, count=2))
    response = translator.to_standard(_vendor_response("W100A400"))
    assert isinstance(response, ReadHoldingRegistersResponse)
    assert _registers_to_float(response.registers) == pytest.approx(100.0)


# Tests for error handling
def test_unsupported_address():
    """Reading an unsupported address raises GatewayError."""
    translator = ThyracontV2Translator()
    request = ReadHoldingRegistersRequest(address=99, count=2)
    with pytest.raises(GatewayError):
        translator.to_vendor(request)


def test_wrong_count():
    """Reading a supported address with a non-two register count raises GatewayError."""
    translator = ThyracontV2Translator()
    request = ReadHoldingRegistersRequest(address=0, count=1)
    with pytest.raises(GatewayError):
        translator.to_vendor(request)


def test_unsupported_request_type():
    """A non-FC03 request (write) raises GatewayError."""
    translator = ThyracontV2Translator()
    request = WriteSingleRegisterRequest(address=0, registers=[1])
    with pytest.raises(GatewayError):
        translator.to_vendor(request)


def test_error_response():
    """A vendor ERROR response raises GatewayError."""
    translator = ThyracontV2Translator()
    translator.to_vendor(ReadHoldingRegistersRequest(address=0, count=2))
    response = ThyracontRequest(access_code=AccessCode.ERROR, command="MV", data=b"SYNTAX")
    with pytest.raises(GatewayError):
        translator.to_standard(response)


def test_malformed_response():
    """A malformed vendor response raises GatewayError."""
    translator = ThyracontV2Translator()
    translator.to_vendor(ReadHoldingRegistersRequest(address=0, count=2))
    with pytest.raises(GatewayError):
        translator.to_standard(_vendor_response("not-a-float"))


if __name__ == "__main__":
    pytest.main()
