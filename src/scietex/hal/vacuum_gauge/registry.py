"""
Vacuum gauge driver registry.

Drivers are advertised through the ``scietex.hal.vacuum_gauge.drivers`` entry
point group declared in this package's ``pyproject.toml``. Consumers (the
vacuum gauge worker, the API plugin) resolve a driver by its entry point name
rather than by a dotted class path, so the stored identifier stays stable when
modules move.

Entry points are read from installed distribution metadata. A driver added to
the source tree only appears after the package is reinstalled.
"""

from importlib.metadata import entry_points
from typing import cast

from .base.protocol import VacuumGaugeProtocol

ENTRY_POINT_GROUP = "scietex.hal.vacuum_gauge.drivers"


def discover_drivers() -> dict[str, type[VacuumGaugeProtocol]]:
    """
    Map every advertised driver's entry point name to its class.

    Returns:
        dict[str, type[VacuumGaugeProtocol]]: Entry point name to driver class,
        sorted by name.

    Raises:
        TypeError: If an entry point resolves to something that is not a class.
    """
    discovered: dict[str, type[VacuumGaugeProtocol]] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        driver = entry_point.load()
        if not isinstance(driver, type):
            raise TypeError(
                f"Entry point {entry_point.name!r} resolved to {type(driver).__name__}, not a class"
            )
        discovered[entry_point.name] = cast(type[VacuumGaugeProtocol], driver)
    return dict(sorted(discovered.items()))


def resolve_driver(name: str) -> type[VacuumGaugeProtocol] | None:
    """
    Resolve a single driver by entry point name.

    Args:
        name: Entry point name, e.g. ``thyracont_modbus_v1``.

    Returns:
        type[VacuumGaugeProtocol] | None: The driver class, or ``None`` when no
        advertised driver carries that name.
    """
    return discover_drivers().get(name)
