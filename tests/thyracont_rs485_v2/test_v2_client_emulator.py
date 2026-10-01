"""
Tests for scietex.hal.vacuum_gauge.Thyracont.rs485.v2.client and emulation modules.

This module tests the ThyracontVacuumGauge client against the ThyracontV2Emulator server, ensuring
correct communication over the Thyracont RS485 V2 protocol for pressure measurement, operating
hours, sensor wear statistics, and identification queries.
"""

import logging
import pytest

# pylint: disable=ungrouped-imports
from scietex.hal.serial import VirtualSerialPair
from scietex.hal.serial.config import ModbusSerialConnectionConfig

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.client import ThyracontVacuumGauge
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import Sensor
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation import ThyracontV2Emulator
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.client import ThyracontVacuumGauge
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import Sensor
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

    client: ThyracontVacuumGauge = ThyracontVacuumGauge(
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

    client: ThyracontVacuumGauge = ThyracontVacuumGauge(
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

    client: ThyracontVacuumGauge = ThyracontVacuumGauge(
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

    client: ThyracontVacuumGauge = ThyracontVacuumGauge(
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

    client: ThyracontVacuumGauge = ThyracontVacuumGauge(
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

    client: ThyracontVacuumGauge = ThyracontVacuumGauge(
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
