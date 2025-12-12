"""
Edwards Analog Vacuum Gauge Module.

This module provides specific implementations of analog vacuum gauges for
Edwards APG-M and APG-L models. It uses calibration data from `edwards.calibration_data`
to convert voltage to pressure readings in millibars (mbar) via linear interpolation,
with support for atmospheric gas adjustments.

Classes:
    - APGMGauge: A vacuum gauge class for the Edwards APG-M model, using linear interpolation.
    - APGLGauge: A vacuum gauge class for the Edwards APG-L model, using linear interpolation.

Key Features:
    - Utilizes pre-defined calibration data for accurate pressure conversion.
    - Supports atmospheric gas corrections via inherited functionality.
    - Clamps voltage and pressure to model-specific ranges.
"""

from typing import Optional

from ..base.analog import InterpolationVacuumGauge
from ..base.atmosphere import Atmosphere
from .calibration_data import APG_M_CALIBRATION_DATA, APG_L_CALIBRATION_DATA


# pylint: disable=too-few-public-methods
class APGMGauge(InterpolationVacuumGauge):
    """
    A vacuum gauge class for the Edwards APG-M model using linear interpolation.

    This class extends `InterpolationVacuumGauge` to provide pressure readings for the
    Edwards APG-M vacuum gauge based on its calibration data. It supports atmospheric gas
    adjustments and enforces voltage and pressure limits specific to the APG-M model.

    Attributes:
        model_name (str): Fixed to "Edwards APG-M".
        data (NDArray[np.float64]): Calibration data from `APG_M_CALIBRATION_DATA`.
        v_min (float): Minimum voltage threshold (2.0 V).
        v_max (float): Maximum voltage threshold (10.0 V).
        p_min (float): Minimum pressure output before atmospheric scaling (1e-5 mbar).
        p_max (float): Maximum pressure output before atmospheric scaling (1000 mbar).
        atmosphere (Atmosphere): The atmospheric gas used for calculations.
    """

    def __init__(
        self,
        atmosphere: Optional[str | Atmosphere] = None,
        extrapolate: Optional[bool] = False,
    ):
        """
        Initializes the APGMGauge instance.

        Args:
            atmosphere (Optional[Union[str, Atmosphere]], optional): The atmospheric gas used for
                calculations, either as an `Atmosphere` member or its string value (e.g., "Air").
                Defaults to `Atmosphere.AIR` if not provided.
            extrapolate (Optional[bool], optional): Whether to extrapolate beyond the calibration
                data. Defaults to False to prevent extrapolation outside the 2.0-10.0 V range.
        """
        super().__init__(
            model_name="Edwards APG-M",
            data=APG_M_CALIBRATION_DATA,
            v_min=2.0,
            v_max=10.0,
            p_min=1e-5,
            p_max=1000.0,
            atmosphere=atmosphere,
            extrapolate=extrapolate,
        )


# pylint: disable=too-few-public-methods
class APGLGauge(InterpolationVacuumGauge):
    """
    A vacuum gauge class for the Edwards APG-L model using linear interpolation.

    This class extends `InterpolationVacuumGauge` to provide pressure readings for the
    Edwards APG-L vacuum gauge based on its calibration data. It supports atmospheric
    gas adjustments and enforces voltage and pressure limits specific to the APG-L model.

    Attributes:
        model_name (str): Fixed to "Edwards APG-L".
        data (NDArray[np.float64]): Calibration data from `APG_L_CALIBRATION_DATA`.
        v_min (float): Minimum voltage threshold (2.0 V).
        v_max (float): Maximum voltage threshold (10.0 V).
        p_min (float): Minimum pressure output before atmospheric scaling (1e-6 mbar).
        p_max (float): Maximum pressure output before atmospheric scaling (1000 mbar).
        atmosphere (Atmosphere): The atmospheric gas used for calculations.
    """

    def __init__(
        self,
        atmosphere: Optional[str | Atmosphere] = None,
        extrapolate: Optional[bool] = False,
    ):
        """
        Initializes the APGLGauge instance.

        Args:
            atmosphere (Optional[Union[str, Atmosphere]], optional): The atmospheric gas used for
                calculations, either as an `Atmosphere` member or its string value (e.g., "Air").
                Defaults to `Atmosphere.AIR` if not provided.
            extrapolate (Optional[bool], optional): Whether to extrapolate beyond the calibration
                data. Defaults to False to prevent extrapolation outside the 2.0-10.0 V range.
        """
        super().__init__(
            model_name="Edwards APG-L",
            data=APG_L_CALIBRATION_DATA,
            v_min=2.0,
            v_max=10.0,
            p_min=1e-6,
            p_max=1000.0,
            atmosphere=atmosphere,
            extrapolate=extrapolate,
        )
