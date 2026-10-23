"""
Tests for scietex.hal.vacuum_gauge.Thyracont.rs485.v2.client and emulation modules.

This module tests the ThyracontRS485V2Gauge client against the ThyracontV2Emulator server, ensuring
correct communication over the Thyracont RS485 V2 protocol for pressure measurement, operating
hours, sensor wear statistics, and identification queries.
"""

import logging

import pytest

# pylint: disable=ungrouped-imports
from scietex.hal.serial import VirtualSerialPair
from scietex.hal.serial.config import ModbusSerialConnectionConfig

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.client import ThyracontRS485V2Gauge
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import (
        DisplayOrientation,
        DisplayUnits,
        Sensor,
    )
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation import ThyracontV2Emulator
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.client import ThyracontRS485V2Gauge
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import (
        DisplayOrientation,
        DisplayUnits,
        Sensor,
    )
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation import ThyracontV2Emulator


@pytest.fixture
def logger_fixture():
    """Provide a logger for debugging."""
    return logging.getLogger("test_logger")


# pylint: disable=redefined-outer-name
@pytest.fixture
def vsp_fixture(logger_fixture):
    """Start Virtual Serial Pair."""
    vsp = VirtualSerialPair(logger=logger_fixture)
    vsp.start()
    yield vsp
    vsp.stop()


# pylint: disable=redefined-outer-name
@pytest.fixture
def modbus_config(vsp_fixture):
    """Provide a Modbus serial connection configuration."""
    return [
        ModbusSerialConnectionConfig(
            port=vsp_port,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=1.0,
        )
        for vsp_port in vsp_fixture.serial_ports
    ]


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_get_model(modbus_config, logger_fixture):
    """Test retrieving the gauge model."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    model = await client.get_model()
    assert model == "MTM9D"

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_measure(modbus_config, logger_fixture):
    """Test measuring the default pressure."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )
    emulator.pressure = 1000.0
    pressure = await client.measure()
    assert pressure == pytest.approx(1000.0)

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_get_operating_hours(modbus_config, logger_fixture):
    """Test retrieving operating-hours statistics."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )
    emulator.gauge_hours = 100.0
    emulator.cathode_hours = 2.5
    hours = await client.get_operating_hours()
    assert hours["gauge"] == pytest.approx(100.0)
    assert hours["cathode"] == pytest.approx(2.5)

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_get_sensor_statistics(modbus_config, logger_fixture):
    """Test retrieving Pirani sensor wear statistics."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )
    emulator.wear = 42.0
    emulator.hours_since_zero_adjustment = 100.0
    stats = await client.get_sensor_statistics(Sensor.PIRANI)
    assert stats["wear"] == pytest.approx(42.0)
    assert stats["status"] == "contamination"
    assert stats["hours_since_zero_adjustment"] == pytest.approx(100.0)

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_get_identification(modbus_config, logger_fixture):
    """Test retrieving the identification strings."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )
    assert await client.get_product_name() == "Thyracont MTM9D"
    assert await client.get_device_sn() == "00000000"
    assert await client.get_head_sn() == "00000000"

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_get_measurement_range(modbus_config, logger_fixture):
    """Test retrieving the measurement range."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )
    result = await client.get_measurement_range()
    assert result["high"] == pytest.approx(1000.0)
    assert result["low"] == pytest.approx(0.001)

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_emulator_properties(modbus_config, logger_fixture):
    """Test emulator property getters and setters."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    emulator.pressure = 1.23e-3
    assert emulator.pressure == pytest.approx(1.23e-3)
    emulator.gauge_hours = 10.0
    assert emulator.gauge_hours == pytest.approx(10.0)
    emulator.cathode_hours = 1.5
    assert emulator.cathode_hours == pytest.approx(1.5)
    emulator.wear = 30.0
    assert emulator.wear == pytest.approx(30.0)
    emulator.model = "CUSTOM"
    assert emulator.model == "CUSTOM"

    await emulator.stop()


if __name__ == "__main__":
    pytest.main()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_relay_round_trip(modbus_config, logger_fixture):
    """Test writing and reading a relay through the semantic surface."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    await client.set_relay(1, {"on": 1e-3, "off": 1e-1, "mode": "pressure", "D": 5})
    relay = await client.get_relay(1)
    assert relay is not None
    assert relay["mode"] == "pressure"
    assert relay["on"] == pytest.approx(1e-3)
    assert relay["off"] == pytest.approx(1e-1)
    assert relay["D"] == 5

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_relay_mode_switch(modbus_config, logger_fixture):
    """Test switching a relay to a non-pressure mode."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    await client.set_relay(2, {"mode": "T1"})
    relay = await client.get_relay(2)
    assert relay is not None
    assert relay["mode"] == "T1"

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_display_controls(modbus_config, logger_fixture):
    """Test the display unit, orientation and data-source controls."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    await client.set_display_units("torr")
    assert await client.get_display_units() == DisplayUnits.TORR

    await client.set_display_orientation(1)
    assert await client.get_display_orientation() == DisplayOrientation.GAUGE_DOWN

    await client.rotate_display()
    assert await client.get_display_orientation() == DisplayOrientation.GAUGE_UP

    await client.set_display_data_source(Sensor.PIRANI)
    assert await client.get_display_data_source() == Sensor.PIRANI

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_penning_and_degas(modbus_config, logger_fixture):
    """Test the Penning and degas toggles."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    await client.set_penning(True)
    assert await client.get_penning() is True

    await client.set_degas(True)
    assert await client.get_degas() is True

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_device_controls(modbus_config, logger_fixture):
    """Test panel lock, controller, filament and gas correction."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    await client.set_panel_locked(True)
    assert await client.get_panel_locked() is True

    await client.set_controller_enabled(True)
    assert await client.get_controller_enabled() is True

    await client.set_filament_control(2)
    assert await client.get_filament_control() == 2

    await client.set_gas_correction(Sensor.PIRANI, 1.5)
    assert await client.get_gas_correction(Sensor.PIRANI) == pytest.approx(1.5)

    await client.set_low_pass_filter(Sensor.PIRANI, 3)
    assert await client.get_low_pass_filter(Sensor.PIRANI) == 3

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_reset_to_defaults(modbus_config, logger_fixture):
    """Test that a factory reset restores the control surface."""
    emulator = ThyracontV2Emulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ThyracontRS485V2Gauge = ThyracontRS485V2Gauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    await client.set_display_units("torr")
    await client.set_panel_locked(True)
    await client.set_degas(True)

    await client.reset_to_defaults()

    assert await client.get_display_units() == DisplayUnits.MBAR
    assert await client.get_panel_locked() is False
    assert await client.get_degas() is False

    await emulator.stop()
