"""
Vacuum gauge protocol.

This module defines the transport-agnostic contract every vacuum gauge driver
implements, plus the capability flags that tell a caller which optional control
operations a given gauge supports. The contract is deliberately minimal: a
driver must be able to connect, disconnect, read the current pressure and
return a snapshot of its readings. Everything else is optional and advertised
through the ``supports_*`` class attributes, so a caller can reject an
unsupported command before dispatching it instead of catching an exception
after the fact.

Classes:
    VacuumGaugeProtocol: The runtime-checkable protocol every gauge driver
        satisfies.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class VacuumGaugeProtocol(Protocol):
    """
    Contract implemented by every vacuum gauge driver.

    The four core methods are mandatory. The ``supports_*`` flags default to
    ``False`` and are overridden by drivers that implement the matching
    control operation; callers must consult them before invoking an optional
    method.

    Attributes:
        label (str): Human-readable gauge label, unique within a service.
        supports_penning (bool): Whether the gauge exposes Penning control.
        supports_setpoint (bool): Whether the gauge exposes setpoints.
        supports_calibration (bool): Whether the gauge exposes calibration.
        supports_atmosphere (bool): Whether the gauge supports atmosphere
            adjustment.
        supports_zero (bool): Whether the gauge supports zero adjustment.
    """

    label: str

    supports_penning: bool = False
    supports_setpoint: bool = False
    supports_calibration: bool = False
    supports_atmosphere: bool = False
    supports_zero: bool = False

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
