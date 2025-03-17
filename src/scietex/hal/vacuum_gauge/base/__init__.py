"""
Base Vacuum Gauge Subpackage.

This subpackage provides foundational classes and utilities for working with analog vacuum gauges.
It includes abstract and concrete implementations for converting analog voltage outputs to pressure
readings in millibars (mbar), supporting various atmospheric gases and customizable gauge
parameters. These components serve as building blocks for specific gauge implementations
(e.g., in the `edwards` subpackage).

Classes:
    Atmosphere: An enumeration of supported atmospheric gases for pressure conversion adjustments.
    ExponentialVacuumGauge: An abstract base class for vacuum gauges with exponential output.
    InterpolationVacuumGauge: A class for vacuum gauges using linear interpolation based on
        calibration data.

Modules:
    atmosphere: Defines the `Atmosphere` enumeration for gas type handling.
    analog: Contains the core vacuum gauge classes `ExponentialVacuumGauge` and
        `InterpolationVacuumGauge`.
"""

from .atmosphere import Atmosphere
from .analog import ExponentialVacuumGauge, InterpolationVacuumGauge

__all__ = ["Atmosphere", "ExponentialVacuumGauge", "InterpolationVacuumGauge"]
