"""
Leybold Vacuum Gauge Subpackage.

This subpackage provides implementations of analog vacuum gauges specific to Leybold models.
It includes a class for converting analog voltage outputs to pressure readings in millibars (mbar)
using an exponential formula tailored to the Leybold TTR 101 N THERMOVAC gauge, with support for
atmospheric gas adjustments.

Classes:
    TTR101NGauge: A vacuum gauge class for the Leybold TTR 101 N THERMOVAC, using an
        exponential conversion formula.

Modules:
    analog: Contains the implementation of the Leybold TTR 101 N THERMOVAC gauge class.
"""

from .analog import TTR101NGauge

__all__ = ["TTR101NGauge"]
