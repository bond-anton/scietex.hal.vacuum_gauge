"""
Thyracont RS485 Version 2 Subpackage.

This subpackage provides tools for interacting with and emulating Thyracont vacuum gauges
(e.g., MTM9D) over their RS485 protocol, version 2. It includes a client class for communicating
with physical gauges and an emulator class for simulating gauge behavior, both built on top of a
custom protocol implementation using `pymodbus` and `scietex.hal.serial`. The subpackage supports
pressure measurement, operating-hours and wear statistics, identification queries, and emulation,
with flexible backends for real hardware (`pymodbus` or `pyserial`).

Classes:
    ThyracontVacuumGauge: An RS485 client for interacting with a Thyracont vacuum gauge, providing
        methods to read and write gauge data.
    ThyracontV2Emulator: An RS485 server emulator for simulating a Thyracont vacuum gauge, with
        properties to manage simulated data.

Modules:
    client: Implements the `ThyracontVacuumGauge` class for real gauge communication.
    emulation: Implements the `ThyracontV2Emulator` class for gauge simulation.
    emulation_utils: Defines the emulated device state and command parsing.
    data: Provides utilities for encoding and decoding V2 protocol data.
    decoder: Defines a custom PDU decoder for the Thyracont V2 protocol.
    framer: Implements a custom ASCII framer for the Thyracont V2 protocol.
    request: Defines a custom Modbus PDU for Thyracont V2 requests.
"""

from .client import ThyracontVacuumGauge
from .emulation import ThyracontV2Emulator

__all__ = ["ThyracontVacuumGauge", "ThyracontV2Emulator"]
