"""
Tests for the scietex.hal.vacuum_gauge.Thyracont.rs485.v1.emulation_utils module.

This module tests utility functions for emulating Thyracont RS485 communication, including reading
and writing 32-bit values across register pairs, pressure encoding/decoding, and parsing custom
ASCII commands.
"""

import pytest

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v1.emulation_utils import (
        REG_ATM_SEL,
        REG_CAL1,
        REG_CAL2,
        REG_CAL_SEL,
        REG_P,
        REG_PENNING_STATE,
        REG_PENNING_SYNC,
        REG_SP1,
        REG_SP2,
        REG_SP_SEL,
        REG_ZERO_SEL,
        parse_command,
        pressure_from_reg,
        pressure_to_reg,
        read_two_regs,
        write_two_regs,
    )
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v1.emulation_utils import (
        REG_ATM_SEL,
        REG_CAL1,
        REG_CAL2,
        REG_CAL_SEL,
        REG_P,
        REG_PENNING_STATE,
        REG_PENNING_SYNC,
        REG_SP1,
        REG_SP2,
        REG_SP_SEL,
        REG_ZERO_SEL,
        parse_command,
        pressure_from_reg,
        pressure_to_reg,
        read_two_regs,
        write_two_regs,
    )
from scietex.hal.serial.utilities.numeric import combine_32bit, split_32bit


# Fixture for the register store
@pytest.fixture
def store():
    """Create a plain list of 14 holding-register values."""
    return [0] * 14


# Tests for read_two_regs
# pylint: disable=redefined-outer-name
def test_read_two_regs(store):
    """Test reading a 32-bit value from two registers."""
    store[0] = 0x1234  # High 16 bits
    store[1] = 0x5678  # Low 16 bits
    result = read_two_regs(store, 0)
    assert result == combine_32bit(0x1234, 0x5678)  # 0x12345678


# Tests for write_two_regs
# pylint: disable=redefined-outer-name
def test_write_two_regs(store):
    """Test writing a 32-bit value to two registers."""
    value = 0x12345678
    write_two_regs(store, value, 2)
    high, low = split_32bit(value)
    assert store[2] == high  # 0x1234
    assert store[3] == low  # 0x5678


# Tests for pressure_from_reg
# pylint: disable=redefined-outer-name
def test_pressure_from_reg(store):
    """Test reading and decoding a pressure value."""
    p_encoded = int("123417")  # Encodes 1.234e-3 mbar
    high, low = split_32bit(p_encoded)
    store[REG_P] = high
    store[REG_P + 1] = low
    pressure = pressure_from_reg(store, REG_P)
    assert pressure == pytest.approx(1.234e-3)


# pylint: disable=redefined-outer-name
def test_pressure_from_reg_zero(store):
    """Test reading a zero pressure value."""
    p_encoded = int("000019")  # Encodes 0.0 mbar
    write_two_regs(store, p_encoded, REG_P)
    pressure = pressure_from_reg(store, REG_P)
    assert pressure == 0.0


# Tests for pressure_to_reg
# pylint: disable=redefined-outer-name
def test_pressure_to_reg(store):
    """Test encoding and writing a pressure value."""
    pressure_to_reg(store, 0.9876, REG_P)
    p_encoded = read_two_regs(store, REG_P)
    assert p_encoded == int("987619")  # Encodes 0.9876 mbar


# pylint: disable=redefined-outer-name
def test_pressure_to_reg_large(store):
    """Test encoding and writing a large pressure value."""
    pressure_to_reg(store, 12.34, REG_P)
    p_encoded = read_two_regs(store, REG_P)
    assert p_encoded == int("123421")  # Encodes 12.34 mbar


# Tests for parse_command
# pylint: disable=redefined-outer-name
def test_parse_command_type(store):
    """Test parsing the 'T' command (gauge type)."""
    response = parse_command(store, "T", "ignored")
    assert response == b"MTM09D"


# pylint: disable=redefined-outer-name
def test_parse_command_read_pressure(store):
    """Test parsing the 'M' command (read pressure)."""
    write_two_regs(store, int("123403"), REG_P)  # 1.23e-3 mbar
    response = parse_command(store, "M", "ignored")
    assert response == b"123403"


# pylint: disable=redefined-outer-name
def test_parse_command_write_pressure(store):
    """Test parsing the 'm' command (write pressure)."""
    parse_command(store, "m", "987620")  # 0.9876 mbar
    p_encoded = read_two_regs(store, REG_P)
    assert p_encoded == int("987620")


# pylint: disable=redefined-outer-name
def test_parse_command_read_setpoint(store):
    """Test parsing the 'S' command (read setpoint)."""
    write_two_regs(store, int("123422"), REG_SP1)  # 12.34 mbar
    response = parse_command(store, "S", "1")
    assert response == b"123422"
    response = parse_command(store, "S", "2")
    assert response == b"000000"  # Default REG_SP2 value


# pylint: disable=redefined-outer-name
def test_parse_command_select_setpoint(store):
    """Test parsing the 's' command (select setpoint)."""
    parse_command(store, "s", "1")
    assert store[REG_SP_SEL] == 1
    parse_command(store, "s", "2")
    assert store[REG_SP_SEL] == 2


# pylint: disable=redefined-outer-name
def test_parse_command_write_setpoint(store):
    """Test parsing the 's' command (write selected setpoint)."""
    store[REG_SP_SEL] = 1
    parse_command(store, "s", "123422")  # 12.34 mbar
    assert read_two_regs(store, REG_SP1) == int("123422")
    assert store[REG_SP_SEL] == 0  # Cleared after write
    store[REG_SP_SEL] = 2
    parse_command(store, "s", "123422")  # 12.34 mbar
    assert read_two_regs(store, REG_SP2) == int("123422")
    assert store[REG_SP_SEL] == 0  # Cleared after write


# pylint: disable=redefined-outer-name
def test_parse_command_read_calibration(store):
    """Test parsing the 'C' command (read calibration)."""
    store[REG_CAL1] = 123  # 1.23
    response = parse_command(store, "C", "1")
    assert response == b"000123"
    response = parse_command(store, "C", "2")
    assert response == b"000000"  # Default REG_CAL2 value


# pylint: disable=redefined-outer-name
def test_parse_command_select_calibration(store):
    """Test parsing the 'c' command (select calibration)."""
    parse_command(store, "c", "1")
    assert store[REG_CAL_SEL] == 1
    parse_command(store, "c", "2")
    assert store[REG_CAL_SEL] == 2


# pylint: disable=redefined-outer-name
def test_parse_command_write_calibration(store):
    """Test parsing the 'c' command (write selected calibration)."""
    store[REG_CAL_SEL] = 2
    parse_command(store, "c", "99")  # 0.99
    assert store[REG_CAL2] == 99
    assert store[REG_CAL_SEL] == 0  # Cleared after write


# pylint: disable=redefined-outer-name
def test_parse_command_write_cal1_does_not_clobber_cal2(store):
    """Writing CAL1 must not overwrite CAL2 or the Penning-state register."""
    store[REG_CAL1] = 111
    store[REG_CAL2] = 222
    store[REG_PENNING_STATE] = 333
    store[REG_CAL_SEL] = 1
    parse_command(store, "c", "123")
    assert store[REG_CAL1] == 123
    assert store[REG_CAL2] == 222  # Unchanged
    assert store[REG_PENNING_STATE] == 333  # Unchanged


# pylint: disable=redefined-outer-name
def test_parse_command_write_cal2_does_not_clobber_penning(store):
    """Writing CAL2 must not overwrite the Penning-state register."""
    store[REG_CAL1] = 111
    store[REG_CAL2] = 222
    store[REG_PENNING_STATE] = 333
    store[REG_CAL_SEL] = 2
    parse_command(store, "c", "99")
    assert store[REG_CAL1] == 111  # Unchanged
    assert store[REG_CAL2] == 99
    assert store[REG_PENNING_STATE] == 333  # Unchanged


# pylint: disable=redefined-outer-name
def test_parse_command_read_penning_state(store):
    """Test parsing the 'I' command (read Penning state)."""
    store[REG_PENNING_STATE] = 1
    response = parse_command(store, "I", "ignored")
    assert response == b"000001"


# pylint: disable=redefined-outer-name
def test_parse_command_write_penning_state(store):
    """Test parsing the 'i' command (write Penning state)."""
    parse_command(store, "i", "2")
    assert store[REG_PENNING_STATE] == 2


# pylint: disable=redefined-outer-name
def test_parse_command_read_penning_sync(store):
    """Test parsing the 'W' command (read Penning sync)."""
    store[REG_PENNING_SYNC] = 42
    response = parse_command(store, "W", "ignored")
    assert response == b"000042"


# pylint: disable=redefined-outer-name
def test_parse_command_write_penning_sync(store):
    """Test parsing the 'w' command (write Penning sync)."""
    parse_command(store, "w", "15")
    assert store[REG_PENNING_SYNC] == 15


# pylint: disable=redefined-outer-name
def test_parse_command_toggle_atmosphere(store):
    """Test parsing the 'j' command (toggle atmosphere adjustment)."""
    parse_command(store, "j", "1")
    assert store[REG_ATM_SEL] == 1
    assert store[REG_ZERO_SEL] == 0


# pylint: disable=redefined-outer-name
def test_parse_command_toggle_zero(store):
    """Test parsing the 'j' command (toggle zero adjustment)."""
    parse_command(store, "j", "0")
    assert store[REG_ZERO_SEL] == 1
    assert store[REG_ATM_SEL] == 0


# pylint: disable=redefined-outer-name
def test_parse_command_apply_atmosphere(store):
    """Test parsing the 'j' command (apply atmosphere adjustment)."""
    parse_command(store, "j", "1")
    assert store[REG_ATM_SEL] == 1
    assert store[REG_ZERO_SEL] == 0
    response = parse_command(store, "j", "100023")  # Valid adjustment value
    assert response == b"100023"
    parse_command(store, "j", "1")
    assert store[REG_ATM_SEL] == 1
    assert store[REG_ZERO_SEL] == 0
    response = parse_command(store, "j", "123456")  # Invalid adjustment value
    assert response == b""


# pylint: disable=redefined-outer-name
def test_parse_command_apply_zero(store):
    """Test parsing the 'j' command (apply zero adjustment)."""
    parse_command(store, "j", "0")
    assert store[REG_ATM_SEL] == 0
    assert store[REG_ZERO_SEL] == 1
    response = parse_command(store, "j", "000000")  # Valid zero value
    assert response == b"000000"
    parse_command(store, "j", "0")
    assert store[REG_ATM_SEL] == 0
    assert store[REG_ZERO_SEL] == 1
    response = parse_command(store, "j", "123456")  # Invalid zero value
    assert response == b""


if __name__ == "__main__":
    pytest.main()
