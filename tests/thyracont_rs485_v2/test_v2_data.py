"""
Tests for the scietex.hal.vacuum_gauge.Thyracont.rs485.v2.data module.

This module tests the V2 protocol data utilities: floating-point string encoding/decoding,
measurement-range decoding, and operating-hours/wear-status response decoding.
"""

import pytest

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import (
        decode_float,
        decode_operating_hours,
        decode_range,
        decode_wear_status,
        encode_float,
        encode_range,
    )
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import (
        decode_float,
        decode_operating_hours,
        decode_range,
        decode_wear_status,
        encode_float,
        encode_range,
    )


# Tests for encode_float
def test_encode_float_typical():
    """Test float encoding for typical values."""
    assert encode_float(123.4) == "1.234e2"
    assert encode_float(1000.0) == "1.000e3"
    assert encode_float(0.00123) == "1.230e-3"


def test_encode_float_zero():
    """Test float encoding for zero."""
    assert encode_float(0.0) == "0.000e0"


# Tests for decode_float
def test_decode_float_valid():
    """Test float decoding with valid strings."""
    assert decode_float("1.234e2") == pytest.approx(123.4)
    assert decode_float("1.000e3") == pytest.approx(1000.0)


def test_decode_float_special():
    """Test float decoding for over/under-range markers."""
    assert decode_float("OR") == 999999.0
    assert decode_float("UR") == 0.0


def test_decode_float_invalid():
    """Test float decoding with invalid inputs."""
    assert decode_float("") is None
    assert decode_float("abc") is None
    assert decode_float(None) is None


# Tests for decode_range
def test_decode_range_valid():
    """Test range decoding with a valid string."""
    result = decode_range("H1.0e3L1.0e-3")
    assert result["high"] == pytest.approx(1000.0)
    assert result["low"] == pytest.approx(0.001)


def test_decode_range_invalid():
    """Test range decoding with invalid inputs."""
    result = decode_range("garbage")
    assert result["high"] is None
    assert result["low"] is None


# Tests for encode_range
def test_encode_range():
    """Test range encoding from a limits dictionary."""
    assert encode_range({"high": 1000.0, "low": 0.001}) == "H1e3L1e-3"


# Tests for decode_operating_hours
def test_decode_operating_hours_gauge_only():
    """Test operating-hours decoding without cathode data."""
    result = decode_operating_hours("1234")
    assert result["gauge"] == pytest.approx(308.5)
    assert result["cathode"] is None


def test_decode_operating_hours_with_cathode():
    """Test operating-hours decoding with cathode data."""
    result = decode_operating_hours("1234C5678")
    assert result["gauge"] == pytest.approx(308.5)
    assert result["cathode"] == pytest.approx(1419.5)


def test_decode_operating_hours_none():
    """Test operating-hours decoding with no data."""
    assert decode_operating_hours(None) is None


# Tests for decode_wear_status
def test_decode_wear_status_pirani():
    """Test wear-status decoding for the Pirani branch (W<int>A<int>)."""
    result = decode_wear_status("W42A100")
    assert result["wear"] == pytest.approx(42.0)
    assert result["status"] == "contamination"
    assert result["hours_since_zero_adjustment"] == pytest.approx(25.0)


def test_decode_wear_status_not_calculated():
    """Test wear-status decoding for the 'not calculated' marker."""
    result = decode_wear_status("W32767A0")
    assert result["status"] == "not calculated"


def test_decode_wear_status_none():
    """Test wear-status decoding with no data."""
    assert decode_wear_status(None) is None


if __name__ == "__main__":
    pytest.main()
