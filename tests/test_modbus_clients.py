"""
Tests for the Modbus/TCP vacuum gauge clients.

These tests exercise the register encoding and decoding without any network
I/O: the Modbus client is replaced by a stub that records calls and returns
canned responses, so the tests cover the register map and the error handling
rather than the transport.
"""

import asyncio
import struct

import pytest
from pymodbus.pdu import ExceptionResponse
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    WriteMultipleRegistersResponse,
    WriteSingleRegisterResponse,
)
from scietex.hal.serial import ModbusOperationError
from scietex.hal.serial.utilities.numeric import ByteOrder, split_32bit

# The fallback branch imports the installed package while the primary branch
# imports from src/, so pylint cannot group them.
# pylint: disable=ungrouped-imports
try:
    from src.scietex.hal.vacuum_gauge.base.protocol import VacuumGaugeProtocol
    from src.scietex.hal.vacuum_gauge.erstevak.modbus.v1.client import (
        ErstevakModbusV1Gauge,
    )
    from src.scietex.hal.vacuum_gauge.erstevak.modbus.v2.client import (
        ErstevakModbusV2Gauge,
    )
    from src.scietex.hal.vacuum_gauge.thyracont.modbus.v1.client import (
        ThyracontModbusV1Gauge,
        _decode_pressure,
        _encode_pressure,
    )
    from src.scietex.hal.vacuum_gauge.thyracont.modbus.v2.client import (
        ThyracontModbusV2Gauge,
        _registers_to_float,
    )
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.base.protocol import VacuumGaugeProtocol
    from scietex.hal.vacuum_gauge.erstevak.modbus.v1.client import ErstevakModbusV1Gauge
    from scietex.hal.vacuum_gauge.erstevak.modbus.v2.client import ErstevakModbusV2Gauge
    from scietex.hal.vacuum_gauge.thyracont.modbus.v1.client import (
        ThyracontModbusV1Gauge,
        _decode_pressure,
        _encode_pressure,
    )
    from scietex.hal.vacuum_gauge.thyracont.modbus.v2.client import (
        ThyracontModbusV2Gauge,
        _registers_to_float,
    )


class _StubClient:
    """Stand-in for `AsyncModbusTcpClient` that records calls."""

    def __init__(self, responses=None, connect_result=True):
        self.responses = list(responses or [])
        self.calls = []
        self.closed = False
        self.connect_result = connect_result

    async def connect(self):
        """Pretend to connect, reporting the configured result."""
        return self.connect_result

    def close(self):
        """Record the close."""
        self.closed = True

    def _next(self):
        if not self.responses:
            raise AssertionError("stub ran out of canned responses")
        return self.responses.pop(0)

    async def read_holding_registers(self, address, *, count=1, device_id=1):
        """Record the read and return the next canned response."""
        self.calls.append(("read", address, count, device_id))
        return self._next()

    async def write_register(self, address, value, *, device_id=1):
        """Record the write and return the next canned response."""
        self.calls.append(("write", address, value, device_id))
        return self._next()

    async def write_registers(self, address, values, *, device_id=1):
        """Record the write and return the next canned response."""
        self.calls.append(("write_many", address, list(values), device_id))
        return self._next()


def _attach(gauge, stub):
    """Attach a stub client to a gauge, bypassing `connect()`."""
    gauge._client = stub  # pylint: disable=protected-access
    return gauge


def _read_response(registers):
    return ReadHoldingRegistersResponse(registers=registers)


def _write_response(address, value):
    return WriteSingleRegisterResponse(address=address, registers=[value])


def _write_many_response(address, count):
    return WriteMultipleRegistersResponse(address=address, count=count)


# -- pressure encoding ------------------------------------------------------


@pytest.mark.parametrize(
    "pressure",
    [1.234, 1.23e-3, 1000.0, 1e-5, 1e3, 5e-7],
)
def test_pressure_round_trip(pressure):
    """Encoding then decoding a pressure returns the original value."""
    assert _decode_pressure(_encode_pressure(pressure)) == pytest.approx(pressure)


def test_pressure_encode_rejects_non_positive():
    """A non-positive pressure cannot be encoded."""
    with pytest.raises(ValueError):
        _encode_pressure(0.0)


def test_pressure_decode_rejects_zero():
    """A zero register value is not a valid pressure."""
    assert _decode_pressure(0) is None


# -- V1 client --------------------------------------------------------------


def test_v1_measure_decodes_pressure():
    """`measure` reads two registers and decodes the pressure."""
    gauge = _attach(
        ThyracontModbusV1Gauge("127.0.0.1"),
        _StubClient([_read_response(list(split_32bit(_encode_pressure(1.234))))]),
    )
    assert asyncio.run(gauge.measure()) == pytest.approx(1.234)


def test_v1_measure_uses_unit_id():
    """The configured unit id is passed to the Modbus call."""
    stub = _StubClient([_read_response(list(split_32bit(_encode_pressure(1.0))))])
    gauge = _attach(ThyracontModbusV1Gauge("127.0.0.1", unit_id=7), stub)
    asyncio.run(gauge.measure())
    assert stub.calls == [("read", 0, 2, 7)]


def test_v1_measure_raises_on_exception_response():
    """A Modbus exception response surfaces as `ModbusOperationError`."""
    gauge = _attach(
        ThyracontModbusV1Gauge("127.0.0.1"),
        _StubClient([ExceptionResponse(3, 2)]),
    )
    with pytest.raises(ModbusOperationError):
        asyncio.run(gauge.measure())


def test_v1_read_data_includes_penning():
    """`read_data` returns pressure plus both Penning flags."""
    stub = _StubClient(
        [
            _read_response(list(split_32bit(_encode_pressure(1.0)))),
            _read_response([1]),
            _read_response([0]),
        ]
    )
    gauge = _attach(ThyracontModbusV1Gauge("127.0.0.1"), stub)
    data = asyncio.run(gauge.read_data())
    assert data["pressure"] == pytest.approx(1.0)
    assert data["penning_state"] is True
    assert data["penning_sync"] is False


def test_v1_set_setpoint_selects_before_writing():
    """`set_setpoint` writes the select register before the value register."""
    stub = _StubClient(
        [
            _write_response(10, 2),
            _write_many_response(11, 2),
        ]
    )
    gauge = _attach(ThyracontModbusV1Gauge("127.0.0.1"), stub)
    asyncio.run(gauge.set_setpoint(2, 1.0))
    assert stub.calls[0] == ("write", 10, 2, 1)
    assert stub.calls[1][0] == "write_many"
    assert stub.calls[1][1] == 11


def test_v1_set_penning_state_writes_register():
    """`set_penning_state` writes the Penning register."""
    stub = _StubClient([_write_response(8, 1)])
    gauge = _attach(ThyracontModbusV1Gauge("127.0.0.1"), stub)
    asyncio.run(gauge.set_penning_state(True))
    assert stub.calls == [("write", 8, 1, 1)]


def test_v1_set_atmosphere_writes_1000_mbar():
    """`set_atmosphere` writes 1000 mbar to the pressure register."""
    stub = _StubClient([_write_many_response(0, 2)])
    gauge = _attach(ThyracontModbusV1Gauge("127.0.0.1"), stub)
    asyncio.run(gauge.set_atmosphere())
    assert stub.calls[0][0] == "write_many"
    assert stub.calls[0][1] == 0


def test_v1_close_releases_client():
    """`close` closes the underlying client and clears it."""
    stub = _StubClient()
    gauge = _attach(ThyracontModbusV1Gauge("127.0.0.1"), stub)
    asyncio.run(gauge.close())
    assert stub.closed is True
    assert gauge._client is None  # pylint: disable=protected-access


def test_v1_requires_connect():
    """Calling a read before `connect()` raises."""
    gauge = ThyracontModbusV1Gauge("127.0.0.1")
    with pytest.raises(RuntimeError):
        asyncio.run(gauge.measure())


def test_v1_connect_raises_when_gateway_unreachable(monkeypatch):
    """A failed connect raises instead of leaving the gauge looking connected."""
    stub = _StubClient(connect_result=False)
    monkeypatch.setattr(
        "scietex.hal.vacuum_gauge.thyracont.modbus.v1.client.AsyncModbusTcpClient",
        lambda *args, **kwargs: stub,
    )
    gauge = ThyracontModbusV1Gauge("127.0.0.1")
    with pytest.raises(ModbusOperationError):
        asyncio.run(gauge.connect())


def test_v2_connect_raises_when_gateway_unreachable(monkeypatch):
    """A failed connect raises instead of leaving the gauge looking connected."""
    stub = _StubClient(connect_result=False)
    monkeypatch.setattr(
        "scietex.hal.vacuum_gauge.thyracont.modbus.v2.client.AsyncModbusTcpClient",
        lambda *args, **kwargs: stub,
    )
    gauge = ThyracontModbusV2Gauge("127.0.0.1")
    with pytest.raises(ModbusOperationError):
        asyncio.run(gauge.connect())


# -- V2 client --------------------------------------------------------------


def test_registers_to_float_decodes_big_endian():
    """Two big-endian registers decode into the original float32."""
    raw = struct.pack(">f", 1.5)
    word = struct.unpack(">I", raw)[0]
    high, low = split_32bit(word, ByteOrder.BIG_ENDIAN)
    assert _registers_to_float([high, low]) == pytest.approx(1.5)


def test_v2_measure_decodes_pressure():
    """`measure` reads two registers and decodes the float32 pressure."""
    raw = struct.pack(">f", 2.5)
    word = struct.unpack(">I", raw)[0]
    registers = list(split_32bit(word, ByteOrder.BIG_ENDIAN))
    gauge = _attach(ThyracontModbusV2Gauge("127.0.0.1"), _StubClient([_read_response(registers)]))
    assert asyncio.run(gauge.measure()) == pytest.approx(2.5)


def test_v2_read_data_reads_all_fields():
    """`read_data` reads pressure and the four statistics registers."""
    raw = struct.pack(">f", 1.0)
    word = struct.unpack(">I", raw)[0]
    registers = list(split_32bit(word, ByteOrder.BIG_ENDIAN))
    stub = _StubClient([_read_response(registers) for _ in range(5)])
    gauge = _attach(ThyracontModbusV2Gauge("127.0.0.1"), stub)
    data = asyncio.run(gauge.read_data())
    assert set(data) == {
        "pressure",
        "gauge_hours",
        "cathode_hours",
        "pirani_wear",
        "pirani_hours",
    }
    assert [call[1] for call in stub.calls] == [0, 2, 4, 6, 8]


def test_v2_has_no_control_capabilities():
    """The read-only V2 protocol advertises no control capabilities."""
    gauge = ThyracontModbusV2Gauge("127.0.0.1")
    assert gauge.supports_penning is False
    assert gauge.supports_setpoint is False
    assert gauge.supports_calibration is False
    assert gauge.supports_atmosphere is False
    assert gauge.supports_zero is False


# -- Erstevak subclasses ----------------------------------------------------


def test_erstevak_v1_defaults_label():
    """The Erstevak V1 client defaults to an Erstevak label."""
    gauge = ErstevakModbusV1Gauge("127.0.0.1")
    assert gauge.label == "Erstevak Gauge"
    assert gauge.supports_penning is True


def test_erstevak_v2_defaults_label():
    """The Erstevak V2 client defaults to an Erstevak label."""
    gauge = ErstevakModbusV2Gauge("127.0.0.1")
    assert gauge.label == "Erstevak Gauge"
    assert gauge.supports_penning is False


# -- protocol conformance ---------------------------------------------------


@pytest.mark.parametrize(
    "gauge_class",
    [
        ThyracontModbusV1Gauge,
        ThyracontModbusV2Gauge,
        ErstevakModbusV1Gauge,
        ErstevakModbusV2Gauge,
    ],
)
def test_clients_satisfy_protocol(gauge_class):
    """Every client satisfies `VacuumGaugeProtocol`."""
    assert isinstance(gauge_class("127.0.0.1"), VacuumGaugeProtocol)
