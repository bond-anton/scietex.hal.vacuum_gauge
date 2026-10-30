"""
Thyracont RS485 Version 1 Subpackage.

This subpackage provides both sides of the Thyracont RS485 V1 protocol: the
gateway-side implementation consumed by `scietex.hal.serial`'s `ModbusGateway`,
which translates standard Modbus requests into the vendor's command-oriented
ASCII protocol, and a direct client that issues those commands over a serial
port without a gateway in between.

Classes:
    ThyracontEmulator: An RS485 server emulator for simulating a Thyracont vacuum gauge, with
        properties to manage simulated data.
    ThyracontRS485V1Gauge: A direct RS485 client for a V1 gauge.
    ThyracontV1Translator: A `GatewayTranslator` mapping standard Modbus requests to and from the
        V1 vendor protocol.

Modules:
    client: Implements the `ThyracontRS485V1Gauge` direct serial client.
    emulation: Implements the `ThyracontEmulator` class for gauge simulation.
    data: Provides utilities for encoding and decoding pressure and calibration data.
    decoder: Defines a custom PDU decoder for the Thyracont protocol.
    emulation_utils: Contains utilities for managing Modbus registers in the emulator.
    framer: Implements a custom ASCII framer for the Thyracont protocol.
    request: Defines a custom Modbus PDU for Thyracont requests.
    translator: Implements the `ThyracontV1Translator` gateway plugin.
"""

from .client import ThyracontRS485V1Gauge
from .emulation import ThyracontEmulator
from .translator import ThyracontV1Translator

__all__ = ["ThyracontEmulator", "ThyracontRS485V1Gauge", "ThyracontV1Translator"]
