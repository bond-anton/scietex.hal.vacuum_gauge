"""
Tests for the scietex.hal.vacuum_gauge.thyracont.rs485.v1.translator module.

This module tests the `ThyracontV1Translator` gateway plugin, ensuring standard Modbus requests
(FC03/FC06/FC16) map onto the correct Thyracont V1 vendor commands and that vendor responses map
back into the correct standard Modbus responses, without any serial I/O.
"""

import pytest

# pylint: disable=ungrouped-imports
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersRequest,
    ReadHoldingRegistersResponse,
    ReadInputRegistersRequest,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)
from scietex.hal.serial.gateway import GatewayError

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v1.request import ThyracontRequest
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v1.translator import (
        ThyracontV1Translator,
    )
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v1.request import ThyracontRequest
    from scietex.hal.vacuum_gauge.thyracont.rs485.v1.translator import (
        ThyracontV1Translator,
    )


@pytest.fixture
def translator():
    """Create a fresh translator instance."""
    return ThyracontV1Translator()


# -- FC03 reads -------------------------------------------------------------


# pylint: disable=redefined-outer-name
def test_read_pressure(translator):
    """FC03 read of pressure (addr 0, count 2) maps to the 'M' command."""
    request = ReadHoldingRegistersRequest(address=0, count=2)
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "M"
    assert vendor.data == ""

    response = ThyracontRequest(command="M", data=b"001234")
    standard = translator.to_standard(response)
    assert isinstance(standard, ReadHoldingRegistersResponse)
    assert standard.registers == [1234, 0]


# pylint: disable=redefined-outer-name
def test_read_setpoint_one(translator):
    """FC03 read of SP1 (addr 2, count 2) maps to 'S' + '1'."""
    request = ReadHoldingRegistersRequest(address=2, count=2)
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "S"
    assert vendor.data == "1"


# pylint: disable=redefined-outer-name
def test_read_setpoint_two(translator):
    """FC03 read of SP2 (addr 4, count 2) maps to 'S' + '2'."""
    request = ReadHoldingRegistersRequest(address=4, count=2)
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "S"
    assert vendor.data == "2"


# pylint: disable=redefined-outer-name
def test_read_calibration_one(translator):
    """FC03 read of CAL1 (addr 6, count 1) maps to 'C' + '1' and decodes one register."""
    request = ReadHoldingRegistersRequest(address=6, count=1)
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "C"
    assert vendor.data == "1"

    response = ThyracontRequest(command="C", data=b"000123")
    standard = translator.to_standard(response)
    assert isinstance(standard, ReadHoldingRegistersResponse)
    assert standard.registers == [123]


# pylint: disable=redefined-outer-name
def test_read_calibration_two(translator):
    """FC03 read of CAL2 (addr 7, count 1) maps to 'C' + '2'."""
    request = ReadHoldingRegistersRequest(address=7, count=1)
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "C"
    assert vendor.data == "2"


# pylint: disable=redefined-outer-name
def test_read_penning_state(translator):
    """FC03 read of Penning state (addr 8, count 1) maps to the 'I' command."""
    request = ReadHoldingRegistersRequest(address=8, count=1)
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "I"
    assert vendor.data == ""


# pylint: disable=redefined-outer-name
def test_read_penning_sync(translator):
    """FC03 read of Penning sync (addr 9, count 1) maps to the 'W' command."""
    request = ReadHoldingRegistersRequest(address=9, count=1)
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "W"
    assert vendor.data == ""


# -- writes -----------------------------------------------------------------


# pylint: disable=redefined-outer-name
def test_write_pressure(translator):
    """FC06 write of pressure (addr 0, 2 regs) maps to 'm' with a 6-digit payload."""
    request = WriteSingleRegisterRequest(address=0, registers=[1234, 0])
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "m"
    assert vendor.data == "001234"


# pylint: disable=redefined-outer-name
def test_write_setpoint_select(translator):
    """FC06 write of SP select (addr 10, value 1) maps to 's' + '1'."""
    request = WriteSingleRegisterRequest(address=10, registers=[1])
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "s"
    assert vendor.data == "1"


# pylint: disable=redefined-outer-name
def test_write_setpoint_value(translator):
    """FC06 write of SP value (addr 11, 2 regs) maps to 's' with a 6-digit payload."""
    request = WriteSingleRegisterRequest(address=11, registers=[1234, 0])
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "s"
    assert vendor.data == "001234"


# pylint: disable=redefined-outer-name
def test_write_calibration_select(translator):
    """FC06 write of CAL select (addr 12, value 2) maps to 'c' + '2'."""
    request = WriteSingleRegisterRequest(address=12, registers=[2])
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "c"
    assert vendor.data == "2"


# pylint: disable=redefined-outer-name
def test_write_calibration_value(translator):
    """FC06 write of CAL value (addr 13, 2 regs) maps to 'c' with a 6-digit payload."""
    request = WriteSingleRegisterRequest(address=13, registers=[1234, 0])
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "c"
    assert vendor.data == "001234"


# pylint: disable=redefined-outer-name
def test_write_penning_state(translator):
    """FC06 write of Penning state (addr 8) maps to 'i' with the raw value."""
    request = WriteSingleRegisterRequest(address=8, registers=[1])
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "i"
    assert vendor.data == "1"


# pylint: disable=redefined-outer-name
def test_write_penning_sync(translator):
    """FC06 write of Penning sync (addr 9) maps to 'w' with the raw value."""
    request = WriteSingleRegisterRequest(address=9, registers=[1])
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "w"
    assert vendor.data == "1"


# pylint: disable=redefined-outer-name
def test_write_multiple_pressure(translator):
    """FC16 write of pressure (addr 0, 2 regs) maps to 'm' with a 6-digit payload."""
    request = WriteMultipleRegistersRequest(address=0, registers=[1234, 0])
    vendor = translator.to_vendor(request)
    assert isinstance(vendor, ThyracontRequest)
    assert vendor.command == "m"
    assert vendor.data == "001234"


# -- to_standard for writes -------------------------------------------------


# pylint: disable=redefined-outer-name
def test_to_standard_write_single(translator):
    """FC06 write produces a WriteSingleRegisterResponse echoing the value."""
    translator.to_vendor(WriteSingleRegisterRequest(address=8, registers=[1]))
    standard = translator.to_standard(ThyracontRequest(command="i", data=b"1"))
    assert isinstance(standard, WriteSingleRegisterResponse)
    assert standard.address == 8
    assert standard.registers == [1]


# pylint: disable=redefined-outer-name
def test_to_standard_write_multiple(translator):
    """FC16 write produces a WriteMultipleRegistersResponse echoing the count."""
    translator.to_vendor(WriteMultipleRegistersRequest(address=0, registers=[1234, 0]))
    standard = translator.to_standard(ThyracontRequest(command="m", data=b"001234"))
    assert isinstance(standard, WriteMultipleRegistersResponse)
    assert standard.address == 0
    assert standard.count == 2


# -- error paths ------------------------------------------------------------


# pylint: disable=redefined-outer-name
def test_unsupported_request_type(translator):
    """A non-FC03/FC06/FC16 request raises GatewayError."""
    request = ReadInputRegistersRequest(address=0, count=2)
    with pytest.raises(GatewayError):
        translator.to_vendor(request)


# pylint: disable=redefined-outer-name
def test_read_unsupported_address(translator):
    """An unlisted read address raises GatewayError."""
    with pytest.raises(GatewayError):
        translator.to_vendor(ReadHoldingRegistersRequest(address=99, count=2))


# pylint: disable=redefined-outer-name
def test_write_unsupported_address(translator):
    """An unlisted write address raises GatewayError."""
    with pytest.raises(GatewayError):
        translator.to_vendor(WriteSingleRegisterRequest(address=99, registers=[1]))


# pylint: disable=redefined-outer-name
def test_read_wrong_count(translator):
    """A 32-bit read with count 1 raises GatewayError."""
    with pytest.raises(GatewayError):
        translator.to_vendor(ReadHoldingRegistersRequest(address=0, count=1))


# pylint: disable=redefined-outer-name
def test_read_wrong_count_16bit(translator):
    """A 16-bit read with count 2 raises GatewayError."""
    with pytest.raises(GatewayError):
        translator.to_vendor(ReadHoldingRegistersRequest(address=8, count=2))


# pylint: disable=redefined-outer-name
def test_write_pressure_wrong_count(translator):
    """A 32-bit write with one register raises GatewayError."""
    with pytest.raises(GatewayError):
        translator.to_vendor(WriteSingleRegisterRequest(address=0, registers=[1234]))


# pylint: disable=redefined-outer-name
def test_write_penning_wrong_count(translator):
    """A 16-bit write with two registers raises GatewayError."""
    with pytest.raises(GatewayError):
        translator.to_vendor(WriteSingleRegisterRequest(address=8, registers=[1, 2]))


# pylint: disable=redefined-outer-name
def test_write_select_invalid_value(translator):
    """A select register written with a value other than 1 or 2 raises GatewayError."""
    with pytest.raises(GatewayError):
        translator.to_vendor(WriteSingleRegisterRequest(address=10, registers=[3]))


# pylint: disable=redefined-outer-name
def test_to_standard_without_pending(translator):
    """to_standard without a preceding to_vendor raises GatewayError."""
    with pytest.raises(GatewayError):
        translator.to_standard(ThyracontRequest(command="M", data=b"001234"))


# pylint: disable=redefined-outer-name
def test_to_standard_non_thyracont(translator):
    """to_standard with a non-Thyracont response raises GatewayError."""
    translator.to_vendor(ReadHoldingRegistersRequest(address=0, count=2))
    with pytest.raises(GatewayError):
        translator.to_standard(ReadHoldingRegistersResponse(registers=[0, 0]))


# pylint: disable=redefined-outer-name
def test_to_standard_empty_response(translator):
    """to_standard with an empty vendor response raises GatewayError."""
    translator.to_vendor(ReadHoldingRegistersRequest(address=0, count=2))
    with pytest.raises(GatewayError):
        translator.to_standard(ThyracontRequest(command="M"))


# pylint: disable=redefined-outer-name
def test_to_standard_malformed_response(translator):
    """to_standard with a non-numeric vendor response raises GatewayError."""
    translator.to_vendor(ReadHoldingRegistersRequest(address=0, count=2))
    with pytest.raises(GatewayError):
        translator.to_standard(ThyracontRequest(command="M", data=b"abc123"))


if __name__ == "__main__":
    pytest.main()
