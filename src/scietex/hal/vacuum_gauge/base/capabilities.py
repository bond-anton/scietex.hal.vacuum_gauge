"""
Vacuum gauge capability model.

A gauge advertises what it can do through a single :class:`GaugeCapabilities`
value, grouped by function rather than by method name. The grouping is
semantic: a driver maps its own vocabulary onto these groups, so a caller can
ask "can this gauge switch a relay?" without knowing whether the underlying
protocol calls it a setpoint, a relay, or a threshold.

The groups are frozen dataclasses so a driver declares them once as a class
attribute and callers cannot mutate them.

Classes:
    PenningCapabilities: Penning (cold cathode) control surface.
    RelayCapabilities: Relay/threshold switching surface.
    CalibrationCapabilities: Two-point adjustment surface.
    DisplayCapabilities: Front-panel display surface.
    FilamentCapabilities: Hot-cathode filament surface.
    GaugeCapabilities: The complete capability set for one gauge.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PenningCapabilities:
    """
    Penning (cold cathode) control surface.

    Attributes:
        state (bool): Whether the Penning gauge can be switched on and off.
        sync (bool): Whether Penning operation can be synchronised with the
            Pirani sensor.
    """

    state: bool = False
    sync: bool = False


@dataclass(frozen=True)
class RelayCapabilities:
    """
    Relay/threshold switching surface.

    A setpoint is one mode of a relay, not a separate capability: a gauge that
    switches on a pressure threshold exposes a relay whose ``modes`` contains
    ``"pressure"``. Protocols with richer relays add their own mode names.

    Attributes:
        count (int): Number of independently configurable relays.
        modes (tuple[str, ...]): Relay modes the gauge accepts. ``"pressure"``
            means the relay switches on a pressure threshold.
        hysteresis (bool): Whether a relay accepts hysteresis settings.
    """

    count: int = 0
    modes: tuple[str, ...] = ()
    hysteresis: bool = False


@dataclass(frozen=True)
class CalibrationCapabilities:
    """
    Two-point adjustment surface.

    Attributes:
        high (bool): Whether the gauge can be adjusted at a high pressure
            reference (atmosphere).
        low (bool): Whether the gauge can be adjusted at a low pressure
            reference (zero).
    """

    high: bool = False
    low: bool = False


@dataclass(frozen=True)
class DisplayCapabilities:
    """
    Front-panel display surface.

    Attributes:
        units (bool): Whether the displayed unit can be changed.
        orientation (bool): Whether the display can be flipped.
        data_source (bool): Whether the displayed sensor can be selected.
    """

    units: bool = False
    orientation: bool = False
    data_source: bool = False


@dataclass(frozen=True)
class FilamentCapabilities:
    """
    Hot-cathode filament surface.

    Attributes:
        control (bool): Whether the filament mode can be set.
        number (bool): Whether the active filament can be read or selected.
    """

    control: bool = False
    number: bool = False


@dataclass(frozen=True)
class GaugeCapabilities:
    """
    The complete capability set for one gauge.

    Every group defaults to "unsupported", so a driver declares only what it
    actually implements.

    Attributes:
        measurement (bool): Whether the gauge reports pressure. Always true for
            a working driver; kept explicit so a caller can treat the whole
            capability set uniformly.
        penning (PenningCapabilities): Penning control surface.
        relay (RelayCapabilities): Relay/threshold switching surface.
        calibration (CalibrationCapabilities): Two-point adjustment surface.
        display (DisplayCapabilities): Front-panel display surface.
        degas (bool): Whether a degas cycle can be started and stopped.
        filament (FilamentCapabilities): Hot-cathode filament surface.
        gas_correction (bool): Whether a per-sensor gas correction factor can be
            set.
        panel_lock (bool): Whether the front panel can be locked.
        controller (bool): Whether the internal controller can be enabled.
        filter (bool): Whether a low-pass filter can be configured.
        digital_logic (bool): Whether digital I/O logic can be configured.
        reset (bool): Whether the gauge supports a factory-default reset.
    """

    measurement: bool = True
    penning: PenningCapabilities = field(default_factory=PenningCapabilities)
    relay: RelayCapabilities = field(default_factory=RelayCapabilities)
    calibration: CalibrationCapabilities = field(default_factory=CalibrationCapabilities)
    display: DisplayCapabilities = field(default_factory=DisplayCapabilities)
    degas: bool = False
    filament: FilamentCapabilities = field(default_factory=FilamentCapabilities)
    gas_correction: bool = False
    panel_lock: bool = False
    controller: bool = False
    filter: bool = False
    digital_logic: bool = False
    reset: bool = False
