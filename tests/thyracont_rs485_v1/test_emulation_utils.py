"""
Tests for the scietex.hal.vacuum_gauge.Thyracont.rs485.v1.emulation_utils module.

This module tests utility functions for emulating Thyracont RS485 communication, including reading
and writing 32-bit values across register pairs, pressure encoding/decoding, and parsing custom
ASCII commands.
"""

import pytest
from pymodbus.datastore import ModbusDeviceContext, ModbusSequentialDataBlock

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v1.emulation_utils import (
        REG_P,
        REG_SP1,
        REG_SP2,
        REG_CAL1,
        REG_CAL2,
        REG_PENNING_STATE,
        REG_PENNING_SYNC,
        REG_SP_SEL,
        REG_CAL_SEL,
        REG_ATM_SEL,
        REG_ZERO_SEL,
        read_two_regs,
        write_two_regs,
        pressure_from_reg,
        pressure_to_reg,
        parse_command,
    )
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v1.emulation_utils import (
        REG_P,
        REG_SP1,
        REG_SP2,
        REG_CAL1,
        REG_CAL2,
        REG_PENNING_STATE,
        REG_PENNING_SYNC,
        REG_SP_SEL,
        REG_CAL_SEL,
        REG_ATM_SEL,
        REG_ZERO_SEL,
        read_two_regs,
        write_two_regs,
        pressure_from_reg,
        pressure_to_reg,
        parse_command,
    )
from scietex.hal.serial.utilities.numeric import split_32bit, combine_32bit


# Fixture for ModbusSlaveContext
@pytest.fixture
def context():
    """Create a ModbusSlaveContext with initialized holding registers."""
    # Initialize with 14 registers (0-13) to cover all REG_* constants
    data_block = ModbusSequentialDataBlock(0, [0] * 14)
    return ModbusDeviceContext(hr=data_block)


# Tests for read_two_regs
# pylint: disable=redefined-outer-name
def test_read_two_regs(context):
    """Test reading a 32-bit value from two registers."""
    context.store["h"].values[0] = 0x1234  # High 16 bits
    context.store["h"].values[1] = 0x5678  # Low 16 bits
    result = read_two_regs(context, 0)
    assert result == combine_32bit(0x1234, 0x5678)  # 0x12345678


# Tests for write_two_regs
# pylint: disable=redefined-outer-name
def test_write_two_regs(context):
    """Test writing a 32-bit value to two registers."""
    value = 0x12345678
    write_two_regs(context, value, 2)
    high, low = split_32bit(value)
    assert context.store["h"].values[2] == high  # 0x1234
    assert context.store["h"].values[3] == low  # 0x5678


# Tests for pressure_from_reg
# pylint: disable=redefined-outer-name
def test_pressure_from_reg(context):
    """Test reading and decoding a pressure value."""
    p_encoded = int("123417")  # Encodes 1.234e-3 mbar
    high, low = split_32bit(p_encoded)
    context.store["h"].values[REG_P] = high
    context.store["h"].values[REG_P + 1] = low
    pressure = pressure_from_reg(context, REG_P)
    assert pressure == pytest.approx(1.234e-3)


# pylint: disable=redefined-outer-name
def test_pressure_from_reg_zero(context):
    """Test reading a zero pressure value."""
    p_encoded = int("000019")  # Encodes 0.0 mbar
    write_two_regs(context, p_encoded, REG_P)
    pressure = pressure_from_reg(context, REG_P)
    assert pressure == 0.0


# Tests for pressure_to_reg
# pylint: disable=redefined-outer-name
def test_pressure_to_reg(context):
    """Test encoding and writing a pressure value."""
    pressure_to_reg(context, 0.9876, REG_P)
    p_encoded = read_two_regs(context, REG_P)
    assert p_encoded == int("987619")  # Encodes 0.9876 mbar


# pylint: disable=redefined-outer-name
def test_pressure_to_reg_large(context):
    """Test encoding and writing a large pressure value."""
    pressure_to_reg(context, 12.34, REG_P)
    p_encoded = read_two_regs(context, REG_P)
    assert p_encoded == int("123421")  # Encodes 12.34 mbar


# Tests for parse_command
# pylint: disable=redefined-outer-name
def test_parse_command_type(context):
    """Test parsing the 'T' command (gauge type)."""
    response = parse_command(context, "T", "ignored")
    assert response == b"MTM09D"


# pylint: disable=redefined-outer-name
def test_parse_command_read_pressure(context):
    """Test parsing the 'M' command (read pressure)."""
    write_two_regs(context, int("123403"), REG_P)  # 1.23e-3 mbar
    response = parse_command(context, "M", "ignored")
    assert response == b"123403"


# pylint: disable=redefined-outer-name
def test_parse_command_write_pressure(context):
    """Test parsing the 'm' command (write pressure)."""
    parse_command(context, "m", "987620")  # 0.9876 mbar
    p_encoded = read_two_regs(context, REG_P)
    assert p_encoded == int("987620")


# pylint: disable=redefined-outer-name
def test_parse_command_read_setpoint(context):
    """Test parsing the 'S' command (read setpoint)."""
    write_two_regs(context, int("123422"), REG_SP1)  # 12.34 mbar
    response = parse_command(context, "S", "1")
    assert response == b"123422"
    response = parse_command(context, "S", "2")
    assert response == b"000000"  # Default REG_SP2 value


# pylint: disable=redefined-outer-name
def test_parse_command_select_setpoint(context):
    """Test parsing the 's' command (select setpoint)."""
    parse_command(context, "s", "1")
    assert context.store["h"].values[REG_SP_SEL] == 1
    parse_command(context, "s", "2")
    assert context.store["h"].values[REG_SP_SEL] == 2


# pylint: disable=redefined-outer-name
def test_parse_command_write_setpoint(context):
    """Test parsing the 's' command (write selected setpoint)."""
    context.store["h"].values[REG_SP_SEL] = 1
    parse_command(context, "s", "123422")  # 12.34 mbar
    assert read_two_regs(context, REG_SP1) == int("123422")
    assert context.store["h"].values[REG_SP_SEL] == 0  # Cleared after write
    context.store["h"].values[REG_SP_SEL] = 2
    parse_command(context, "s", "123422")  # 12.34 mbar
    assert read_two_regs(context, REG_SP2) == int("123422")
    assert context.store["h"].values[REG_SP_SEL] == 0  # Cleared after write


# pylint: disable=redefined-outer-name
def test_parse_command_read_calibration(context):
    """Test parsing the 'C' command (read calibration)."""
    context.store["h"].values[REG_CAL1] = 123  # 1.23
    response = parse_command(context, "C", "1")
    assert response == b"000123"
    response = parse_command(context, "C", "2")
    assert response == b"000000"  # Default REG_CAL2 value


# pylint: disable=redefined-outer-name
def test_parse_command_select_calibration(context):
    """Test parsing the 'c' command (select calibration)."""
    parse_command(context, "c", "1")
    assert context.store["h"].values[REG_CAL_SEL] == 1
    parse_command(context, "c", "2")
    assert context.store["h"].values[REG_CAL_SEL] == 2


# pylint: disable=redefined-outer-name
def test_parse_command_write_calibration(context):
    """Test parsing the 'c' command (write selected calibration)."""
    context.store["h"].values[REG_CAL_SEL] = 2
    parse_command(context, "c", "99")  # 0.99
    assert context.store["h"].values[REG_CAL2] == 99
    assert context.store["h"].values[REG_CAL_SEL] == 0  # Cleared after write


# pylint: disable=redefined-outer-name
def test_parse_command_read_penning_state(context):
    """Test parsing the 'I' command (read Penning state)."""
    context.store["h"].values[REG_PENNING_STATE] = 1
    response = parse_command(context, "I", "ignored")
    assert response == b"000001"


# pylint: disable=redefined-outer-name
def test_parse_command_write_penning_state(context):
    """Test parsing the 'i' command (write Penning state)."""
    parse_command(context, "i", "2")
    assert context.store["h"].values[REG_PENNING_STATE] == 2


# pylint: disable=redefined-outer-name
def test_parse_command_read_penning_sync(context):
    """Test parsing the 'W' command (read Penning sync)."""
    context.store["h"].values[REG_PENNING_SYNC] = 42
    response = parse_command(context, "W", "ignored")
    assert response == b"000042"


# pylint: disable=redefined-outer-name
def test_parse_command_write_penning_sync(context):
    """Test parsing the 'w' command (write Penning sync)."""
    parse_command(context, "w", "15")
    assert context.store["h"].values[REG_PENNING_SYNC] == 15


# pylint: disable=redefined-outer-name
def test_parse_command_toggle_atmosphere(context):
    """Test parsing the 'j' command (toggle atmosphere adjustment)."""
    parse_command(context, "j", "1")
    assert context.store["h"].values[REG_ATM_SEL] == 1
    assert context.store["h"].values[REG_ZERO_SEL] == 0


# pylint: disable=redefined-outer-name
def test_parse_command_toggle_zero(context):
    """Test parsing the 'j' command (toggle zero adjustment)."""
    parse_command(context, "j", "0")
    assert context.store["h"].values[REG_ZERO_SEL] == 1
    assert context.store["h"].values[REG_ATM_SEL] == 0


# pylint: disable=redefined-outer-name
def test_parse_command_apply_atmosphere(context):
    """Test parsing the 'j' command (apply atmosphere adjustment)."""
    parse_command(context, "j", "1")
    assert context.store["h"].values[REG_ATM_SEL] == 1
    assert context.store["h"].values[REG_ZERO_SEL] == 0
    response = parse_command(context, "j", "100023")  # Valid adjustment value
    assert response == b"100023"
    parse_command(context, "j", "1")
    assert context.store["h"].values[REG_ATM_SEL] == 1
    assert context.store["h"].values[REG_ZERO_SEL] == 0
    response = parse_command(context, "j", "123456")  # Invalid adjustment value
    assert response == b""


# pylint: disable=redefined-outer-name
def test_parse_command_apply_zero(context):
    """Test parsing the 'j' command (apply zero adjustment)."""
    parse_command(context, "j", "0")
    assert context.store["h"].values[REG_ATM_SEL] == 0
    assert context.store["h"].values[REG_ZERO_SEL] == 1
    response = parse_command(context, "j", "000000")  # Valid zero value
    assert response == b"000000"
    parse_command(context, "j", "0")
    assert context.store["h"].values[REG_ATM_SEL] == 0
    assert context.store["h"].values[REG_ZERO_SEL] == 1
    response = parse_command(context, "j", "123456")  # Invalid zero value
    assert response == b""


if __name__ == "__main__":
    pytest.main()
