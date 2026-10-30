"""
Tests for the Erstevak RS485 V2 capability claim.

The Erstevak V2 driver subclasses the Thyracont one, so it inherits the command
surface. It must not inherit the capability claim: the Thyracont claim describes
a full-featured gauge with a cold cathode, a hot-cathode filament and a degas
cycle, and the Erstevak gauges this driver serves are single-sensor Pirani
instruments. These tests pin the narrower claim so a future inheritance change
cannot silently widen it.
"""

from scietex.hal.vacuum_gauge.erstevak.rs485.v2.client import ErstevakRS485V2Gauge
from scietex.hal.vacuum_gauge.thyracont.rs485.v2.client import ThyracontRS485V2Gauge


def test_erstevak_overrides_the_inherited_claim():
    """The subclass declares its own capability set rather than inheriting one."""
    assert "capabilities" in ErstevakRS485V2Gauge.__dict__


def test_erstevak_claims_no_cold_cathode():
    """A Pirani gauge has no cold cathode, so Penning control is not claimed."""
    caps = ErstevakRS485V2Gauge.capabilities
    assert caps.penning.state is False
    assert caps.penning.sync is False


def test_erstevak_claims_no_filament_or_degas():
    """A Pirani gauge has no hot cathode, so filament and degas are not claimed."""
    caps = ErstevakRS485V2Gauge.capabilities
    assert caps.filament.control is False
    assert caps.filament.number is False
    assert caps.degas is False


def test_erstevak_keeps_the_shared_surface():
    """The features a Pirani gauge does have stay claimed."""
    caps = ErstevakRS485V2Gauge.capabilities
    assert caps.measurement is True
    assert caps.relay.count == 2
    assert caps.calibration.high is True
    assert caps.calibration.low is True
    assert caps.display.units is True
    assert caps.reset is True


def test_erstevak_claim_is_narrower_than_thyracont():
    """Every group the Erstevak claim drops is one the Thyracont claim has."""
    erstevak = ErstevakRS485V2Gauge.capabilities
    thyracont = ThyracontRS485V2Gauge.capabilities
    assert thyracont.penning.state is True and erstevak.penning.state is False
    assert thyracont.degas is True and erstevak.degas is False
    assert thyracont.filament.control is True and erstevak.filament.control is False
