"""
Leybold Analog Vacuum Gauge Module.

This module provides an implementation of the Leybold TTR 101 N THERMOVAC vacuum gauge, converting
analog voltage output to pressure readings in millibars (mbar) using an exponential formula. It
extends the `ExponentialVacuumGauge` base class with specific parameters and atmospheric gas
correction factors tailored to the TTR 101 N model.

Classes:
    - TTR101NGauge: A vacuum gauge class for the Leybold TTR 101 N THERMOVAC, using an
      exponential conversion formula.

Key Features:
    - Converts voltage to pressure using the formula: 10 ** ((voltage - 6.143) / 1.286), with
      clamping at 5e-5 mbar below 0.6119 V and 1.5e3 mbar above 10.2275 V.
    - Supports atmospheric gas adjustments with specific correction factors for known gases.
"""

from typing import Optional
import numpy as np
from numpy.typing import NDArray

from ..base.analog import ExponentialVacuumGauge
from ..base.atmosphere import Atmosphere


# pylint: disable=too-few-public-methods
class TTR101NGauge(ExponentialVacuumGauge):
    """
    A vacuum gauge class for the Leybold TTR 101 N THERMOVAC using an exponential conversion
    formula.

    This class extends `ExponentialVacuumGauge` to provide pressure readings for the
    Leybold TTR 101 N THERMOVAC gauge. It uses a specific exponential formula for
    voltage-to-pressure conversion and applies atmospheric gas correction factors based on
    known coefficients.

    Attributes:
        model_name (str): Fixed to "Leybold TTR 101 N THERMOVAC".
        offset_voltage (float): Fixed to 6.143 V, used in the exponential formula.
        scale (float): Fixed to 1.286, used in the exponential formula.
        v_min (float): Minimum voltage threshold (0.6119 V); inputs below this are clamped to
            `p_min`.
        v_max (float): Maximum voltage threshold (10.2275 V); inputs above this are clamped to
            `p_max`.
        p_min (float): Minimum pressure output before atmospheric scaling (5e-5 mbar).
        p_max (float): Maximum pressure output before atmospheric scaling (1.5e3 mbar).
        atmosphere (Atmosphere): The atmospheric gas used for calculations.
        atmosphere_factor (dict[Atmosphere, float]): A dictionary mapping atmospheric gases to
            their respective conversion factors, with known values for some gases and defaults
            of 1.0 for others.
    """

    # pylint: disable=duplicate-code
    atmosphere_factor = {
        Atmosphere.AIR: 1.0,  # Valid in the range 3e-3 to 3e-1 mbar
        Atmosphere.AR: 1.57,  # Valid in the range 3e-3 to 1e+0 mbar
        Atmosphere.CO: 1.0,  # Valid in the range 3e-3 to 3e-1 mbar
        Atmosphere.CO2: 1.0,  # Valid in the range 3e-3 to 3e-1 mbar
        Atmosphere.H2: 0.84,  # Valid in the range 3e-3 to 2e-1 mbar
        Atmosphere.HE: 1.4,  # Valid in the range 3e-3 to 3e-1 mbar
        Atmosphere.N2: 1.0,  # Valid in the range 3e-3 to 3e-1 mbar
        Atmosphere.O2: 1.0,  # Valid in the range 3e-3 to 3e-1 mbar
        Atmosphere.NE: 1.0,  # Unknown; default value
        Atmosphere.KR: 1.0,  # Unknown; default value
        Atmosphere.XE: 1.0,  # Unknown; default value
    }

    def __init__(self, atmosphere: Optional[str | Atmosphere] = None):
        """
        Initializes the TTR101NGauge instance.

        Args:
            atmosphere (Optional[Union[str, Atmosphere]], optional): The atmospheric gas used for
                calculations, either as an `Atmosphere` member or its string value (e.g., "Air").
                Defaults to `Atmosphere.AIR` if not provided.
        """
        super().__init__(
            model_name="Leybold TTR 101 N THERMOVAC",
            offset_voltage=6.143,
            scale=1.286,
            v_min=0.6119,
            v_max=10.2275,
            p_min=5e-5,
            p_max=1.5e3,
            atmosphere=atmosphere,
        )

    def convert_voltage(self, voltage: float | NDArray[np.float64]) -> float | NDArray[np.float64]:
        """
        Converts analog output voltage to pressure (mbar) using the TTR 101 N formula.

        This method overrides the base class implementation to use the specific formula for the
        Leybold TTR 101 N THERMOVAC: `pressure = 10 ** ((voltage - 6.143) / 1.286)`. Voltages below
        0.6119 V are clamped to 5e-5 mbar, and voltages above 10.2275 V are clamped to 1.5e3 mbar.
        The result is then scaled by the atmospheric gas factor.

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
