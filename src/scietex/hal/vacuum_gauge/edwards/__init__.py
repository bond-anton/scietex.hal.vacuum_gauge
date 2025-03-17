"""
Edwards Vacuum Gauge Subpackage.

This subpackage provides implementations of analog vacuum gauges specific to Edwards models.
It includes classes for converting analog voltage outputs to pressure readings in millibars (mbar)
using calibration data and atmospheric gas adjustments. The classes are designed for use with
Edwards APG-M and APG-L vacuum gauges, leveraging interpolation-based conversion methods.

Classes:
    APGMGauge: A vacuum gauge class for the Edwards APG-M model, using linear interpolation.
    APGLGauge: A vacuum gauge class for the Edwards APG-L model, using linear interpolation.

Modules:
    analog: Contains the implementation of Edwards-specific vacuum gauge classes.
    calibration_data: Provides calibration data arrays for Edwards APG-M and APG-L models.
"""

from .analog import APGMGauge, APGLGauge

__all__ = ["APGMGauge", "APGLGauge"]
