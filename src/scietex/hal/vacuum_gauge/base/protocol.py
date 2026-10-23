"""
Vacuum gauge protocol.

This module defines the transport-agnostic contract every vacuum gauge driver
implements, plus the capability model that tells a caller which optional control
operations a given gauge supports. The contract is deliberately minimal: a
driver must be able to connect, disconnect, read the current pressure and
return a snapshot of its readings. Everything else is optional and advertised
through :attr:`VacuumGaugeProtocol.capabilities`, so a caller can reject an
unsupported command before dispatching it instead of catching an exception
after the fact.

The optional methods are named after what they do, not after any one protocol's
vocabulary: ``set_relay`` covers a Modbus setpoint and an RS485 relay alike, and
``adjust_high``/``adjust_low`` cover both a calibration coefficient and a
two-point adjustment. A driver implements the subset its hardware exposes and
declares that subset in its capability set.

Classes:
    VacuumGaugeProtocol: The runtime-checkable protocol every gauge driver
        satisfies.
"""

from typing import Any, Protocol, runtime_checkable

from .capabilities import GaugeCapabilities


@runtime_checkable
class VacuumGaugeProtocol(Protocol):
    """
    Contract implemented by every vacuum gauge driver.

    The four core methods are mandatory. Every optional method raises
    ``NotImplementedError`` by default and is advertised through
    :attr:`capabilities`; callers must consult the capability set before
    invoking one.

    Attributes:
        label (str): Human-readable gauge label, unique within a service.
        capabilities (GaugeCapabilities): What this gauge can do, grouped by
            function.
        measurement_unit (str): The unit ``measure()`` returns, fixed per
            driver.
    """

    label: str

    capabilities: GaugeCapabilities = GaugeCapabilities()
    measurement_unit: str = "mbar"

    @property
    def supports_penning(self) -> bool:
        """Whether the gauge exposes Penning control."""
        return self.capabilities.penning.state

    @property
    def supports_setpoint(self) -> bool:
        """Whether the gauge exposes pressure-threshold switching."""
        return "pressure" in self.capabilities.relay.modes

    @property
    def supports_calibration(self) -> bool:
        """Whether the gauge exposes two-point calibration."""
        return self.capabilities.calibration.high or self.capabilities.calibration.low

    @property
    def supports_atmosphere(self) -> bool:
        """Whether the gauge supports atmosphere adjustment."""
        return self.capabilities.calibration.high

    @property
    def supports_zero(self) -> bool:
        """Whether the gauge supports zero adjustment."""
        return self.capabilities.calibration.low

    async def connect(self) -> None:
        """Open the transport to the gauge."""

    async def close(self) -> None:
        """Close the transport to the gauge."""

    async def measure(self) -> float | None:
        """
        Read the current pressure.

        Returns:
            float | None: Pressure in millibars, or ``None`` when the gauge
                reports no valid reading.
        """

    async def read_data(self) -> dict:
        """
        Read a snapshot of the gauge's current values.

        Returns:
            dict: Field name to value mapping. The exact keys depend on the
                driver; ``pressure`` is always present.
        """

    async def set_penning(self, state: bool) -> None:
        """
        Switch the Penning (cold cathode) gauge on or off.

        Args:
            state: Whether to turn the Penning gauge on.
        """
        raise NotImplementedError

    async def get_penning(self) -> bool:
        """
        Read the Penning gauge state.

        Returns:
            bool: Whether the Penning gauge is on.
        """
        raise NotImplementedError

    async def set_penning_sync(self, state: bool) -> None:
        """
        Enable or disable Penning synchronisation.

        Args:
            state: Whether to enable synchronisation.
        """
        raise NotImplementedError

    async def get_penning_sync(self) -> bool:
        """
        Read the Penning synchronisation state.

        Returns:
            bool: Whether synchronisation is enabled.
        """
        raise NotImplementedError

    async def get_relay(self, index: int) -> dict[str, Any] | None:
        """
        Read one relay's settings.

        Args:
            index: Relay index, 1-based.

        Returns:
            dict[str, Any] | None: Relay settings, or ``None`` when the gauge
                reports no value. A pressure-threshold relay carries ``on`` and
                ``off`` pressures in millibars and ``mode`` set to
                ``"pressure"``; richer protocols add their own keys.
        """
        raise NotImplementedError

    async def set_relay(self, index: int, settings: dict[str, Any]) -> None:
        """
        Write one relay's settings.

        Args:
            index: Relay index, 1-based.
            settings: Relay settings. ``on`` and ``off`` are pressures in
                millibars; ``mode`` defaults to ``"pressure"``.
        """
        raise NotImplementedError

    async def reset_relay(self, index: int) -> None:
        """
        Restore one relay to its factory default.

        Args:
            index: Relay index, 1-based.
        """
        raise NotImplementedError

    async def adjust_high(self, pressure: float | None = None) -> None:
        """
        Adjust the gauge at a high pressure reference.

        Args:
            pressure: Reference pressure in millibars, or ``None`` to let the
                gauge use its current reading.
        """
        raise NotImplementedError

    async def adjust_low(self, pressure: float | None = None) -> None:
        """
        Adjust the gauge at a low pressure reference.

        Args:
            pressure: Reference pressure in millibars, or ``None`` to let the
                gauge use its current reading.
        """
        raise NotImplementedError

    async def get_display_units(self) -> str | None:
        """
        Read the unit shown on the front-panel display.

        Returns:
            str | None: The display unit, or ``None`` when unavailable.
        """
        raise NotImplementedError

    async def set_display_units(self, units: str) -> None:
        """
        Set the unit shown on the front-panel display.

        Args:
            units: The display unit.
        """
        raise NotImplementedError

    async def get_display_orientation(self) -> str | None:
        """
        Read the front-panel display orientation.

        Returns:
            str | None: The orientation, or ``None`` when unavailable.
        """
        raise NotImplementedError

    async def set_display_orientation(self, orientation: str) -> None:
        """
        Set the front-panel display orientation.

        Args:
            orientation: The orientation.
        """
        raise NotImplementedError

    async def rotate_display(self) -> None:
        """Flip the front-panel display to the opposite orientation."""
        raise NotImplementedError

    async def get_display_data_source(self) -> str | None:
        """
        Read which sensor the front-panel display shows.

        Returns:
            str | None: The sensor name, or ``None`` when unavailable.
        """
        raise NotImplementedError

    async def set_display_data_source(self, sensor: str) -> None:
        """
        Select which sensor the front-panel display shows.

        Args:
            sensor: The sensor name.
        """
        raise NotImplementedError

    async def get_degas(self) -> bool:
        """
        Read the degas state.

        Returns:
            bool: Whether degas is running.
        """
        raise NotImplementedError

    async def set_degas(self, state: bool) -> None:
        """
        Start or stop a degas cycle.

        Args:
            state: Whether to run degas.
        """
        raise NotImplementedError

    async def get_filament_control(self) -> str | None:
        """
        Read the filament control mode.

        Returns:
            str | None: The filament mode, or ``None`` when unavailable.
        """
        raise NotImplementedError

    async def set_filament_control(self, mode: int) -> None:
        """
        Set the filament control mode.

        Args:
            mode: The filament mode.
        """
        raise NotImplementedError

    async def get_filament_number(self) -> str | None:
        """
        Read the active filament number.

        Returns:
            str | None: The filament number, or ``None`` when unavailable.
        """
        raise NotImplementedError

    async def get_filament_status(self) -> str | None:
        """
        Read the filament status.

        Returns:
            str | None: The filament status, or ``None`` when unavailable.
        """
        raise NotImplementedError

    async def get_gas_correction(self, sensor: str) -> float | None:
        """
        Read a sensor's gas correction factor.

        Args:
            sensor: The sensor name.

        Returns:
            float | None: The correction factor, or ``None`` when unavailable.
        """
        raise NotImplementedError

    async def set_gas_correction(self, sensor: str, factor: float) -> None:
        """
        Set a sensor's gas correction factor.

        Args:
            sensor: The sensor name.
            factor: The correction factor.
        """
        raise NotImplementedError

    async def get_panel_locked(self) -> bool:
        """
        Read the front-panel lock state.

        Returns:
            bool: Whether the front panel is locked.
        """
        raise NotImplementedError

    async def set_panel_locked(self, locked: bool) -> None:
        """
        Lock or unlock the front panel.

        Args:
            locked: Whether to lock the front panel.
        """
        raise NotImplementedError

    async def get_controller_enabled(self) -> bool:
        """
        Read the internal controller state.

        Returns:
            bool: Whether the controller is enabled.
        """
        raise NotImplementedError

    async def set_controller_enabled(self, enabled: bool) -> None:
        """
        Enable or disable the internal controller.

        Args:
            enabled: Whether to enable the controller.
        """
        raise NotImplementedError

    async def get_low_pass_filter(self, sensor: str) -> int | None:
        """
        Read a sensor's low-pass filter setting.

        Args:
            sensor: The sensor name.

        Returns:
            int | None: The filter setting, or ``None`` when unavailable.
        """
        raise NotImplementedError

    async def set_low_pass_filter(self, sensor: str, level: int) -> None:
        """
        Set a sensor's low-pass filter.

        Args:
            sensor: The sensor name.
            level: The filter level.
        """
        raise NotImplementedError

    async def get_digital_logic(self) -> bool | None:
        """
        Read the digital I/O logic polarity.

        Returns:
            bool | None: The logic polarity, or ``None`` when unavailable.
        """
        raise NotImplementedError

    async def set_digital_logic(self, state: bool) -> None:
        """
        Set the digital I/O logic polarity.

        Args:
            state: The logic polarity.
        """
        raise NotImplementedError

    async def reset_to_defaults(self) -> None:
        """Restore every resettable setting to its factory default."""
        raise NotImplementedError
