"""
Tests for the scietex.hal.vacuum_gauge.erstevak.analog module.

This module tests the MTP4DGauge and MTM9DGauge classes, ensuring correct initialization,
voltage-to-pressure conversion with model-specific exponential formulas, and atmospheric
correction behavior (fixed for MTP4D, pressure-dependent for MTM9D).
"""

import pytest
import numpy as np
from numpy.testing import assert_almost_equal

try:
    from src.scietex.hal.vacuum_gauge.erstevak import MTP4DGauge, MTM9DGauge
    from src.scietex.hal.vacuum_gauge.base.atmosphere import Atmosphere
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.erstevak import MTP4DGauge, MTM9DGauge
    from scietex.hal.vacuum_gauge.base.atmosphere import Atmosphere


# Tests for MTP4DGauge
def test_mtp4d_gauge_init_default():
    """Test default initialization of MTP4DGauge."""
    gauge = MTP4DGauge()
    assert gauge.model_name == "Erstevak MTP4D"
    assert gauge.offset_voltage == 5.5
    assert gauge.scale == 1.0
    assert gauge.v_min == 0.0
    assert gauge.v_max == 10.0
    assert gauge.p_min == 1e-5
    assert gauge.p_max == 1e3
    assert gauge.atmosphere == Atmosphere.AIR


def test_mtp4d_gauge_init_custom_atmosphere():
    """Test initialization with custom atmosphere."""
    gauge = MTP4DGauge(atmosphere="Kr")
    assert gauge.atmosphere == Atmosphere.KR
    gauge_atm = MTP4DGauge(atmosphere=Atmosphere.NE)
    assert gauge_atm.atmosphere == Atmosphere.NE


def test_mtp4d_convert_voltage_single():
    """Test voltage-to-pressure conversion for a single value with MTP4D."""
    gauge = MTP4DGauge()  # Air, factor = 1.0
    # Formula: 10 ** (voltage - 5.5)
    assert_almost_equal(gauge.convert_voltage(6.5), 10.0, decimal=6)  # 10^(6.5-5.5)
    assert_almost_equal(gauge.convert_voltage(4.5), 0.1, decimal=6)  # 10^(4.5-5.5)
    assert gauge.convert_voltage(-1.0) == 1e-5  # Clamped to p_min
    assert gauge.convert_voltage(11.0) == 1e3  # Clamped to p_max


def test_mtp4d_convert_voltage_array():
    """Test voltage-to-pressure conversion for a NumPy array with MTP4D."""
    gauge = MTP4DGauge()  # Air, factor = 1.0
    voltages = np.array([-1.0, 4.5, 6.5, 11.0])
    expected = np.array([1e-5, 0.1, 10.0, 1e3])  # Clamped and exponential
    result = gauge.convert_voltage(voltages)
    assert_almost_equal(result, expected, decimal=6)


def test_mtp4d_convert_voltage_atmosphere():
    """Test atmospheric correction for MTP4D."""
    gauge_ar = MTP4DGauge(atmosphere="Ar")
    pressure_ar = gauge_ar.convert_voltage(6.5)
    assert_almost_equal(pressure_ar, 10.0 * 1.6, decimal=6)  # 10.0 * Ar factor (1.6)

    gauge_h2 = MTP4DGauge(atmosphere="H2")
    pressure_h2 = gauge_h2.convert_voltage(6.5)
    assert_almost_equal(pressure_h2, 10.0 * 0.57, decimal=6)  # 10.0 * H2 factor (0.57)


def test_mtp4d_convert_voltage_edge_cases():
    """Test edge cases for voltage conversion with MTP4D."""
    gauge = MTP4DGauge()  # Air, factor = 1.0
    assert_almost_equal(gauge.convert_voltage(0.0), 1e-5, decimal=6)  # Clamped to p_min
    assert_almost_equal(gauge.convert_voltage(10.0), 1e3, decimal=6)  # Clamped to p_max
    assert_almost_equal(gauge.convert_voltage(0.1), 10 ** (0.1 - 5.5), decimal=6)
    assert_almost_equal(gauge.convert_voltage(9.9), 10 ** (9.9 - 5.5), decimal=6)


# Tests for MTM9DGauge
def test_mtm9d_gauge_init_default():
    """Test default initialization of MTM9DGauge."""
    gauge = MTM9DGauge()
    assert gauge.model_name == "Erstevak MTM9D"
    assert gauge.offset_voltage == 6.8
    assert gauge.scale == 0.6
    assert gauge.v_min == 0.0
    assert gauge.v_max == 10.0
    assert gauge.p_min == 1e-5
    assert gauge.p_max == 1e3
    assert gauge.atmosphere == Atmosphere.AIR


def test_mtm9d_gauge_init_custom_atmosphere():
    """Test initialization with custom atmosphere."""
    gauge = MTM9DGauge(atmosphere="CO2")
    assert gauge.atmosphere == Atmosphere.CO2
    gauge_atm = MTM9DGauge(atmosphere=Atmosphere.HE)
    assert gauge_atm.atmosphere == Atmosphere.HE


def test_mtm9d_convert_voltage_single_low_pressure():
    """Test voltage-to-pressure conversion for a single low pressure with MTM9D."""
    gauge = MTM9DGauge()  # Air, factor_low = 1.0
    # Formula: 10 ** ((voltage - 6.8) / 0.6)
    # Voltage 5.0: 10^((5.0-6.8)/0.6) = 10^(-3) = 1e-3
    pressure = gauge.convert_voltage(5.0)
    assert_almost_equal(pressure, 1e-3, decimal=6)  # <= 1e-3, factor_low = 1.0
    # Voltage 4.4: 10^((4.4-6.8)/0.6) = 10^(-4) = 1e-4
    pressure = gauge.convert_voltage(4.4)
    assert_almost_equal(pressure, 1e-4, decimal=6)  # <= 1e-3, factor_low = 1.0


def test_mtm9d_convert_voltage_single_high_pressure():
    """Test voltage-to-pressure conversion for a single high pressure with MTM9D."""
    gauge = MTM9DGauge()  # Air, factor_high = 1.0
    # Voltage 6.8: 10^((6.8-6.8)/0.6) = 10^0 = 1.0
    pressure = gauge.convert_voltage(6.8)
    assert_almost_equal(pressure, 1.0, decimal=6)  # > 1e-3, factor_high = 1.0
    # Voltage 8.0: 10^((8.0-6.8)/0.6) = 10^(2) = 100.0
    pressure = gauge.convert_voltage(8.0)
    assert_almost_equal(pressure, 100.0, decimal=6)  # > 1e-3, factor_high = 1.0


def test_mtm9d_convert_voltage_array():
    """Test voltage-to-pressure conversion for a NumPy array with MTM9D."""
    gauge = MTM9DGauge()  # Air, factors = 1.0
    voltages = np.array([-1.0, 4.4, 5.0, 6.8, 8.0, 11.0])
    expected = np.array([1e-5, 1e-4, 1e-3, 1.0, 100.0, 1e3])  # Clamped and exponential
    result = gauge.convert_voltage(voltages)
    assert_almost_equal(result, expected, decimal=6)


def test_mtm9d_convert_voltage_atmosphere_low():
    """Test atmospheric correction for MTM9D at low pressure (< 1e-3 mbar)."""
    gauge_kr = MTM9DGauge(atmosphere="Kr")
    pressure_kr = gauge_kr.convert_voltage(4.4)  # 1e-4 < 1e-3
    assert_almost_equal(pressure_kr, 1e-4 * 2.4, decimal=6)  # 1e-4 * Kr factor_low (2.4)

    gauge_co2 = MTM9DGauge(atmosphere="CO2")
    pressure_co2 = gauge_co2.convert_voltage(5.0)  # 1e-3 <= 1e-3
    assert_almost_equal(pressure_co2, 1e-3 * 0.89, decimal=6)  # 1e-3 * CO2 factor_low (0.89)


def test_mtm9d_convert_voltage_atmosphere_high():
    """Test atmospheric correction for MTM9D at high pressure (> 1e-3 mbar)."""
    gauge_he = MTM9DGauge(atmosphere="He")
    pressure_he = gauge_he.convert_voltage(8.0)  # 100.0 > 1e-3
    assert_almost_equal(pressure_he, 100.0 * 5.9, decimal=6)  # 100.0 * He factor_high (5.9)

    gauge_xe = MTM9DGauge(atmosphere="Xe")
    pressure_xe = gauge_xe.convert_voltage(6.8)  # 1.0 > 1e-3
    assert_almost_equal(pressure_xe, 1.0 * 0.41, decimal=6)  # 1.0 * Xe factor_high (0.41)


def test_mtm9d_convert_voltage_edge_cases():
    """Test edge cases for voltage conversion with MTM9D."""
    gauge = MTM9DGauge()  # Air, factors = 1.0
    assert_almost_equal(gauge.convert_voltage(0.0), 1e-5, decimal=6)  # Clamped to p_min
    assert_almost_equal(gauge.convert_voltage(10.0), 1e3, decimal=6)  # Clamped to p_max
    # Just above v_min: 10^((0.1-6.8)/0.6)
    assert_almost_equal(gauge.convert_voltage(0.1), 10 ** ((0.1 - 6.8) / 0.6), decimal=6)
    # Just below v_max: 10^((9.9-6.8)/0.6)
    assert_almost_equal(gauge.convert_voltage(9.9), 10 ** ((9.9 - 6.8) / 0.6), decimal=6)


# Combined test for atmosphere factor coverage
def test_erstevak_atmosphere_factor_coverage():
    """Test that all Atmosphere members have correction factors for both gauges."""
    for gauge_class in [MTP4DGauge, MTM9DGauge]:
        gauge = gauge_class()
        for atm in Atmosphere:
            assert (
                atm in gauge.atmosphere_factor
            ), f"No factor for {atm.value} in {gauge.model_name}"
            assert isinstance(gauge.atmosphere_factor[atm], float)
        if gauge_class == MTM9DGauge:
            for atm in Atmosphere:
                assert atm in gauge.atmosphere_factor_low, f"No low factor for {atm.value}"
                assert atm in gauge.atmosphere_factor_high, f"No high factor for {atm.value}"
                assert isinstance(gauge.atmosphere_factor_low[atm], float)
                assert isinstance(gauge.atmosphere_factor_high[atm], float)


if __name__ == "__main__":
    pytest.main()
