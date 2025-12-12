"""
Erstevak Analog Vacuum Gauge Module.

This module provides implementations of exponential vacuum gauges for Erstevak MTM9D and MTP4D
models. It extends the `ExponentialVacuumGauge` base class with specific formulas and atmospheric
gas correction factors tailored to each model. The MTM9D model uses pressure-dependent
coefficients.

Classes:
    - MTP4DGauge: A vacuum gauge class for the Erstevak MTP4D, using a simple exponential formula.
    - MTM9DGauge: A vacuum gauge class for the Erstevak MTM9D, using an exponential formula with
      pressure-dependent atmospheric coefficients.

Key Features:
    - Converts voltage to pressure using model-specific exponential formulas.
    - Supports atmospheric gas adjustments with fixed (MTP4D) or pressure-dependent (MTM9D)
      coefficients.
    - Clamps voltage inputs to reasonable ranges based on gauge specifications.
"""

from typing import Optional
import numpy as np
from numpy.typing import NDArray

from ..base.analog import ExponentialVacuumGauge
from ..base.atmosphere import Atmosphere


# pylint: disable=too-few-public-methods
class MTP4DGauge(ExponentialVacuumGauge):
    """
    A vacuum gauge class for the Erstevak MTP4D using a simple exponential formula.

    This class extends `ExponentialVacuumGauge` to provide pressure readings for the Erstevak MTP4D
    vacuum gauge using the formula: `pressure = 10 ** (voltage - 5.5)`. It applies fixed
    atmospheric gas correction factors.

    Attributes:
        model_name (str): Fixed to "Erstevak MTP4D".
        offset_voltage (float): Fixed to 5.5 V, used in the exponential formula.
        scale (float): Fixed to 1.0, used in the exponential formula.
        v_min (float): Minimum voltage threshold (0.0 V); inputs below this are clamped to `p_min`.
        v_max (float): Maximum voltage threshold (10.0 V); inputs above this are clamped to `p_max`.
        p_min (float): Minimum pressure output before atmospheric scaling (1e-5 mbar).
        p_max (float): Maximum pressure output before atmospheric scaling (1e3 mbar).
        atmosphere (Atmosphere): The atmospheric gas used for calculations.
        atmosphere_factor (dict[Atmosphere, float]): A dictionary mapping atmospheric gases to their
            respective conversion factors, with known values for some gases and defaults of 1.0
            for others.
    """

    atmosphere_factor = {
        Atmosphere.AIR: 1.0,
        Atmosphere.AR: 1.6,
        Atmosphere.CO: 1.0,
        Atmosphere.CO2: 0.89,
        Atmosphere.H2: 0.57,
        Atmosphere.HE: 1.0,
        Atmosphere.N2: 1.0,
        Atmosphere.O2: 1.0,  # Unknown; default value
        Atmosphere.NE: 1.4,
        Atmosphere.KR: 2.4,
        Atmosphere.XE: 1.0,  # Unknown; default value
    }

    def __init__(self, atmosphere: Optional[str | Atmosphere] = None):
        """
        Initializes the MTP4DGauge instance.

        Args:
            atmosphere (Optional[Union[str, Atmosphere]], optional): The atmospheric gas used for
                calculations, either as an `Atmosphere` member or its string value (e.g., "Air").
                Defaults to `Atmosphere.AIR` if not provided.
        """
        super().__init__(
            model_name="Erstevak MTP4D",
            offset_voltage=5.5,
            scale=1.0,
            v_min=0.0,
            v_max=10.0,
            p_min=1e-5,
            p_max=1e3,
            atmosphere=atmosphere,
        )


# pylint: disable=too-few-public-methods
class MTM9DGauge(ExponentialVacuumGauge):
    """
    A vacuum gauge class for the Erstevak MTM9D using an exponential formula with
    pressure-dependent coefficients.

    This class extends `ExponentialVacuumGauge` to provide pressure readings for the Erstevak MTM9D
    vacuum gauge using the formula: `pressure = 10 ** ((voltage - 6.8) / 0.6)`. It applies
    atmospheric gas correction factors that vary depending on whether the calculated pressure is
    below or above 1e-3 mbar.

    Attributes:
        model_name (str): Fixed to "Erstevak MTM9D".
        offset_voltage (float): Fixed to 6.8 V, used in the exponential formula.
        scale (float): Fixed to 0.6, used in the exponential formula.
        v_min (float): Minimum voltage threshold (0.0 V); inputs below this
            are clamped to `p_min`.
        v_max (float): Maximum voltage threshold (10.0 V); inputs above this
            are clamped to `p_max`.
        p_min (float): Minimum pressure output before atmospheric scaling (1e-5 mbar).
        p_max (float): Maximum pressure output before atmospheric scaling (1e3 mbar).
        atmosphere (Atmosphere): The atmospheric gas used for calculations.
        atmosphere_factor_low (dict[Atmosphere, float]): Coefficients for pressures
            below 1e-3 mbar.
        atmosphere_factor_high (dict[Atmosphere, float]): Coefficients for pressures
            above 1e-3 mbar.
    """

    atmosphere_factor_low = {
        Atmosphere.AIR: 1.0,
        Atmosphere.AR: 1.6,
        Atmosphere.CO: 1.0,
        Atmosphere.CO2: 0.89,
        Atmosphere.H2: 0.57,
        Atmosphere.HE: 1.0,
        Atmosphere.N2: 1.0,
        Atmosphere.O2: 1.0,  # Unknown; default value
        Atmosphere.NE: 1.4,
        Atmosphere.KR: 2.4,
        Atmosphere.XE: 1.0,  # Unknown; default value
    }

    atmosphere_factor_high = {
        Atmosphere.AIR: 1.0,
        Atmosphere.AR: 0.8,
        Atmosphere.CO: 1.0,  # Unknown; default value
        Atmosphere.CO2: 0.74,
        Atmosphere.H2: 2.4,
        Atmosphere.HE: 5.9,
        Atmosphere.N2: 1.0,
        Atmosphere.O2: 1.0,  # Unknown; default value
        Atmosphere.NE: 3.5,
        Atmosphere.KR: 0.6,
        Atmosphere.XE: 0.41,
    }

    def __init__(self, atmosphere: Optional[str | Atmosphere] = None):
        """
        Initializes the MTM9DGauge instance.

        Args:
            atmosphere (Optional[Union[str, Atmosphere]], optional): The atmospheric gas used for
                calculations, either as an `Atmosphere` member or its string value (e.g., "Air").
                Defaults to `Atmosphere.AIR` if not provided.
        """
        super().__init__(
            model_name="Erstevak MTM9D",
            offset_voltage=6.8,
            scale=0.6,
            v_min=0.0,
            v_max=10.0,
            p_min=1e-5,
            p_max=1e3,
            atmosphere=atmosphere,
        )

    # pylint: disable=duplicate-code
    def convert_voltage(self, voltage: float | NDArray[np.float64]) -> float | NDArray[np.float64]:
        """
        Converts analog output voltage to pressure (mbar) using the MTM9D formula with
        pressure-dependent coefficients.

        This method calculates pressure using the formula:
            `pressure = 10 ** ((voltage - 6.8) / 0.6)`.
        Voltages below 0.0 V are clamped to 1e-5 mbar, and voltages above 10.0 V are
        clamped to 1e3 mbar. The atmospheric gas correction factor is applied based on whether the
        calculated pressure is below or above 1e-3 mbar.

        Args:
            voltage (Union[float, NDArray[np.float64]]): The analog output voltage(s) from the
                vacuum gauge. Can be a single float or a NumPy array.

        Returns:
            Union[float, NDArray[np.float64]]: The calculated pressure in millibars (mbar),
                matching the input type (float or array).
        """
        voltage_array = np.asarray(voltage)
        clamped_voltage = np.clip(voltage_array, self.v_min, self.v_max)
        base_pressure = np.where(
            clamped_voltage == self.v_min,
            self.p_min,
            np.where(
                clamped_voltage == self.v_max,
                self.p_max,
                10 ** ((clamped_voltage - self.offset_voltage) / self.scale),
            ),
        )
        # Apply pressure-dependent coefficients
        pressure = np.where(
            base_pressure <= 1e-3,
            base_pressure * self.atmosphere_factor_low[self.atmosphere],
            base_pressure * self.atmosphere_factor_high[self.atmosphere],
        )
        return pressure if isinstance(voltage, np.ndarray) else float(pressure)
