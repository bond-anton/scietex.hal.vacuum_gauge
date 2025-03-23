"""
Tests for the scietex.hal.vacuum_gauge.Thyracont.rs485.v1.data module.

This module tests the utility functions for encoding and decoding pressure and calibration data
in the Thyracont RS485 protocol, ensuring correct mantissa/exponent calculation, pressure string
formatting, and calibration value conversion.
"""

from decimal import Decimal
from numpy.testing import assert_almost_equal
import pytest

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v1.data import (
        f_exp,
        f_man,
        _pressure_encode,
        _pressure_decode,
        _calibration_encode,
        _calibration_decode,
    )
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v1.data import (
        f_exp,
        f_man,
        _pressure_encode,
        _pressure_decode,
        _calibration_encode,
        _calibration_decode,
    )


# Tests for f_exp
def test_f_exp_positive():
    """Test exponent calculation for positive numbers."""
    assert f_exp(123.45) == 2  # 1.2345e2
    assert f_exp(0.00123) == -3  # 1.23e-3
    assert f_exp(1.0) == 0  # 1.0e0
    assert f_exp(1000.0) == 3  # 1.0e3


def test_f_exp_zero():
    """Test exponent calculation for zero."""
    assert f_exp(0.0) == 0  # 0.0e0, but Decimal gives -1 due to normalization


def test_f_exp_invalid():
    """Test exponent calculation with invalid input."""
    with pytest.raises(ValueError, match="Invalid argument inf in f_exp function"):
        f_exp(float("inf"))
    with pytest.raises(ValueError, match="Invalid argument nan in f_exp function"):
        f_exp(float("nan"))


# Tests for f_man
def test_f_man_positive():
    """Test mantissa calculation for positive numbers."""
    assert_almost_equal(f_man(123.45), Decimal("1.2345"))
    assert_almost_equal(f_man(0.00123), Decimal("1.23"))
    assert_almost_equal(f_man(1.0), Decimal("1"))
    assert_almost_equal(f_man(1000.0), Decimal("1"))


def test_f_man_zero():
    """Test mantissa calculation for zero."""
    assert f_man(0.0) == Decimal("0")


def test_f_man_invalid():
    """Test mantissa calculation with invalid input."""
    with pytest.raises(ValueError):  # Raised by f_exp
        f_man(float("inf"))
    with pytest.raises(ValueError):
        f_man(float("nan"))


# Tests for _pressure_encode
def test_pressure_encode_typical():
    """Test pressure encoding for typical vacuum pressures."""
    assert _pressure_encode(1.23e-3) == "123017"
    assert _pressure_encode(0.9876) == "987619"
    assert _pressure_encode(12.34) == "123421"


def test_pressure_encode_edge_cases():
    """Test pressure encoding for edge cases."""
    assert _pressure_encode(0.0) == "000020"  # 0.0e0, mantissa = 0000, exp = -1 + 20 = 19
    assert _pressure_encode(9999.0) == "999923"  # 9.999e3, exp = 3 + 20 = 23


def test_pressure_encode_invalid():
    """Test pressure encoding with invalid input."""
    with pytest.raises(ValueError):  # Raised by f_exp
        _pressure_encode(float("inf"))
    with pytest.raises(ValueError):
        _pressure_encode(float("nan"))


# Tests for _pressure_decode
def test_pressure_decode_valid():
    """Test pressure decoding with valid strings."""
    assert _pressure_decode("123417") == pytest.approx(1.234e-3)  # 1234 * 10^(3-23)
    assert _pressure_decode("987619") == pytest.approx(0.9876)  # 9876 * 10^(20-23)
    assert _pressure_decode("123421") == pytest.approx(12.34)  # 1234 * 10^(22-23)


def test_pressure_decode_zero():
    """Test pressure decoding for zero."""
    assert _pressure_decode("000019") == 0.0  # 0000 * 10^(19-23)


def test_pressure_decode_invalid():
    """Test pressure decoding with invalid inputs."""
    assert _pressure_decode("abc123") is None  # Non-numeric
    assert _pressure_decode("12345") is None  # Too short
    assert _pressure_decode("1234567") is None  # Too long
    assert _pressure_decode("") is None  # Empty
    assert _pressure_decode(None) is None  # None


# Tests for _calibration_encode
def test_calibration_encode_typical():
    """Test calibration encoding for typical values."""
    assert _calibration_encode(1.23) == "123"  # 1.23 * 100 = 123
    assert _calibration_encode(0.987) == "99"  # 0.987 * 100 = 99 (rounded)
    assert _calibration_encode(10.0) == "1000"  # 10.0 * 100 = 1000


def test_calibration_encode_rounding():
    """Test calibration encoding with rounding."""
    assert _calibration_encode(1.2345) == "123"  # 1.2345 * 100 = 123 (rounded)
    assert _calibration_encode(0.995) == "100"  # 0.995 * 100 = 100 (rounded)


def test_calibration_encode_zero():
    """Test calibration encoding for zero."""
    assert _calibration_encode(0.0) == "0"


# Tests for _calibration_decode
def test_calibration_decode_valid():
    """Test calibration decoding with valid strings."""
    assert _calibration_decode("123") == 1.23
    assert _calibration_decode("99") == 0.99
    assert _calibration_decode("1000") == 10.0


def test_calibration_decode_zero():
    """Test calibration decoding for zero."""
    assert _calibration_decode("0") == 0.0


def test_calibration_decode_invalid():
    """Test calibration decoding with invalid inputs."""
    assert _calibration_decode("abc") is None  # Non-numeric
    assert _calibration_decode("") is None  # Empty
    assert _calibration_decode(None) is None  # None
    assert _calibration_decode("12.3") is None  # Float string


if __name__ == "__main__":
    pytest.main()
