"""
Tests for the scietex.hal.vacuum_gauge.base subpackage.

This module tests the ExponentialVacuumGauge and InterpolationVacuumGauge classes from analog.py,
as well as the Atmosphere enum from atmosphere.py, ensuring correct initialization,
voltage-to-pressure conversion, and atmospheric gas handling.
"""

import pytest
import numpy as np
from numpy.testing import assert_almost_equal

try:
    from src.scietex.hal.vacuum_gauge.base import ExponentialVacuumGauge, InterpolationVacuumGauge
    from src.scietex.hal.vacuum_gauge.base import Atmosphere
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.base import ExponentialVacuumGauge, InterpolationVacuumGauge
    from scietex.hal.vacuum_gauge.base import Atmosphere


# Tests for Atmosphere enum (unchanged from previous version)
def test_atmosphere_enum_members():
    """Test that all Atmosphere members are correctly defined."""
    expected_members = {
        "AIR": "Air",
        "AR": "Ar",
        "CO": "CO",
        "CO2": "CO2",
        "H2": "H2",
        "HE": "He",
        "N2": "N2",
        "O2": "O2",
        "NE": "Ne",
        "KR": "Kr",
        "XE": "Xe",
    }
    for name, value in expected_members.items():
        assert getattr(Atmosphere, name).value == value
        assert isinstance(getattr(Atmosphere, name), Atmosphere)


def test_atmosphere_from_string_valid():
    """Test from_string converts valid gas strings to Atmosphere members."""
    assert Atmosphere.from_string("Air") == Atmosphere.AIR
    assert Atmosphere.from_string("He") == Atmosphere.HE
    assert Atmosphere.from_string("CO2") == Atmosphere.CO2


def test_atmosphere_from_string_invalid():
    """Test from_string raises ValueError for invalid gas strings."""
    with pytest.raises(ValueError, match="Unknown atmosphere gas: InvalidGas"):
        Atmosphere.from_string("InvalidGas")
    with pytest.raises(ValueError, match="Unknown atmosphere gas: H20"):
        Atmosphere.from_string("H20")


def test_atmosphere_from_string_case_sensitivity():
    """Test from_string is case-sensitive and matches exact values."""
    with pytest.raises(ValueError, match="Unknown atmosphere gas: air"):
        Atmosphere.from_string("air")


# Tests for ExponentialVacuumGauge
def test_exponential_vacuum_gauge_init_default():
    """Test default initialization of ExponentialVacuumGauge."""
    gauge = ExponentialVacuumGauge("TestGauge")
    assert gauge.model_name == "TestGauge"
    assert gauge.offset_voltage == 5.0
    assert gauge.scale == 1.0
    assert gauge.v_min == 0.0
    assert gauge.v_max == 10.0
    assert gauge.p_min == 5e-5
    assert gauge.p_max == 1.5e3
    assert gauge.atmosphere == Atmosphere.AIR


def test_exponential_vacuum_gauge_init_custom():
    """Test custom initialization with string and Atmosphere inputs."""
    gauge = ExponentialVacuumGauge(
        "CustomGauge",
        offset_voltage=4.0,
        scale=2.0,
        v_min=1.0,
        v_max=9.0,
        p_min=1e-4,
        p_max=1e3,
        atmosphere="He",
    )
    assert gauge.offset_voltage == 4.0
    assert gauge.scale == 2.0
    assert gauge.v_min == 1.0
    assert gauge.v_max == 9.0
    assert gauge.p_min == 1e-4
    assert gauge.p_max == 1e3
    assert gauge.atmosphere == Atmosphere.HE

    gauge_atm = ExponentialVacuumGauge("AtmGauge", atmosphere=Atmosphere.AR)
    assert gauge_atm.atmosphere == Atmosphere.AR


def test_exponential_convert_voltage_single():
    """Test voltage-to-pressure conversion for a single value."""
    gauge = ExponentialVacuumGauge("TestGauge", offset_voltage=5.0, scale=1.0)
    # Expected: 10 ** ((6.0 - 5.0) / 1.0) = 10 ** 1 = 10.0
    assert_almost_equal(gauge.convert_voltage(6.0), 10.0, decimal=6)
    # Clamping: below v_min (0.0) -> p_min (5e-5)
    assert gauge.convert_voltage(-1.0) == 5e-5
    # Clamping: above v_max (10.0) -> p_max (1.5e3)
    assert gauge.convert_voltage(11.0) == 1.5e3


def test_exponential_convert_voltage_array():
    """Test voltage-to-pressure conversion for a NumPy array."""
    gauge = ExponentialVacuumGauge("TestGauge", offset_voltage=5.0, scale=1.0)
    voltages = np.array([-1.0, 5.0, 6.0, 11.0])
    expected = np.array([5e-5, 1.0, 10.0, 1.5e3])  # 10^((v-5)/1) with clamping
    result = gauge.convert_voltage(voltages)
    assert_almost_equal(result, expected, decimal=6)


def test_exponential_convert_voltage_atmosphere():
    """Test that atmosphere factor is applied (currently 1.0 for all gases)."""
    gauge = ExponentialVacuumGauge("TestGauge", atmosphere=Atmosphere.HE)
    assert_almost_equal(gauge.convert_voltage(6.0), 10.0, decimal=6)  # Factor = 1.0


# Tests for InterpolationVacuumGauge
@pytest.fixture
def calibration_data():
    """Provide sample calibration data for InterpolationVacuumGauge."""
    return np.array(
        [
            [0.0, 1e-6],  # v_min, p_min
            [5.0, 1e-3],
            [10.0, 1000.0],  # v_max, p_max
        ]
    )


# pylint: disable=redefined-outer-name
def test_interpolation_vacuum_gauge_init_default(calibration_data):
    """Test default initialization of InterpolationVacuumGauge."""
    gauge = InterpolationVacuumGauge("TestGauge", calibration_data)
    assert gauge.model_name == "TestGauge"
    assert gauge.v_min == 0.0
    assert gauge.v_max == 10.0
    assert gauge.p_min == 1e-6
    assert gauge.p_max == 1000.0
    assert gauge.atmosphere == Atmosphere.AIR
    assert np.array_equal(gauge.data, calibration_data)


# pylint: disable=redefined-outer-name
def test_interpolation_vacuum_gauge_init_custom(calibration_data):
    """Test custom initialization with string and Atmosphere inputs."""
    gauge = InterpolationVacuumGauge(
        "CustomGauge",
        calibration_data,
        v_min=1.0,
        v_max=9.0,
        p_min=1e-5,
        p_max=500.0,
        atmosphere="N2",
        extrapolate=True,
    )
    assert gauge.v_min == 1.0
    assert gauge.v_max == 9.0
    assert gauge.p_min == 1e-5
    assert gauge.p_max == 500.0
    assert gauge.atmosphere == Atmosphere.N2


# pylint: disable=redefined-outer-name
def test_interpolation_convert_voltage_single(calibration_data):
    """Test voltage-to-pressure conversion for a single value."""
    gauge = InterpolationVacuumGauge("TestGauge", calibration_data)
    # Linear interpolation between (5.0, 1e-3) and (10.0, 1000.0)
    assert_almost_equal(gauge.convert_voltage(7.5), 500.0005, decimal=6)  # Midpoint approx
    assert gauge.convert_voltage(-1.0) == 1e-6  # Clamped to p_min
    assert gauge.convert_voltage(11.0) == 1000.0  # Clamped to p_max


# pylint: disable=redefined-outer-name
def test_interpolation_convert_voltage_array(calibration_data):
    """Test voltage-to-pressure conversion for a NumPy array."""
    gauge = InterpolationVacuumGauge("TestGauge", calibration_data)
    voltages = np.array([-1.0, 2.5, 5.0, 7.5, 11.0])
    # Expected: [p_min, interp(0-5), 1e-3, interp(5-10), p_max]
    expected = np.array([1e-6, 5.005e-4, 1e-3, 500.0005, 1000.0])
    result = gauge.convert_voltage(voltages)
    assert_almost_equal(result, expected, decimal=6)


# pylint: disable=redefined-outer-name
def test_interpolation_convert_voltage_atmosphere(calibration_data):
    """Test that atmosphere factor is applied (currently 1.0 for all gases)."""
    gauge = InterpolationVacuumGauge("TestGauge", calibration_data, atmosphere=Atmosphere.CO2)
    assert_almost_equal(gauge.convert_voltage(7.5), 500.0005, decimal=6)  # Factor = 1.0


def test_interpolation_invalid_data():
    """Test that invalid calibration data raises an error."""
    invalid_data = np.array([[1.0], [2.0]])  # Wrong shape
    with pytest.raises(ValueError, match="Wrong data array shape"):
        InterpolationVacuumGauge("BadGauge", invalid_data)


if __name__ == "__main__":
    pytest.main()
