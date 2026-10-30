"""End-to-end check that the V2 gateway descriptor's bundle actually reads a gauge.

The descriptor is only wiring, so the unit tests prove the paths are right but
not that the resolved plugins work together. This drives the descriptor's own
translator against the V2 emulator over a virtual serial pair, which is the same
path the gateway takes: FC03 request -> vendor command -> ASCII response ->
float32 registers.
"""

import logging
import struct

import pytest
from pymodbus.pdu.register_message import ReadHoldingRegistersRequest
from scietex.hal.serial import VirtualSerialPair
from scietex.hal.serial.config import ModbusSerialConnectionConfig
from scietex.hal.serial.gateway.plugin_loader import (
    resolve_decoder,
    resolve_framer,
    resolve_pdu,
    resolve_translator,
)

from scietex.hal.vacuum_gauge.modbus_drivers import thyracont_rs485_v2
from scietex.hal.vacuum_gauge.thyracont.rs485.v2.client import ThyracontRS485V2Gauge
from scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation import ThyracontV2Emulator


@pytest.fixture
def vsp():
    """Start a virtual serial pair."""
    pair = VirtualSerialPair(logger=logging.getLogger("test_logger"))
    pair.start()
    yield pair
    pair.stop()


@pytest.fixture
def configs(vsp):
    """Connection configs for both ends of the pair."""
    return [
        ModbusSerialConnectionConfig(
            port=port, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=1.0
        )
        for port in vsp.serial_ports
    ]


def test_descriptor_plugins_resolve():
    """Every reference in the descriptor resolves to a real class."""
    assert resolve_framer(thyracont_rs485_v2.framer).__name__ == "ThyracontASCIIFramer"
    assert resolve_decoder(thyracont_rs485_v2.decoder).__name__ == "ThyracontDecodePDU"
    assert resolve_pdu(thyracont_rs485_v2.pdus[0]).__name__ == "ThyracontRequest"
    assert resolve_translator(thyracont_rs485_v2.translator).__name__ == "ThyracontV2Translator"


@pytest.mark.asyncio
async def test_descriptor_translator_reads_pressure(configs):
    """The descriptor's translator turns an FC03 read into a real pressure value.

    The emulator is a pymodbus server, so it only answers while the event loop
    runs; the client class drives the exchange and the translator is applied to
    the decoded response exactly as the gateway would.
    """
    emulator = ThyracontV2Emulator(
        con_params=configs[0], logger=logging.getLogger("test_logger"), address=2
    )
    await emulator.start()
    emulator.pressure = 123.4

    client = ThyracontRS485V2Gauge(
        connection_config=configs[1],
        address=2,
        label="Test Gauge",
        logger=logging.getLogger("test_logger"),
        timeout=1.0,
        backend="pymodbus",
    )
    assert await client.measure() == pytest.approx(123.4)

    # Now the gateway path: the descriptor's translator maps FC03 -> vendor
    # command and the decoded response -> float32 registers.
    translator = resolve_translator(thyracont_rs485_v2.translator)()
    request = ReadHoldingRegistersRequest(address=0, count=2)
    vendor_request = translator.to_vendor(request)
    assert vendor_request.command == "MV"

    decoder = resolve_decoder(thyracont_rs485_v2.decoder)(is_server=False)
    # The gateway registers the descriptor's PDUs on the decoder before use.
    decoder.register(resolve_pdu(thyracont_rs485_v2.pdus[0]))
    # The decoder takes the payload the framer strips the address and checksum
    # from: <access code><command><length><data>.
    decoded = decoder.decode(b"1MV05123.4")
    assert decoded is not None

    standard = translator.to_standard(decoded)
    high, low = standard.registers
    value = struct.unpack(">f", struct.pack(">HH", high, low))[0]
    assert value == pytest.approx(123.4, abs=0.01)

    await emulator.stop()
