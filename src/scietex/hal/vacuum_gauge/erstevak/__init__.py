"""
Erstevak Vacuum Gauge Subpackage.

This subpackage provides implementations of exponential vacuum gauges specific to Erstevak models.
It includes classes for converting analog voltage outputs to pressure readings in millibars (mbar)
using exponential formulas tailored to the Erstevak MTP4D and MTM9D gauges, with support for
atmospheric gas adjustments. The MTM9D model uses pressure-dependent coefficients.

Classes:
    MTP4DGauge: A vacuum gauge class for the Erstevak MTP4D, using a simple exponential formula.
    MTM9DGauge: A vacuum gauge class for the Erstevak MTM9D, using an exponential formula with
        pressure-dependent atmospheric coefficients.

Modules:
    analog: Contains the implementation of the Erstevak MTP4D and MTM9D gauge classes.
"""

from .analog import MTP4DGauge, MTM9DGauge

__all__ = ["MTP4DGauge", "MTM9DGauge"]
