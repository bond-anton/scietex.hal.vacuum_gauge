"""
Tests for the scietex.hal.vacuum_gauge.leybold subpackage.

This module tests the TTR101NGauge class from analog.py, ensuring correct initialization,
voltage-to-pressure conversion, and atmospheric correction behavior.
"""

import pytest
import numpy as np
from numpy.testing import assert_almost_equal

try:
    from src.scietex.hal.vacuum_gauge.leybold import TTR101NGauge
    from src.scietex.hal.vacuum_gauge.base.atmosphere import Atmosphere
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.leybold import TTR101NGauge
    from scietex.hal.vacuum_gauge.base.atmosphere import Atmosphere


# Tests for TTR101NGauge
def test_ttr101n_gauge_init_default():
    """Test default initialization of TTR101NGauge."""
    gauge = TTR101NGauge()
    assert gauge.model_name == "Leybold TTR 101 N THERMOVAC"
    assert gauge.offset_voltage == 6.143
    assert gauge.scale == 1.286
    assert gauge.v_min == 0.6119
    assert gauge.v_max == 10.2275
    assert gauge.p_min == 5e-5
    assert gauge.p_max == 1500.0
    assert gauge.atmosphere == Atmosphere.AIR


def test_ttr101n_gauge_init_custom_atmosphere():
    """Test initialization with custom atmosphere."""
    gauge = TTR101NGauge(atmosphere="H2")
    assert gauge.atmosphere == Atmosphere.H2
    gauge_atm = TTR101NGauge(atmosphere=Atmosphere.NE)
    assert gauge_atm.atmosphere == Atmosphere.NE


def test_ttr101n_convert_voltage_single():
    """Test voltage-to-pressure conversion for a single value with TTR 101 N."""
    gauge = TTR101NGauge()
    # Formula: 10 ** ((voltage - 5.0) / 1.0)
    assert_almost_equal(gauge.convert_voltage(6.0), 0.77410966, decimal=6)  # 10^(6-5)
    assert_almost_equal(gauge.convert_voltage(4.0), 0.02155721, decimal=6)  # 10^(4-5)
    assert gauge.convert_voltage(0.0) == 5e-5  # Clamped to p_min
    assert gauge.convert_voltage(9.0) == 166.57791365267636  # Clamped to p_max


def test_ttr101n_convert_voltage_array():
    """Test voltage-to-pressure conversion for a NumPy array with TTR 101 N."""
    gauge = TTR101NGauge()
    voltages = np.array([0.0, 4.0, 6.0, 9.0])
    expected = np.array(
        [5e-5, 2.15572091e-02, 7.74109662e-01, 1.66577914e02]
    )  # Clamped and exponential
    result = gauge.convert_voltage(voltages)
    assert_almost_equal(result, expected, decimal=6)


def test_ttr101n_convert_voltage_atmosphere():
    """Test atmospheric correction for TTR 101 N."""
    gauge_he = TTR101NGauge(atmosphere="He")
    pressure_he = gauge_he.convert_voltage(6.0)
    assert_almost_equal(
        pressure_he, 0.7741096624041693 * 1.4, decimal=6
    )  # 0.7741096624041693 * He factor (1.4)

    gauge_kr = TTR101NGauge(atmosphere="Kr")
    pressure_kr = gauge_kr.convert_voltage(6.0)
    assert_almost_equal(
        pressure_kr, 0.7741096624041693 * 1.0, decimal=6
    )  # 0.7741096624041693 * Kr factor (1.0)


def test_ttr101n_convert_voltage_edge_cases():
    """Test edge cases for voltage conversion."""
    gauge = TTR101NGauge()
    # Exactly at v_min and v_max
    assert_almost_equal(
        gauge.convert_voltage(1.0), 0.00010017921055326844, decimal=6
    )  # Clamped to p_min
    assert_almost_equal(
        gauge.convert_voltage(8.6), 81.39082069890404, decimal=6
    )  # Clamped to p_max
    # Just within range
    assert_almost_equal(gauge.convert_voltage(1.1), 0.00011982242442791071, decimal=6)
    assert_almost_equal(gauge.convert_voltage(8.5), 68.04793178596019, decimal=6)


def test_ttr101n_atmosphere_factor_coverage():
    """Test that all Atmosphere members have a correction factor."""
    gauge = TTR101NGauge()
    for atm in Atmosphere:
        assert atm in gauge.atmosphere_factor, f"No correction factor for {atm.value}"
        assert isinstance(gauge.atmosphere_factor[atm], float)


if __name__ == "__main__":
    pytest.main()
