"""
Calibration Data for Edwards APG Vacuum Gauges.

This module defines calibration data constants for Edwards APG-M and APG-L vacuum gauge models.
Each constant is a NumPy array with shape (n, 2), where the first column represents voltage
readings (in volts) and the second column represents corresponding pressure values (in mbar).
These datasets can be used for interpolating pressure from voltage measurements in vacuum systems.

Constants:
    APG_M_CALIBRATION_DATA : Calibration data for the Edwards APG-M gauge model.
    APG_L_CALIBRATION_DATA : Calibration data for the Edwards APG-L gauge model.

Notes:
    - The data spans a range of voltages from 2.0 to 10.0 volts.
    - Pressure values are provided in scientific notation, covering a wide range from high vacuum
      (e.g., 1e-6 mbar) to near-atmospheric pressure (e.g., 1000 mbar).
    - These arrays are suitable for use with interpolation methods
      (e.g., from `scietex.hal.analog_sensor`).
"""

import numpy as np


APG_M_CALIBRATION_DATA = np.array(
    [
        [2.00e00, 1.00e-05],
        [2.05e00, 2.31e-04],
        [2.10e00, 6.21e-04],
        [2.20e00, 1.36e-03],
        [2.40e00, 2.97e-03],
        [2.60e00, 4.61e-03],
        [2.80e00, 6.51e-03],
        [3.00e00, 1.02e-02],
        [3.20e00, 1.47e-02],
        [3.40e00, 1.91e-02],
        [3.60e00, 2.95e-02],
        [3.80e00, 4.16e-02],
        [4.00e00, 5.61e-02],
        [4.20e00, 7.20e-02],
        [4.40e00, 8.94e-02],
        [4.60e00, 1.13e-01],
        [4.80e00, 1.45e-01],
        [5.00e00, 1.76e-01],
        [5.20e00, 2.22e-01],
        [5.40e00, 3.16e-01],
        [5.60e00, 4.13e-01],
        [5.80e00, 5.40e-01],
        [6.00e00, 6.82e-01],
        [6.20e00, 8.41e-01],
        [6.40e00, 1.06e00],
        [6.60e00, 1.33e00],
        [6.80e00, 1.60e00],
        [7.00e00, 1.87e00],
        [7.20e00, 2.26e00],
        [7.40e00, 2.75e00],
        [7.60e00, 3.24e00],
        [7.80e00, 3.73e00],
        [8.00e00, 4.39e00],
        [8.20e00, 5.29e00],
        [8.40e00, 6.27e00],
        [8.60e00, 7.63e00],
        [8.80e00, 9.39e00],
        [9.00e00, 1.27e01],
        [9.20e00, 1.67e01],
        [9.40e00, 2.24e01],
        [9.50e00, 2.88e01],
        [9.60e00, 3.53e01],
        [9.70e00, 4.48e01],
        [9.80e00, 6.65e01],
        [9.90e00, 1.41e02],
        [9.95e00, 6.16e02],
        [1.00e01, 1.00e03],
    ]
)
"""Calibration data for the Edwards APG-M vacuum gauge.

A NumPy array of shape (47, 2) containing voltage-pressure pairs:
- Column 0: Voltage readings (in volts), ranging from 2.0 to 10.0.
- Column 1: Corresponding pressure values (in millibars, mbar), ranging from 1e-5 to 1000.
"""


APG_L_CALIBRATION_DATA = np.array(
    [
        [2.00e00, 1.00e-06],
        [2.05e00, 8.26e-05],
        [2.10e00, 2.27e-04],
        [2.20e00, 5.00e-04],
        [2.40e00, 1.08e-03],
        [2.60e00, 1.68e-03],
        [2.80e00, 2.60e-03],
        [3.00e00, 3.84e-03],
        [3.20e00, 5.15e-03],
        [3.40e00, 6.87e-03],
        [3.60e00, 1.05e-02],
        [3.80e00, 1.56e-02],
        [4.00e00, 2.10e-02],
        [4.20e00, 2.77e-02],
        [4.40e00, 3.45e-02],
        [4.60e00, 4.16e-02],
        [4.80e00, 5.04e-02],
        [5.00e00, 5.92e-02],
        [5.20e00, 8.74e-02],
        [5.40e00, 1.27e-01],
        [5.60e00, 1.71e-01],
        [5.80e00, 2.23e-01],
        [6.00e00, 2.90e-01],
        [6.20e00, 3.57e-01],
        [6.40e00, 4.35e-01],
        [6.60e00, 5.33e-01],
        [6.80e00, 6.40e-01],
        [7.00e00, 7.67e-01],
        [7.20e00, 9.23e-01],
        [7.40e00, 1.14e00],
        [7.60e00, 1.40e00],
        [7.80e00, 1.66e00],
        [8.00e00, 1.92e00],
        [8.20e00, 2.38e00],
        [8.40e00, 2.95e00],
        [8.60e00, 3.51e00],
        [8.80e00, 4.17e00],
        [9.00e00, 5.40e00],
        [9.20e00, 7.06e00],
        [9.40e00, 9.69e00],
        [9.50e00, 1.29e01],
        [9.60e00, 1.66e01],
        [9.70e00, 2.07e01],
        [9.80e00, 3.39e01],
        [9.90e00, 6.32e01],
        [9.95e00, 1.44e02],
        [1.00e01, 1.00e03],
    ]
)
"""Calibration data for the Edwards APG-L vacuum gauge.

A NumPy array of shape (47, 2) containing voltage-pressure pairs:
- Column 0: Voltage readings (in volts), ranging from 2.0 to 10.0.
- Column 1: Corresponding pressure values (in millibars, mbar), ranging from 1e-6 to 1000.
"""
