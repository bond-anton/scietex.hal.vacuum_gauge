"""
Thyracont RS485 Version 1 Subpackage.

This subpackage provides the gateway-side protocol implementation for Thyracont
vacuum gauges (e.g. VSP/MTM9D) speaking the vendor's RS485 V1 protocol. It is
consumed by `scietex.hal.serial`'s `ModbusGateway`, which translates standard
Modbus requests into the vendor's command-oriented ASCII protocol, so a
Modbus/TCP client such as `ThyracontModbusV1Gauge` never touches the vendor
framing.

Classes:
    ThyracontEmulator: An RS485 server emulator for simulating a Thyracont vacuum gauge, with
        properties to manage simulated data.
    ThyracontV1Translator: A `GatewayTranslator` mapping standard Modbus requests to and from the
        V1 vendor protocol.

Modules:
    emulation: Implements the `ThyracontEmulator` class for gauge simulation.
    data: Provides utilities for encoding and decoding pressure and calibration data.
    decoder: Defines a custom PDU decoder for the Thyracont protocol.
    emulation_utils: Contains utilities for managing Modbus registers in the emulator.
    framer: Implements a custom ASCII framer for the Thyracont protocol.
    request: Defines a custom Modbus PDU for Thyracont requests.
    translator: Implements the `ThyracontV1Translator` gateway plugin.
"""

from .emulation import ThyracontEmulator
from .translator import ThyracontV1Translator

__all__ = ["ThyracontEmulator", "ThyracontV1Translator"]
