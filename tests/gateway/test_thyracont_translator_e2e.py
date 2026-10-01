"""
End-to-end tests of the Thyracont gateway translators.

A standard Modbus/TCP client reads and writes holding registers through the real
`ModbusGateway` (scietex.hal.serial v2.0.0). The gateway translates FC03/FC06/FC16
into the Thyracont vendor protocol, sends it over a virtual serial pair to a real
Thyracont emulator, and translates the response back.

Both protocol versions are covered: v1 (command-oriented, raw-int registers) and
v2 (read-only float32 register pairs).
"""

import struct

import pytest
from pymodbus.client import AsyncModbusTcpClient

from scietex.hal.serial.gateway.config import GatewayConfig, GatewayDeviceConfig
from scietex.hal.serial.gateway.gateway import ModbusGateway
from scietex.hal.serial.gateway.tcp_server import GatewayTcpServer
from scietex.hal.serial.utilities.numeric import combine_32bit, split_32bit

# pylint: disable=ungrouped-imports
try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v1.data import _pressure_encode
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v1.emulation import ThyracontEmulator
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation import ThyracontV2Emulator
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v1.data import _pressure_encode
    from scietex.hal.vacuum_gauge.thyracont.rs485.v1.emulation import ThyracontEmulator
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation import ThyracontV2Emulator

# Dotted paths to the installed plugin artifacts. The gateway resolves these via
# importlib, so they must be the installed package paths, not ``src.*`` paths.
_V1_FRAMER = "scietex.hal.vacuum_gauge.thyracont.rs485.v1.framer.ThyracontASCIIFramer"
_V1_DECODER = "scietex.hal.vacuum_gauge.thyracont.rs485.v1.decoder.ThyracontDecodePDU"
_V1_PDU = "scietex.hal.vacuum_gauge.thyracont.rs485.v1.request.ThyracontRequest"
_V1_TRANSLATOR = "scietex.hal.vacuum_gauge.thyracont.rs485.v1.translator.ThyracontV1Translator"
_V2_FRAMER = "scietex.hal.vacuum_gauge.thyracont.rs485.v2.framer.ThyracontASCIIFramer"
_V2_DECODER = "scietex.hal.vacuum_gauge.thyracont.rs485.v2.decoder.ThyracontDecodePDU"
_V2_PDU = "scietex.hal.vacuum_gauge.thyracont.rs485.v2.request.ThyracontRequest"
_V2_TRANSLATOR = "scietex.hal.vacuum_gauge.thyracont.rs485.v2.translator.ThyracontV2Translator"

_V1_PLUGINS = (_V1_FRAMER, _V1_DECODER, _V1_PDU, _V1_TRANSLATOR)
_V2_PLUGINS = (_V2_FRAMER, _V2_DECODER, _V2_PDU, _V2_TRANSLATOR)


def _gateway_stack(serial, port, plugins, logger):
    """Build an (unstarted) gateway and TCP server wired to a Thyracont plugin.

    Args:
        serial: Serial connection config for the gateway bus.
        port: TCP listen port.
        plugins: ``(framer, decoder, pdu, translator)`` dotted-path strings.
        logger: Logger instance.

    Returns:
        A ``(gateway, server, port)`` tuple.
    """
    framer, decoder, pdu, translator = plugins
    config = GatewayConfig(
        serial=serial,
        host="127.0.0.1",
        port=port,
        devices={
            1: GatewayDeviceConfig(
                device_id=1,
                framer=framer,
                decoder=decoder,
                pdus=[pdu],
                translator=translator,
            )
        },
    )
    gateway = ModbusGateway(config, logger=logger)
    server = GatewayTcpServer(config, gateway, logger=logger)
    return gateway, server, port


def _decode_float32(registers: list[int]) -> float:
    """Decode two big-endian 16-bit registers into an IEEE-754 float32."""
    word = (registers[0] << 16) | registers[1]
    return struct.unpack(">f", struct.pack(">I", word))[0]


# pylint: disable=redefined-outer-name
@pytest.fixture
def v1_stack(modbus_config, logger_fixture, free_port):
    """A v1 emulator plus a gateway/TCP server sharing one virtual serial pair."""
    emulator = ThyracontEmulator(modbus_config[0], logger=logger_fixture, address=1)
    gateway, server, port = _gateway_stack(modbus_config[1], free_port, _V1_PLUGINS, logger_fixture)
    return emulator, gateway, server, port


# pylint: disable=redefined-outer-name
@pytest.fixture
def v2_stack(modbus_config, logger_fixture, free_port):
    """A v2 emulator plus a gateway/TCP server sharing one virtual serial pair."""
    emulator = ThyracontV2Emulator(modbus_config[0], logger=logger_fixture, address=1)
    gateway, server, port = _gateway_stack(modbus_config[1], free_port, _V2_PLUGINS, logger_fixture)
    return emulator, gateway, server, port


@pytest.mark.asyncio
async def test_v1_read_pressure(v1_stack):
    """FC03 read of pressure returns the emulator's raw encoded value.

    The v1 translator passes register values through as raw integers, and the
    emulator stores pressure as a raw encoded integer, so the read-back value is
    the encoder output for the configured pressure, not the decoded mbar value.
    """
    emulator, gateway, server, port = v1_stack
    await emulator.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        emulator.pressure = 1234.0
        response = await client.read_holding_registers(address=0, count=2, device_id=1)
        assert not response.isError()
        combined = combine_32bit(response.registers[0], response.registers[1])
        assert combined == int(_pressure_encode(1234.0))
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await emulator.stop()


@pytest.mark.asyncio
async def test_v1_read_penning_state(v1_stack):
    """FC03 read of Penning state matches the emulator."""
    emulator, gateway, server, port = v1_stack
    await emulator.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        emulator.penning_state = True
        response = await client.read_holding_registers(address=8, count=1, device_id=1)
        assert not response.isError()
        assert response.registers == [int(emulator.penning_state)]
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await emulator.stop()


@pytest.mark.asyncio
async def test_v1_write_pressure_round_trip(v1_stack):
    """FC16 write of pressure round-trips through the gateway."""
    emulator, gateway, server, port = v1_stack
    await emulator.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        low, high = split_32bit(123456)
        written = await client.write_registers(address=0, values=[low, high], device_id=1)
        assert not written.isError()
        response = await client.read_holding_registers(address=0, count=2, device_id=1)
        assert not response.isError()
        assert combine_32bit(response.registers[0], response.registers[1]) == 123456
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await emulator.stop()


@pytest.mark.asyncio
async def test_v1_setpoint_select_and_write(v1_stack):
    """The two-step SP select + write workaround lands the value at SP1."""
    emulator, gateway, server, port = v1_stack
    await emulator.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        selected = await client.write_register(address=10, value=1, device_id=1)
        assert not selected.isError()
        low, high = split_32bit(654321)
        written = await client.write_registers(address=11, values=[low, high], device_id=1)
        assert not written.isError()
        response = await client.read_holding_registers(address=2, count=2, device_id=1)
        assert not response.isError()
        assert combine_32bit(response.registers[0], response.registers[1]) == 654321
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await emulator.stop()


@pytest.mark.asyncio
async def test_v1_unsupported_address(v1_stack):
    """An unsupported register address maps to a Modbus exception (0x0B)."""
    emulator, gateway, server, port = v1_stack
    await emulator.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        response = await client.read_holding_registers(address=99, count=2, device_id=1)
        assert response.isError()
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await emulator.stop()


@pytest.mark.asyncio
async def test_v2_read_pressure(v2_stack):
    """FC03 read of pressure decodes to the emulator's float32 pressure."""
    emulator, gateway, server, port = v2_stack
    await emulator.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        emulator.pressure = 1234.0
        response = await client.read_holding_registers(address=0, count=2, device_id=1)
        assert not response.isError()
        assert _decode_float32(response.registers) == pytest.approx(emulator.pressure)
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await emulator.stop()


@pytest.mark.asyncio
async def test_v2_read_gauge_hours(v2_stack):
    """FC03 read of gauge operating hours decodes to the emulator's value."""
    emulator, gateway, server, port = v2_stack
    await emulator.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        emulator.gauge_hours = 100.0
        response = await client.read_holding_registers(address=2, count=2, device_id=1)
        assert not response.isError()
        assert _decode_float32(response.registers) == pytest.approx(emulator.gauge_hours)
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await emulator.stop()


@pytest.mark.asyncio
async def test_v2_read_wear(v2_stack):
    """FC03 read of Pirani wear decodes to the emulator's value."""
    emulator, gateway, server, port = v2_stack
    await emulator.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        emulator.wear = 42.0
        response = await client.read_holding_registers(address=6, count=2, device_id=1)
        assert not response.isError()
        assert _decode_float32(response.registers) == pytest.approx(emulator.wear)
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await emulator.stop()


@pytest.mark.asyncio
async def test_v2_unsupported_address(v2_stack):
    """An unsupported register address maps to a Modbus exception (0x0B)."""
    emulator, gateway, server, port = v2_stack
    await emulator.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        response = await client.read_holding_registers(address=99, count=2, device_id=1)
        assert response.isError()
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await emulator.stop()
