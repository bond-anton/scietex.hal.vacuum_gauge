"""
Thyracont RS485 Version 1 Subpackage.

This subpackage provides tools for interacting with and emulating Thyracont vacuum gauges
(e.g., VSP) over their RS485 protocol, version 1. It includes a client class for communicating
with physical gauges and an emulator class for simulating gauge behavior, both built on top of a
custom protocol implementation using `pymodbus` and `scietex.hal.serial`. The subpackage supports
pressure measurement, calibration, setpoint management, and Penning gauge control, with flexible
backends for real hardware (`pymodbus` or `pyserial`) and emulation.

Classes:
    ThyracontVacuumGauge: An RS485 client for interacting with a Thyracont vacuum gauge, providing
        methods to read and write gauge data.
    ThyracontEmulator: An RS485 server emulator for simulating a Thyracont vacuum gauge, with
        properties to manage simulated data.
    ThyracontV1Translator: A `GatewayTranslator` mapping standard Modbus requests to and from the
        V1 vendor protocol.

Modules:
    client: Implements the `ThyracontVacuumGauge` class for real gauge communication.
    emulation: Implements the `ThyracontEmulator` class for gauge simulation.
    data: Provides utilities for encoding and decoding pressure and calibration data.
    decoder: Defines a custom PDU decoder for the Thyracont protocol.
    emulation_utils: Contains utilities for managing Modbus registers in the emulator.
    framer: Implements a custom ASCII framer for the Thyracont protocol.
    request: Defines a custom Modbus PDU for Thyracont requests.
    translator: Implements the `ThyracontV1Translator` gateway plugin.
"""

from .client import ThyracontVacuumGauge
from .emulation import ThyracontEmulator
from .translator import ThyracontV1Translator

__all__ = ["ThyracontVacuumGauge", "ThyracontEmulator", "ThyracontV1Translator"]
