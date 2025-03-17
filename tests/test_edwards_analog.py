"""
Tests for the scietex.hal.vacuum_gauge.edwards subpackage.

This module tests the APGMGauge and APGLGauge classes from analog.py, ensuring correct
initialization, voltage-to-pressure conversion, and atmospheric correction behavior using
calibration data from calibration_data.py.
"""

import pytest
import numpy as np
from numpy.testing import assert_almost_equal

try:
    from src.scietex.hal.vacuum_gauge.edwards import APGMGauge, APGLGauge
    from src.scietex.hal.vacuum_gauge.edwards.calibration_data import (
        APG_M_CALIBRATION_DATA,
        APG_L_CALIBRATION_DATA,
    )
    from src.scietex.hal.vacuum_gauge.base.atmosphere import Atmosphere
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.edwards import APGMGauge, APGLGauge
    from scietex.hal.vacuum_gauge.edwards.calibration_data import (
        APG_M_CALIBRATION_DATA,
        APG_L_CALIBRATION_DATA,
    )
    from scietex.hal.vacuum_gauge.base.atmosphere import Atmosphere


# Tests for APGMGauge
def test_apgm_gauge_init_default():
    """Test default initialization of APGMGauge."""
    gauge = APGMGauge()
    assert gauge.model_name == "Edwards APG-M"
    assert gauge.v_min == 2.0
    assert gauge.v_max == 10.0
    assert gauge.p_min == 1e-5
    assert gauge.p_max == 1000.0
    assert gauge.atmosphere == Atmosphere.AIR
    assert np.array_equal(gauge.data, APG_M_CALIBRATION_DATA)


def test_apgm_gauge_init_custom_atmosphere():
    """Test initialization with custom atmosphere."""
    gauge = APGMGauge(atmosphere="He")
    assert gauge.atmosphere == Atmosphere.HE
    gauge_atm = APGMGauge(atmosphere=Atmosphere.AR)
    assert gauge_atm.atmosphere == Atmosphere.AR


def test_apgm_convert_voltage_single():
    """Test voltage-to-pressure conversion for a single value with APG-M."""
    gauge = APGMGauge()
    # Interpolation between (4.0, 1.0) and (6.0, 10.0)
    assert_almost_equal(gauge.convert_voltage(5.0), 0.176, decimal=6)  # Linear midpoint
    assert gauge.convert_voltage(0.0) == 1e-5  # Clamped to p_min
    assert gauge.convert_voltage(10.0) == 1000.0  # Clamped to p_max


def test_apgm_convert_voltage_array():
    """Test voltage-to-pressure conversion for a NumPy array with APG-M."""
    gauge = APGMGauge()
    voltages = np.array([0.0, 2.0, 5.0, 10.0])
    expected = np.array([1e-5, 1e-5, 1.76e-1, 1000.0])  # Interpolated and clamped
    result = gauge.convert_voltage(voltages)
    assert_almost_equal(result, expected, decimal=6)


def test_apgm_convert_voltage_atmosphere():
    """Test atmospheric correction for APG-M."""
    gauge_he = APGMGauge(atmosphere="He")
    pressure_he = gauge_he.convert_voltage(5.0)
    assert_almost_equal(pressure_he, 0.176 * 1.0, decimal=6)  # 0.176 * He factor (1.0)

    gauge_ar = APGMGauge(atmosphere="Ar")
    pressure_ar = gauge_ar.convert_voltage(5.0)
    assert_almost_equal(pressure_ar, 0.176 * 1.0, decimal=6)  # 0.176 * Ar factor (1.0)


# Tests for APGLGauge
def test_apgl_gauge_init_default():
    """Test default initialization of APGLGauge."""
    gauge = APGLGauge()
    assert gauge.model_name == "Edwards APG-L"
    assert gauge.v_min == 2.0
    assert gauge.v_max == 10.0
    assert gauge.p_min == 1e-6
    assert gauge.p_max == 1000.0
    assert gauge.atmosphere == Atmosphere.AIR
    assert np.array_equal(gauge.data, APG_L_CALIBRATION_DATA)


def test_apgl_gauge_init_custom_atmosphere():
    """Test initialization with custom atmosphere."""
    gauge = APGLGauge(atmosphere="CO2")
    assert gauge.atmosphere == Atmosphere.CO2
    gauge_atm = APGLGauge(atmosphere=Atmosphere.KR)
    assert gauge_atm.atmosphere == Atmosphere.KR


def test_apgl_convert_voltage_single():
    """Test voltage-to-pressure conversion for a single value with APG-L."""
    gauge = APGLGauge()
    # Interpolation between (4.0, 0.1) and (6.0, 10.0)
    assert_almost_equal(gauge.convert_voltage(5.0), 5.92e-2, decimal=6)  # Linear midpoint
    assert gauge.convert_voltage(0.0) == 1e-6  # Clamped to p_min
    assert gauge.convert_voltage(10.0) == 1000.0  # Clamped to p_max


def test_apgl_convert_voltage_array():
    """Test voltage-to-pressure conversion for a NumPy array with APG-L."""
    gauge = APGLGauge()
    voltages = np.array([0.0, 2.0, 5.0, 10.0])
    expected = np.array([1e-6, 1e-6, 5.92e-2, 1000.0])  # Interpolated and clamped
    result = gauge.convert_voltage(voltages)
    assert_almost_equal(result, expected, decimal=6)


def test_apgl_convert_voltage_atmosphere():
    """Test atmospheric correction for APG-L."""
    gauge_h2 = APGLGauge(atmosphere="H2")
    pressure_h2 = gauge_h2.convert_voltage(5.0)
    assert_almost_equal(pressure_h2, 5.92e-2 * 1.0, decimal=6)  # 5.92e-2 * H2 factor (1.0)

    gauge_xe = APGLGauge(atmosphere="Xe")
    pressure_xe = gauge_xe.convert_voltage(5.0)
    assert_almost_equal(pressure_xe, 5.92e-2 * 1.0, decimal=6)  # 5.92e-2 * Xe factor (1.0)


# Tests for calibration_data.py
def test_apgm_calibration_data():
    """Test APG_M_CALIBRATION_DATA structure and values."""
    assert APG_M_CALIBRATION_DATA.shape == (47, 2)  # 5 points, 2 columns (voltage, pressure)
    assert_almost_equal(APG_M_CALIBRATION_DATA[0], [2.0, 1e-5])  # First point
    assert_almost_equal(APG_M_CALIBRATION_DATA[-1], [10.0, 1000.0])  # Last point


def test_apgl_calibration_data():
    """Test APG_L_CALIBRATION_DATA structure and values."""
    assert APG_L_CALIBRATION_DATA.shape == (47, 2)  # 5 points, 2 columns (voltage, pressure)
    assert_almost_equal(APG_L_CALIBRATION_DATA[0], [2.0, 1e-6])  # First point
    assert_almost_equal(APG_L_CALIBRATION_DATA[-1], [10.0, 1000.0])  # Last point


if __name__ == "__main__":
    pytest.main()
