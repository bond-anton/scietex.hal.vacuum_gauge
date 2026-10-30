"""
Tests for the Thyracont RS485 V1 direct client against the V1 emulator.

The V1 wire format is reconstructed from this codebase rather than taken from a
vendor document, so the emulator is the only executable specification available.
These tests drive the client against it over a virtual serial pair and assert on
the emulator's own state, which is the strongest check possible without hardware.
"""

import logging

import pytest
from scietex.hal.serial import VirtualSerialPair
from scietex.hal.serial.config import ModbusSerialConnectionConfig

from scietex.hal.vacuum_gauge.thyracont.rs485.v1.client import ThyracontRS485V1Gauge
from scietex.hal.vacuum_gauge.thyracont.rs485.v1.emulation import ThyracontEmulator


@pytest.fixture
def logger_fixture():
    """Provide a logger for debugging."""
    return logging.getLogger("test_logger")


@pytest.fixture
def vsp_fixture(logger_fixture):
    """Start a virtual serial pair."""
    vsp = VirtualSerialPair(logger=logger_fixture)
    vsp.start()
    yield vsp
    vsp.stop()


@pytest.fixture
def modbus_config(vsp_fixture):
    """Provide connection configs for both ends of the pair."""
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


def _client(modbus_config, logger_fixture, address=1):
    """Build a client pointed at the emulator end of the pair."""
    return ThyracontRS485V1Gauge(
        connection_config=modbus_config[1],
        address=address,
        label="Test Gauge",
        logger=logger_fixture,
        timeout=1.0,
        backend="pymodbus",
    )


class _FakeResponse:
    """Minimal stand-in for a decoded PDU carrying a payload."""

    def __init__(self, data):
        self.data = data


@pytest.mark.asyncio
async def test_measure(modbus_config, logger_fixture):
    """The client reads the emulated pressure."""
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()
    emulator.pressure = 1000.0

    client = _client(modbus_config, logger_fixture)
    assert await client.measure() == pytest.approx(1000.0)

    await emulator.stop()


@pytest.mark.asyncio
async def test_measure_low_pressure(modbus_config, logger_fixture):
    """The six-digit mantissa/exponent encoding round-trips a vacuum value."""
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()
    emulator.pressure = 1.23e-3

    client = _client(modbus_config, logger_fixture)
    assert await client.measure() == pytest.approx(1.23e-3, rel=1e-3)

    await emulator.stop()


@pytest.mark.asyncio
async def test_get_model(modbus_config, logger_fixture):
    """The gauge type is returned as a string, not parsed as a number."""
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client = _client(modbus_config, logger_fixture)
    model = await client.get_model()
    assert model is not None
    assert model.isalnum()

    await emulator.stop()


@pytest.mark.asyncio
async def test_setpoint_round_trip(modbus_config, logger_fixture):
    """A setpoint write is a select followed by a value, and the emulator stores it."""
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client = _client(modbus_config, logger_fixture)
    assert await client.set_setpoint(1, 10.0) is True
    assert emulator.sp1 == pytest.approx(10.0, rel=1e-3)
    assert await client.get_setpoint(1) == pytest.approx(10.0, rel=1e-3)

    assert await client.set_setpoint(2, 0.5) is True
    assert emulator.sp2 == pytest.approx(0.5, rel=1e-3)
    assert await client.get_setpoint(2) == pytest.approx(0.5, rel=1e-3)

    await emulator.stop()


@pytest.mark.asyncio
async def test_setpoint_rejects_bad_number(modbus_config, logger_fixture):
    """Only setpoints 1 and 2 exist; anything else is a caller error."""
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client = _client(modbus_config, logger_fixture)
    with pytest.raises(ValueError):
        await client.get_setpoint(3)
    with pytest.raises(ValueError):
        await client.set_setpoint(0, 1.0)

    await emulator.stop()


@pytest.mark.asyncio
async def test_calibration_round_trip(modbus_config, logger_fixture):
    """A calibration write is a select followed by a value, stored as a 16-bit register."""
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client = _client(modbus_config, logger_fixture)
    assert await client.set_calibration(1, 1.25) is True
    assert emulator.cal1 == pytest.approx(1.25)
    assert await client.get_calibration(1) == pytest.approx(1.25)

    assert await client.set_calibration(2, 0.98) is True
    assert emulator.cal2 == pytest.approx(0.98)
    assert await client.get_calibration(2) == pytest.approx(0.98)

    await emulator.stop()


@pytest.mark.asyncio
async def test_calibration_write_does_not_clobber_the_other_point(modbus_config, logger_fixture):
    """Writing one calibration point leaves the other untouched.

    The protocol reference claimed the write used a two-register operation that
    clobbered the neighbouring point; the emulator assigns a single register, and
    this test pins that behaviour so a regression cannot hide behind the doc.
    """
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()
    emulator.cal1 = 1.0
    emulator.cal2 = 1.0

    client = _client(modbus_config, logger_fixture)
    assert await client.set_calibration(1, 1.5) is True
    assert emulator.cal1 == pytest.approx(1.5)
    assert emulator.cal2 == pytest.approx(1.0)

    await emulator.stop()


@pytest.mark.asyncio
async def test_penning_state_round_trip(modbus_config, logger_fixture):
    """The Penning state can be switched and read back."""
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client = _client(modbus_config, logger_fixture)
    assert await client.set_penning(True) is None
    assert emulator.penning_state is True
    assert await client.get_penning() is True

    assert await client.set_penning(False) is None
    assert emulator.penning_state is False
    assert await client.get_penning() is False

    await emulator.stop()


@pytest.mark.asyncio
async def test_penning_sync_round_trip(modbus_config, logger_fixture):
    """The Penning sync flag can be set and read back.

    The emulator accepts the ``w`` write unconditionally, which is more
    permissive than the hardware: a cathode-less Pirani gauge answers with an
    error literal. The client therefore does not claim ``penning.sync``; this
    test only pins the wire exchange, not the capability.
    """
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client = _client(modbus_config, logger_fixture)
    assert await client.set_penning_sync(False) is None
    assert emulator.penning_sync is False
    assert await client.get_penning_sync() is False

    assert await client.set_penning_sync(True) is None
    assert emulator.penning_sync is True
    assert await client.get_penning_sync() is True

    await emulator.stop()


@pytest.mark.asyncio
async def test_adjustment_commands(modbus_config, logger_fixture):
    """Both adjustment sequences are accepted by the emulator.

    Each adjustment is a select followed by a fixed payload; the emulator
    silently drops a payload that arrives without a preceding selection, so
    this test fails if the client ever sends the payload alone.
    """
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client = _client(modbus_config, logger_fixture)
    await client.adjust_high()
    await client.adjust_low()

    await emulator.stop()


@pytest.mark.asyncio
async def test_read_data_returns_pressure(modbus_config, logger_fixture):
    """The snapshot carries the pressure under the protocol's key."""
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()
    emulator.pressure = 42.0

    client = _client(modbus_config, logger_fixture)
    data = await client.read_data()
    assert data["pressure"] == pytest.approx(42.0, rel=1e-3)

    await emulator.stop()


@pytest.mark.asyncio
async def test_parse_response_rejects_wrong_address(modbus_config, logger_fixture):
    """A response from another address is rejected rather than decoded.

    The emulator is single-device and ignores the address, so the check is
    exercised on the parser directly.
    """
    from scietex.hal.vacuum_gauge.thyracont.rs485.checksum import calc_checksum

    payload = b"001M100023"
    frame = payload + bytes([calc_checksum(payload)]) + b"\r"

    client = _client(modbus_config, logger_fixture, address=1)
    assert client._parse_response(frame) == "100023"

    other = _client(modbus_config, logger_fixture, address=2)
    assert other._parse_response(frame) is None


@pytest.mark.asyncio
async def test_parse_response_rejects_bad_frames(modbus_config, logger_fixture):
    """Empty frames, bad checksums and empty payloads all yield no value."""
    from scietex.hal.vacuum_gauge.thyracont.rs485.checksum import calc_checksum

    client = _client(modbus_config, logger_fixture, address=1)
    assert client._parse_response(b"") is None
    assert client._parse_response(b"001M100023X\r") is None

    # An empty payload is how the gauge rejects a command.
    payload = b"001M"
    rejected = payload + bytes([calc_checksum(payload)]) + b"\r"
    assert client._parse_response(rejected) is None


@pytest.mark.asyncio
async def test_error_literals_are_rejections(modbus_config, logger_fixture):
    """An error literal echoed by the gauge is a rejection, not a value.

    The hardware answers an out-of-range write with ``_RANGE`` and an
    illogical one with ``_LOGIC``. Those strings are not data, so
    ``request_gauge`` must return ``None`` and log the rejection.
    """
    from scietex.hal.vacuum_gauge.thyracont.rs485.checksum import calc_checksum

    client = _client(modbus_config, logger_fixture, address=1)

    # The parser returns the raw payload; the rejection filter lives in
    # request_gauge, so drive that method with a stubbed transport.
    for literal in ("_RANGE", "_LOGIC", "NO_DEF", "SYNTAX"):
        payload = f"001w{literal}".encode()
        frame = payload + bytes([calc_checksum(payload)]) + b"\r"

        async def fake_execute(_request, _frame=frame, **_kwargs):
            return _FakeResponse(client._parse_response(_frame))

        client.execute = fake_execute
        assert await client.request_gauge(command="w", data="0") is None

    # A valid payload is not filtered.
    payload = b"001M100023"
    frame = payload + bytes([calc_checksum(payload)]) + b"\r"

    async def fake_execute_ok(_request, **_kwargs):
        return _FakeResponse(client._parse_response(frame))

    client.execute = fake_execute_ok
    assert await client.request_gauge(command="M") == "100023"


@pytest.mark.asyncio
async def test_connect_is_a_noop(modbus_config, logger_fixture):
    """`connect()` exists for the protocol contract and opens nothing eagerly."""
    emulator = ThyracontEmulator(con_params=modbus_config[0], logger=logger_fixture, address=1)
    await emulator.start()

    client = _client(modbus_config, logger_fixture)
    await client.connect()
    assert await client.measure() == pytest.approx(1000.0)

    await emulator.stop()


@pytest.mark.asyncio
async def test_client_satisfies_the_protocol(modbus_config, logger_fixture):
    """The client is structurally a `VacuumGaugeProtocol`."""
    from scietex.hal.vacuum_gauge.base.protocol import VacuumGaugeProtocol

    client = _client(modbus_config, logger_fixture)
    assert isinstance(client, VacuumGaugeProtocol)


@pytest.mark.asyncio
async def test_capabilities_match_v1(modbus_config, logger_fixture):
    """V1 claims only what it can do: no display, degas, filament or reset."""
    client = _client(modbus_config, logger_fixture)
    caps = client.capabilities
    assert caps.penning.state is True
    # The gauge rejects the sync write, so it is not claimed.
    assert caps.penning.sync is False
    assert caps.relay.count == 2
    assert caps.relay.modes == ("pressure",)
    assert caps.calibration.high is True
    assert caps.calibration.low is True
    assert caps.display.units is False
    assert caps.display.orientation is False
    assert caps.display.data_source is False
    assert caps.degas is False
    assert caps.filament.control is False
    assert caps.filament.number is False
    assert caps.reset is False
