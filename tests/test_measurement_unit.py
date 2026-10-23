"""
Tests for the ``measurement_unit`` class attribute.

Every driver that produces a pressure value declares ``measurement_unit``, the
unit its ``measure()`` returns. This module asserts the attribute is declared
with the value ``"mbar"`` on the protocol, the Thyracont protocol drivers, the
analog converter bases, and the Erstevak subclasses (which inherit it from
Thyracont rather than redeclaring it).
"""

import pytest

# The fallback branch imports the installed package while the primary branch
# imports from src/, so pylint cannot group them.
# pylint: disable=ungrouped-imports
try:
    from src.scietex.hal.vacuum_gauge.base.analog import (
        ExponentialVacuumGauge,
        InterpolationVacuumGauge,
    )
    from src.scietex.hal.vacuum_gauge.base.protocol import VacuumGaugeProtocol
    from src.scietex.hal.vacuum_gauge.erstevak.modbus.v1.client import (
        ErstevakModbusV1Gauge,
    )
    from src.scietex.hal.vacuum_gauge.erstevak.modbus.v2.client import (
        ErstevakModbusV2Gauge,
    )
    from src.scietex.hal.vacuum_gauge.thyracont.modbus.v1.client import (
        ThyracontModbusV1Gauge,
    )
    from src.scietex.hal.vacuum_gauge.thyracont.modbus.v2.client import (
        ThyracontModbusV2Gauge,
    )
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v1.client import (
        ThyracontRS485V1Gauge,
    )
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.client import (
        ThyracontRS485V2Gauge,
    )
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.base.analog import (
        ExponentialVacuumGauge,
        InterpolationVacuumGauge,
    )
    from scietex.hal.vacuum_gauge.base.protocol import VacuumGaugeProtocol
    from scietex.hal.vacuum_gauge.erstevak.modbus.v1.client import ErstevakModbusV1Gauge
    from scietex.hal.vacuum_gauge.erstevak.modbus.v2.client import ErstevakModbusV2Gauge
    from scietex.hal.vacuum_gauge.thyracont.modbus.v1.client import ThyracontModbusV1Gauge
    from scietex.hal.vacuum_gauge.thyracont.modbus.v2.client import ThyracontModbusV2Gauge
    from scietex.hal.vacuum_gauge.thyracont.rs485.v1.client import (
        ThyracontRS485V1Gauge,
    )
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.client import (
        ThyracontRS485V2Gauge,
    )


def test_protocol_declares_mbar_default():
    """The protocol declares ``mbar`` as the default measurement unit."""
    assert VacuumGaugeProtocol.measurement_unit == "mbar"


def test_protocol_measurement_unit_is_a_member():
    """``measurement_unit`` is a protocol member, not stripped by ``ClassVar``."""
    assert "measurement_unit" in VacuumGaugeProtocol.__annotations__


@pytest.mark.parametrize(
    "gauge_class",
    [
        ThyracontModbusV1Gauge,
        ThyracontModbusV2Gauge,
        ThyracontRS485V1Gauge,
        ThyracontRS485V2Gauge,
    ],
)
def test_thyracont_drivers_declare_mbar(gauge_class):
    """Every Thyracont protocol driver declares ``measurement_unit = "mbar"``."""
    assert gauge_class.measurement_unit == "mbar"


@pytest.mark.parametrize(
    "converter_class",
    [ExponentialVacuumGauge, InterpolationVacuumGauge],
)
def test_analog_converters_declare_mbar(converter_class):
    """Both analog voltage->pressure converters declare ``"mbar"``."""
    assert converter_class.measurement_unit == "mbar"


def test_erstevak_inherits_measurement_unit():
    """Erstevak gauges inherit ``measurement_unit`` from Thyracont."""
    assert ErstevakModbusV1Gauge.measurement_unit == "mbar"
    assert ErstevakModbusV2Gauge.measurement_unit == "mbar"
    assert "measurement_unit" not in ErstevakModbusV1Gauge.__dict__
    assert "measurement_unit" not in ErstevakModbusV2Gauge.__dict__
