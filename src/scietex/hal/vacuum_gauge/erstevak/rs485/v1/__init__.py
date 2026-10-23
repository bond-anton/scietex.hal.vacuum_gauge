"""
Erstevak RS485 Version 1 Subpackage.

This subpackage provides tools for interacting with and emulating Erstevak vacuum gauges
(e.g., MTM9D) over their RS485 protocol, version 1. It includes a client class for communicating
with physical gauges and an emulator class for simulating gauge behavior, both built on top of a
custom protocol implementation using `pymodbus` and `scietex.hal.serial`. The subpackage supports
pressure measurement, calibration, setpoint management, and Penning gauge control, with flexible
backends for real hardware (`pymodbus` or `pyserial`) and emulation.

Classes:
    ErstevakRS485V1Gauge: An RS485 client for interacting with an Erstevak vacuum gauge, providing
        methods to read and write gauge data.
    ErstevakEmulator: An RS485 server emulator for simulating an Erstevak vacuum gauge, with
        properties to manage simulated data.

Modules:
    client: Implements the `ErstevakRS485V1Gauge` class for real gauge communication.
    emulation: Implements the `ErstevakEmulator` class for gauge simulation.
    data: Provides utilities for encoding and decoding pressure and calibration data.
    decoder: Defines a custom PDU decoder for the Erstevak protocol.
    emulation_utils: Contains utilities for managing Modbus registers in the emulator.
    framer: Implements a custom ASCII framer for the Erstevak protocol.
    request: Defines a custom Modbus PDU for Erstevak requests.
"""

from .client import ErstevakRS485V1Gauge
from .emulation import ErstevakEmulator

__all__ = ["ErstevakRS485V1Gauge", "ErstevakEmulator"]
