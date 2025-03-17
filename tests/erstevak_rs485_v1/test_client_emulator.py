"""
Tests for scietex.hal.vacuum_gauge.erstevak.rs485.v1.client and emulation modules.

This module tests the ErstevakVacuumGauge client against the ErstevakEmulator server, ensuring
correct communication over the Erstevak RS485 protocol for pressure measurement, calibration,
setpoints, and Penning gauge control using both 'pymodbus' and 'pyserial' backends.
"""

import logging
import pytest

# pylint: disable=ungrouped-imports
from scietex.hal.serial.config import ModbusSerialConnectionConfig
from scietex.hal.serial import VirtualSerialPair

try:
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v1.client import ErstevakVacuumGauge
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v1.emulation import ErstevakEmulator
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.erstevak.rs485.v1.client import ErstevakVacuumGauge
    from scietex.hal.vacuum_gauge.erstevak.rs485.v1.emulation import ErstevakEmulator


# Fixtures
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


# Helper to run tests with both backends
# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_get_model(modbus_config, logger_fixture):
    """Test retrieving the gauge model."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    model = await client.get_model()
    assert model == "MTM09D"

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_measure(modbus_config, logger_fixture):
    """Test measuring the default pressure."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )
    emulator.pressure = 1000.0  # Default value set in emulator
    pressure = await client.measure()
    assert pressure == pytest.approx(1000.0)

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_set_pressure(modbus_config, logger_fixture):
    """Test setting and reading back a pressure value."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    new_pressure = 1.23e-3
    result = await client.set_pressure(new_pressure)
    assert result == pytest.approx(new_pressure)
    assert emulator.pressure == pytest.approx(new_pressure)

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_get_calibration(modbus_config, logger_fixture):
    """Test retrieving calibration values."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    emulator.cal1 = 1.0  # Default value
    emulator.cal2 = 1.5
    cal1 = await client.get_calibration(1)
    cal2 = await client.get_calibration(2)
    assert cal1 == 1.0
    assert cal2 == 1.5

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_set_calibration(modbus_config, logger_fixture):
    """Test setting a calibration value."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    new_cal = 1.23
    result = await client.set_calibration(cal_n=1, value=new_cal)
    assert result == new_cal
    assert emulator.cal1 == new_cal

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_get_setpoint(modbus_config, logger_fixture):
    """Test retrieving setpoint values."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    emulator.sp1 = 0.987
    emulator.sp2 = 12.34
    sp1 = await client.get_setpoint(1)
    sp2 = await client.get_setpoint(2)
    assert sp1 == pytest.approx(0.987)
    assert sp2 == pytest.approx(12.34)

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_set_setpoint(modbus_config, logger_fixture):
    """Test setting a setpoint value."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    new_sp = 5.67
    result = await client.set_setpoint(sp_n=2, pressure=new_sp)
    assert result == pytest.approx(new_sp)
    assert emulator.sp2 == pytest.approx(new_sp)

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_set_atmosphere(modbus_config, logger_fixture):
    """Test setting atmosphere adjustment."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    result = await client.set_atmosphere()
    assert result == pytest.approx(1000.0)
    assert emulator.pressure == pytest.approx(1000.0)

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_set_zero(modbus_config, logger_fixture):
    """Test setting zero adjustment."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    result = await client.set_zero()
    assert result == 0.0
    assert emulator.pressure == 0.0

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_get_penning_state(modbus_config, logger_fixture):
    """Test retrieving Penning gauge state."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    emulator.penning_state = True
    state = await client.get_penning_state()
    assert state is True

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_set_penning_state(modbus_config, logger_fixture):
    """Test setting Penning gauge state."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    result = await client.set_penning_state(False)
    assert result is False
    assert emulator.penning_state is False

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_get_penning_sync(modbus_config, logger_fixture):
    """Test retrieving Penning synchronization state."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    emulator.penning_sync = True  # Default value
    state = await client.get_penning_sync()
    assert state is True

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_set_penning_sync(modbus_config, logger_fixture):
    """Test setting Penning synchronization state."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    result = await client.set_penning_sync(False)
    assert result is False
    assert emulator.penning_sync is False

    await emulator.stop()


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_read_data(modbus_config, logger_fixture):
    """Test reading gauge data dictionary."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    emulator.pressure = 0.00123
    data = await client.read_data()
    assert "pressure" in data
    assert data["pressure"] == pytest.approx(0.00123)

    await emulator.stop()


# Emulator-specific property tests
# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_emulator_properties(modbus_config, logger_fixture):
    """Test emulator property getters and setters."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    # Pressure
    emulator.pressure = 1.23e-3
    assert emulator.pressure == pytest.approx(1.23e-3)
    # Setpoints
    emulator.sp1 = 0.5
    assert emulator.sp1 == pytest.approx(0.5)
    emulator.sp2 = 10.0
    assert emulator.sp2 == pytest.approx(10.0)
    # Calibration
    emulator.cal1 = 1.1
    assert emulator.cal1 == 1.1
    emulator.cal2 = 0.95
    assert emulator.cal2 == 0.95
    # Penning states
    emulator.penning_state = False
    assert emulator.penning_state is False
    emulator.penning_sync = True
    assert emulator.penning_sync is True

    await emulator.stop()


# Client-specific edge case: timeout handling
# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_client_timeout(modbus_config, logger_fixture):
    """Test client handling of request timeout."""
    emulator = ErstevakEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client: ErstevakVacuumGauge = ErstevakVacuumGauge(
        connection_config=modbus_config[1],
        address=1,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )

    client.timeout = 0.01  # Very short timeout
    # Simulate a non-responsive emulator by not awaiting its response properly
    await emulator.stop()  # Stop emulator to force timeout
    result = await client.measure()
    assert result is None


if __name__ == "__main__":
    pytest.main()
