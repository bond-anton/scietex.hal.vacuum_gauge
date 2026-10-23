"""
Tests for the driver entry point registry.

Drivers are advertised through the ``scietex.hal.vacuum_gauge.drivers`` entry
point group. These tests assert the advertised set, that every entry point
resolves to a gauge class carrying a ``display_name``, and that unknown names
resolve to ``None``.
"""

import pytest

# The fallback branch imports the installed package while the primary branch
# imports from src/, so pylint cannot group them.
# pylint: disable=ungrouped-imports
try:
    from src.scietex.hal.vacuum_gauge.registry import (
        ENTRY_POINT_GROUP,
        discover_drivers,
        resolve_driver,
    )
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.registry import (
        ENTRY_POINT_GROUP,
        discover_drivers,
        resolve_driver,
    )

_EXPECTED_NAMES = {
    "erstevak_modbus_v1",
    "erstevak_modbus_v2",
    "erstevak_rs485_v2",
    "thyracont_modbus_v1",
    "thyracont_modbus_v2",
    "thyracont_rs485_v2",
}


def test_entry_point_group_name():
    """The group name is the documented constant."""
    assert ENTRY_POINT_GROUP == "scietex.hal.vacuum_gauge.drivers"


def test_discover_drivers_returns_expected_names():
    """Every advertised driver is discovered under its entry point name."""
    assert set(discover_drivers()) == _EXPECTED_NAMES


def test_discover_drivers_is_sorted():
    """Discovery returns names in sorted order for stable presentation."""
    names = list(discover_drivers())
    assert names == sorted(names)


@pytest.mark.parametrize("name", sorted(_EXPECTED_NAMES))
def test_every_driver_is_a_gauge_class_with_display_name(name):
    """Each entry point resolves to a gauge class declaring a display name."""
    driver = resolve_driver(name)
    assert driver is not None
    # ``issubclass`` is unavailable: the protocol has non-method members.
    assert hasattr(driver, "capabilities")
    assert hasattr(driver, "measurement_unit")
    assert isinstance(driver.display_name, str)
    assert driver.display_name


def test_display_names_are_unique():
    """Display names are distinct, so the picker never shows duplicates."""
    names = [driver.display_name for driver in discover_drivers().values()]
    assert len(names) == len(set(names))


def test_resolve_unknown_driver_returns_none():
    """An unadvertised name resolves to ``None`` rather than raising."""
    assert resolve_driver("no_such_driver") is None
