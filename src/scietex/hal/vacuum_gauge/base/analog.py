"""
Analog Vacuum Gauge Module.

This module provides functionality for working with analog vacuum gauges, converting analog
output voltage to pressure readings in millibar (mbar) units. It supports various atmospheric
gases and allows customization of the gauge model and atmosphere.

Classes:
    - ExponentialVacuumGauge: An abstract base class for handling analog vacuum gauge operations
      with exponential output, including voltage-to-pressure conversion. This class is intended
      to be inherited by subclasses that implement specific gauge models.
    - InterpolationVacuumGauge: A class for handling analog vacuum gauges using linear interpolation
      based on calibration data, converting voltage to pressure with atmospheric gas adjustments.

Key Features:
    - Supports multiple atmospheric gases with customizable conversion factors.
    - Converts analog voltage readings to pressure values in millibars (mbar).
    - Configurable gauge model, voltage range, pressure range, and atmosphere for accurate
      calculations.
    - Offers both exponential and interpolation-based conversion methods.
"""

from typing import Optional
import numpy as np
from numpy.typing import NDArray

from scietex.hal.analog_sensor import AnalogSensorInterface, LinearInterpolatorSensor
from .atmosphere import Atmosphere


# pylint: disable=too-few-public-methods
class ExponentialVacuumGauge(AnalogSensorInterface):
    """
    An abstract base class for handling analog vacuum gauges with exponential output.

    This class provides a foundation for converting analog output voltage from a vacuum gauge into
    pressure readings in millibars (mbar) using an exponential relationship.
    It supports customization for different atmospheric gases and gauge-specific parameters.
    Subclasses should override `convert_voltage` to implement model-specific conversion logic.

    Attributes:
        model_name (str): The model identifier of the vacuum gauge.
        offset_voltage (float): Voltage offset used in the pressure calculation.
        scale (float): Scaling factor for the voltage difference in the exponential pressure
            conversion.
        v_min (float): Minimum voltage threshold; inputs below this are clamped to `p_min`.
        v_max (float): Maximum voltage threshold; inputs above this are clamped to `p_max`.
        p_min (float): Minimum pressure output in mbar before atmospheric scaling (e.g., 5e-5).
        p_max (float): Maximum pressure output in mbar before atmospheric scaling (e.g., 1.5e3).
        atmosphere (Atmosphere): The atmospheric gas used for calculations.
        atmosphere_factor (dict[Atmosphere, float]): A dictionary mapping atmospheric gases to
            their respective conversion factors. Defaults to 1.0 for all supported gases.

    Methods:
        convert_voltage(voltage: Union[float, NDArray[np.float64]])
            -> Union[float, NDArray[np.float64]]:
            Converts analog output voltage to pressure (mbar) based on the gauge model and
            atmosphere.
    """

    atmosphere_factor = {
        Atmosphere.AIR: 1.0,
        Atmosphere.AR: 1.0,
        Atmosphere.CO: 1.0,
        Atmosphere.CO2: 1.0,
        Atmosphere.H2: 1.0,
        Atmosphere.HE: 1.0,
        Atmosphere.N2: 1.0,
        Atmosphere.O2: 1.0,
        Atmosphere.NE: 1.0,
        Atmosphere.KR: 1.0,
        Atmosphere.XE: 1.0,
    }

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        model_name: str,
        offset_voltage: float = 5.0,
        scale: float = 1.0,
        v_min: float = 0.0,
        v_max: float = 10.0,
        p_min: float = 5e-5,
        p_max: float = 1.5e3,
        atmosphere: Optional[str | Atmosphere] = None,
    ):
        """
        Initializes the ExponentialVacuumGauge instance.

        Args:
            model_name (str): The model identifier of the vacuum gauge.
            offset_voltage (float, optional): Voltage offset for the pressure calculation.
                Defaults to 5.0.
            scale (float, optional): Scaling factor for the voltage difference in the exponential
                pressure conversion. Defaults to 1.0.
            v_min (float, optional): Minimum voltage threshold; inputs below this are clamped to
                `p_min`. Defaults to 0.0.
            v_max (float, optional): Maximum voltage threshold; inputs above this are clamped to
                `p_max`. Defaults to 10.0.
            p_min (float, optional): Minimum pressure output in mbar before atmospheric scaling.
                Defaults to 5e-5.
            p_max (float, optional): Maximum pressure output in mbar before atmospheric scaling.
                Defaults to 1.5e3.
            atmosphere (Optional[Union[str, Atmosphere]], optional): The atmospheric gas used for
                calculations, either as an `Atmosphere` member or its string value (e.g., "Air").
                Defaults to `Atmosphere.AIR` if not provided.
        """
        super().__init__(model_name)
        self.offset_voltage: float = offset_voltage
        self.scale: float = scale
        self.v_min: float = v_min
        self.v_max: float = v_max
        self.p_min: float = p_min
        self.p_max: float = p_max
        self.atmosphere: Atmosphere
        if isinstance(atmosphere, str):
            self.atmosphere = Atmosphere.from_string(atmosphere)
        else:
            self.atmosphere = atmosphere if atmosphere is not None else Atmosphere.AIR

    def convert_voltage(self, voltage: float | NDArray[np.float64]) -> float | NDArray[np.float64]:
        """
        Converts analog output voltage to pressure (mbar).

        This method calculates pressure in millibars (mbar) from analog voltage using an
        exponential formula: `pressure = 10 ** ((voltage - offset_voltage) / scale)`.
        Voltages below `v_min` or above `v_max` are clamped to `p_min` or `p_max`, respectively.
        The entire pressure result, including clamps, is then scaled by the atmospheric gas factor.
        This is a basic implementation and should be overridden in subclasses for model-specific
        conversion logic.

        Args:
            voltage (Union[float, NDArray[np.float64]]): The analog output voltage(s) from the
                vacuum gauge. Can be a single float or a NumPy array.

        Returns:
            Union[float, NDArray[np.float64]]: The calculated pressure in millibars (mbar),
                matching the input type (float or array).
        """
        voltage_array = np.asarray(voltage)
        clamped_voltage = np.clip(voltage_array, self.v_min, self.v_max)
        pressure = np.where(
            clamped_voltage == self.v_min,
            self.p_min,
            np.where(
                clamped_voltage == self.v_max,
                self.p_max,
                10 ** ((clamped_voltage - self.offset_voltage) / self.scale),
            ),
        )
        pressure *= self.atmosphere_factor[self.atmosphere]
        return pressure if isinstance(voltage, np.ndarray) else float(pressure)


# pylint: disable=too-few-public-methods
class InterpolationVacuumGauge(LinearInterpolatorSensor):
    """
    A class for handling analog vacuum gauges using linear interpolation based on calibration data.

    This class extends `LinearInterpolatorSensor` to convert analog output voltage from a vacuum
    gauge into pressure readings in millibars (mbar) using linear interpolation over provided
    calibration data. It supports atmospheric gas adjustments and enforces voltage and pressure
    limits. It is designed for vacuum gauges where pressure is mapped directly from voltage via
    calibration points (e.g., Edwards APG-M or APG-L).

    Attributes:
        model_name (str): The model identifier of the vacuum gauge.
        data (NDArray[np.float64]): 2D array with shape (n, 2) containing voltage (column 0) and
            pressure (column 1) calibration points.
        v_min (float): Minimum voltage threshold; inputs below this are clamped to `p_min`.
        v_max (float): Maximum voltage threshold; inputs above this are clamped to `p_max`.
        p_min (float): Minimum pressure output in mbar before atmospheric scaling (e.g., 1e-6).
        p_max (float): Maximum pressure output in mbar before atmospheric scaling (e.g., 1000).
        atmosphere (Atmosphere): The atmospheric gas used for calculations.
        atmosphere_factor (dict[Atmosphere, float]): A dictionary mapping atmospheric gases to
            their respective conversion factors. Defaults to 1.0 for all supported gases.

    Methods:
        convert_voltage(voltage: Union[float, NDArray[np.float64]])
            -> Union[float, NDArray[np.float64]]:
            Converts analog output voltage to pressure (mbar) using linear interpolation, adjusted
            by atmospheric gas factor, with clamping at specified limits.
    """

    atmosphere_factor = {
        Atmosphere.AIR: 1.0,
        Atmosphere.AR: 1.0,
        Atmosphere.CO: 1.0,
        Atmosphere.CO2: 1.0,
        Atmosphere.H2: 1.0,
        Atmosphere.HE: 1.0,
        Atmosphere.N2: 1.0,
        Atmosphere.O2: 1.0,
        Atmosphere.NE: 1.0,
        Atmosphere.KR: 1.0,
        Atmosphere.XE: 1.0,
    }

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        model_name: str,
        data: NDArray[np.float64],
        v_min: float = 0.0,
        v_max: float = 10.0,
        p_min: float = 1e-6,
        p_max: float = 1000.0,
        atmosphere: Optional[str | Atmosphere] = None,
        extrapolate: Optional[bool] = None,
    ):
        """
        Initializes the InterpolationVacuumGauge instance.

        Args:
            model_name (str): The model identifier of the vacuum gauge.
            data (NDArray[np.float64]): 2D array with shape (n, 2) containing voltage (column 0)
                and pressure (column 1) calibration points.
            v_min (float, optional): Minimum voltage threshold; inputs below this are clamped to
                `p_min`. Defaults to 0.0.
            v_max (float, optional): Maximum voltage threshold; inputs above this are clamped to
                `p_max`. Defaults to 10.0.
            p_min (float, optional): Minimum pressure output in mbar before atmospheric scaling.
                Defaults to 1e-6.
            p_max (float, optional): Maximum pressure output in mbar before atmospheric scaling.
                Defaults to 1000.0.
            atmosphere (Optional[Union[str, Atmosphere]], optional): The atmospheric gas used for
                calculations, either as an `Atmosphere` member or its string value (e.g., "Air").
                Defaults to `Atmosphere.AIR` if not provided.
            extrapolate (Optional[bool], optional): Whether to extrapolate beyond the calibration
                data. Defaults to None (uses `LinearInterpolatorSensor` default behavior).
        """
        super().__init__(model_name, data, extrapolate=extrapolate)
        self.v_min: float = v_min
        self.v_max: float = v_max
        self.p_min: float = p_min
        self.p_max: float = p_max
        self.atmosphere: Atmosphere
        if isinstance(atmosphere, str):
            self.atmosphere = Atmosphere.from_string(atmosphere)
        else:
            self.atmosphere = atmosphere if atmosphere is not None else Atmosphere.AIR

    def convert_voltage(self, voltage: float | NDArray[np.float64]) -> float | NDArray[np.float64]:
        """
        Converts analog output voltage to pressure (mbar) using linear interpolation.

        This method uses linear interpolation from the provided calibration data to compute
        pressure, clamps the result to `p_min` or `p_max` if the input voltage is outside `v_min`
        or `v_max`, and then scales the entire pressure result (including clamps) by the
        atmospheric gas factor.

        Args:
            voltage (Union[float, NDArray[np.float64]]): The analog output voltage(s) from the
                vacuum gauge. Can be a single float or a NumPy array.

        Returns:
            Union[float, NDArray[np.float64]]: The calculated pressure in millibars (mbar),
                matching the input type (float or array).
        """
        voltage_array = np.asarray(voltage)
        clamped_voltage = np.clip(voltage_array, self.v_min, self.v_max)
        interpolated_pressure = super().convert_voltage(clamped_voltage)
        pressure = np.where(
            clamped_voltage == self.v_min,
            self.p_min,
            np.where(clamped_voltage == self.v_max, self.p_max, interpolated_pressure),
        )
        pressure *= self.atmosphere_factor[self.atmosphere]
        return pressure if isinstance(voltage, np.ndarray) else float(pressure)
