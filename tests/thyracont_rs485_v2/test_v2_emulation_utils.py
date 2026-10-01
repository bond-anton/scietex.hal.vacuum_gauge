"""
Tests for the scietex.hal.vacuum_gauge.Thyracont.rs485.v2.emulation_utils module.

This module tests the emulated device state dataclass and the V2 command parser.
"""

import pytest

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation_utils import (
        ThyracontV2State,
        parse_command,
    )
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation_utils import (
        ThyracontV2State,
        parse_command,
    )


@pytest.fixture
def state():
    """Create a default emulated device state."""
    return ThyracontV2State()


# Tests for ThyracontV2State defaults
def test_state_defaults():
    """Test the default values of the emulated device state."""
    default_state = ThyracontV2State()
    assert default_state.pressure == 1000.0
    assert default_state.gauge_hours == 0.0
    assert default_state.cathode_hours is None
    assert default_state.wear == 0.0
    assert default_state.hours_since_zero_adjustment == 0.0
    assert default_state.model == "MTM9D"
    assert default_state.product_name == "Thyracont MTM9D"


# Tests for parse_command
# pylint: disable=redefined-outer-name
def test_parse_command_pressure(state):
    """Test parsing the 'MV' command (read pressure)."""
    state.pressure = 1000.0
    assert parse_command(state, "MV", "") == "1.000e3"


# pylint: disable=redefined-outer-name
def test_parse_command_pressure_sensor(state):
    """Test parsing the per-sensor pressure commands."""
    state.pressure = 1.23
    assert parse_command(state, "M1", "") == "1.230e0"


# pylint: disable=redefined-outer-name
def test_parse_command_operating_hours_gauge(state):
    """Test parsing the 'OH' command without a cathode."""
    state.gauge_hours = 100.0
    assert parse_command(state, "OH", "") == "400"


# pylint: disable=redefined-outer-name
def test_parse_command_operating_hours_cathode(state):
    """Test parsing the 'OH' command with a cathode."""
    state.gauge_hours = 100.0
    state.cathode_hours = 2.5
    assert parse_command(state, "OH", "") == "400C10"


# pylint: disable=redefined-outer-name
def test_parse_command_wear_status(state):
    """Test parsing the 'PM' command for the Pirani branch."""
    state.wear = 42.0
    state.hours_since_zero_adjustment = 100.0
    assert parse_command(state, "PM", "1") == "W42A400"


# pylint: disable=redefined-outer-name
def test_parse_command_wear_status_unsupported_sensor(state):
    """Test that 'PM' with unsupported data raises ValueError."""
    with pytest.raises(ValueError):
        parse_command(state, "PM", "3")


# pylint: disable=redefined-outer-name
def test_parse_command_identification(state):
    """Test parsing the identification commands."""
    assert parse_command(state, "TD", "") == "MTM9D"
    assert parse_command(state, "PN", "") == "Thyracont MTM9D"
    assert parse_command(state, "SD", "") == "00000000"
    assert parse_command(state, "SH", "") == "00000000"
    assert parse_command(state, "VD", "") == "1.0"
    assert parse_command(state, "VF", "") == "1.0"
    assert parse_command(state, "VB", "") == "1.0"


# pylint: disable=redefined-outer-name
def test_parse_command_measurement_range(state):
    """Test parsing the 'MR' command."""
    assert parse_command(state, "MR", "") == "H1.0e3L1.0e-3"


# pylint: disable=redefined-outer-name
def test_parse_command_unsupported(state):
    """Test that an unknown command raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported command: XX"):
        parse_command(state, "XX", "")


if __name__ == "__main__":
    pytest.main()
