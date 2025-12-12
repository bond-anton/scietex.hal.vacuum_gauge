"""
Thyracont RS485 Version 1 Emulation Utilities Module.

This module provides utility functions for emulating a Thyracont vacuum gauge's RS485 communication
protocol, specifically interacting with a Modbus slave context. It supports reading and writing
32-bit values across pairs of 16-bit holding registers, converting pressure values to and from an
encoded format, and parsing custom ASCII commands for the Thyracont MTM9D gauge. The module relies
on external utilities for numeric splitting/combining and pressure encoding/decoding.

Constants:
    REG_P (int): Register address for pressure value (32-bit, spans REG_P and REG_P+1).
    REG_SP1 (int): Register address for setpoint 1 (32-bit, spans REG_SP1 and REG_SP1+1).
    REG_SP2 (int): Register address for setpoint 2 (32-bit, spans REG_SP2 and REG_SP2+1).
    REG_CAL1 (int): Register address for calibration value 1 (16-bit).
    REG_CAL2 (int): Register address for calibration value 2 (16-bit).
    REG_PENNING_STATE (int): Register address for Penning gauge state (16-bit).
    REG_PENNING_SYNC (int): Register address for Penning synchronization value (16-bit).
    REG_SP_SEL (int): Register address for setpoint selection flag (16-bit).
    REG_CAL_SEL (int): Register address for calibration selection flag (16-bit).
    REG_ATM_SEL (int): Register address for atmosphere adjustment flag (16-bit).
    REG_ZERO_SEL (int): Register address for zero adjustment flag (16-bit).

Functions:
    read_two_regs(context: ModbusSlaveContext, start_reg: int) -> int
        Reads a 32-bit value from two consecutive 16-bit holding registers.
    write_two_regs(context: ModbusSlaveContext, value: int, start_reg: int) -> None
        Writes a 32-bit value to two consecutive 16-bit holding registers.
    pressure_from_reg(context: ModbusSlaveContext, start_reg: int) -> float
        Reads and decodes a pressure value from two registers.
    pressure_to_reg(context: ModbusSlaveContext, p: float, start_reg: int) -> None
        Encodes and writes a pressure value to two registers.
    parse_command(context: ModbusSlaveContext, command: str, data: str) -> bytes
        Parses and executes Thyracont-specific ASCII commands, returning a response.
"""

from typing import Optional
from pymodbus.datastore import ModbusDeviceContext
from scietex.hal.serial.utilities.numeric import split_32bit, combine_32bit
from .data import _pressure_encode, _pressure_decode


REG_P = 0
REG_SP1 = 2
REG_SP2 = 4
REG_CAL1 = 6
REG_CAL2 = 7
REG_PENNING_STATE = 8
REG_PENNING_SYNC = 9
REG_SP_SEL = 10
REG_CAL_SEL = 11
REG_ATM_SEL = 12
REG_ZERO_SEL = 13


def read_two_regs(context: ModbusDeviceContext, start_reg: int) -> int:
    """
    Reads a 32-bit value from two consecutive 16-bit holding registers.

    Combines two 16-bit values from the Modbus slave context's holding registers into a single
    32-bit integer using the `combine_32bit` utility.

    Parameters
    ----------
    context : ModbusSlaveContext
        The Modbus slave context containing the holding register store.
    start_reg : int
        The starting register address (e.g., 0 for REG_P).

    Returns
    -------
    int
        The 32-bit value combined from the two registers (`start_reg` and `start_reg + 1`).
    """
    a = context.store["h"].values[start_reg]
    b = context.store["h"].values[start_reg + 1]
    return combine_32bit(a, b)


def write_two_regs(context: ModbusDeviceContext, value: int, start_reg: int) -> None:
    """
    Writes a 32-bit value to two consecutive 16-bit holding registers.

    Splits a 32-bit integer into two 16-bit values using the `split_32bit` utility and writes them
    to the Modbus slave context's holding registers.

    Parameters
    ----------
    context : ModbusSlaveContext
        The Modbus slave context containing the holding register store.
    value : int
        The 32-bit value to write.
    start_reg : int
        The starting register address (e.g., 0 for REG_P).
    """
    a, b = split_32bit(value)
    context.store["h"].values[start_reg] = a
    context.store["h"].values[start_reg + 1] = b


def pressure_from_reg(context: ModbusDeviceContext, start_reg: int) -> Optional[float]:
    """
    Reads and decodes a pressure value from two registers.

    Retrieves a 32-bit encoded pressure value from two consecutive registers, formats it as a
    6-digit string, and decodes it into a float using the `_pressure_decode` utility.

    Parameters
    ----------
    context : ModbusSlaveContext
        The Modbus slave context containing the holding register store.
    start_reg : int
        The starting register address (e.g., 0 for REG_P).

    Returns
    -------
    float
        The decoded pressure value in millibars (mbar).
    """
    p_encoded = read_two_regs(context, start_reg)
    return _pressure_decode(f"{p_encoded:06d}")


def pressure_to_reg(context: ModbusDeviceContext, p: float, start_reg: int) -> None:
    """
    Encodes and writes a pressure value to two registers.

    Encodes a pressure value (in millibars) into a 6-digit string using the `_pressure_encode`
    utility, converts it to an integer, and writes it as a 32-bit value across two consecutive
    registers.

    Parameters
    ----------
    context : ModbusSlaveContext
        The Modbus slave context containing the holding register store.
    p : float
        The pressure value in millibars (mbar) to encode and write.
    start_reg : int
        The starting register address (e.g., 0 for REG_P).
    """
    p_encoded = int(_pressure_encode(p))
    write_two_regs(context, p_encoded, start_reg)


# pylint: disable=too-many-branches,too-many-statements
def parse_command(context: ModbusDeviceContext, command: str, data: str) -> bytes:
    """
    Parses and executes Thyracont-specific ASCII commands, returning a response.

    Interprets single-character commands and associated data to read from or write to the Modbus
    slave context's holding registers, emulating the Thyracont MTM9D gauge's RS485 protocol.
    Commands include reading pressure, setpoints, calibration values, and states, as well as
    writing new values or toggling adjustment flags.

    Parameters
    ----------
    context : ModbusSlaveContext
        The Modbus slave context containing the holding register store.
    command : str
        A single-character command (e.g., "T", "M", "s") specifying the action.
    data : str
        The data payload associated with the command (e.g., "1", "123456").

    Returns
    -------
    bytes
        The response data encoded as bytes. Returns the input `data` by default if no specific
        response is generated, or an empty `b""` for certain invalid adjustment commands.

    Notes
    -----
    Supported commands:
    - "T": Returns gauge type ("MTM09D").
    - "M": Reads current pressure (REG_P).
    - "m": Writes new pressure to REG_P.
    - "S": Reads setpoint 1 (REG_SP1) or 2 (REG_SP2) if data is "1" or "2".
    - "s": Selects setpoint (1 or 2) or writes to selected setpoint.
    - "C": Reads calibration value 1 (REG_CAL1) or 2 (REG_CAL2) if data is "1" or "2".
    - "c": Selects calibration (1 or 2) or writes to selected calibration.
    - "I": Reads Penning gauge state (REG_PENNING_STATE).
    - "i": Writes Penning gauge state.
    - "W": Reads Penning synchronization value (REG_PENNING_SYNC).
    - "w": Writes Penning synchronization value.
    - "j": Toggles atmosphere ("1") or zero ("0") adjustment, or applies adjustment with data.
    """
    response_data = data.encode()
    if command == "T":
        response_data = b"MTM09D"
    elif command == "M":
        p_encoded = read_two_regs(context, REG_P)
        response_data = f"{p_encoded:06d}".encode()
    elif command == "m":
        try:
            write_two_regs(context, int(data), REG_P)
        except ValueError:
            pass
    elif command == "S":
        if data == "1":
            p_encoded = read_two_regs(context, REG_SP1)
        elif data == "2":
            p_encoded = read_two_regs(context, REG_SP2)
        else:
            p_encoded = None
        if p_encoded is not None:
            response_data = f"{p_encoded:06d}".encode()
    elif command == "s":
        if data == "1":
            context.store["h"].values[REG_SP_SEL] = 1
        elif data == "2":
            context.store["h"].values[REG_SP_SEL] = 2
        else:
            if context.store["h"].values[REG_SP_SEL] == 1:
                write_two_regs(context, int(data), REG_SP1)
                context.store["h"].values[REG_SP_SEL] = 0
            elif context.store["h"].values[REG_SP_SEL] == 2:
                write_two_regs(context, int(data), REG_SP2)
                context.store["h"].values[REG_SP_SEL] = 0
    elif command == "C":
        if data == "1":
            cal_encoded = context.store["h"].values[REG_CAL1]
        elif data == "2":
            cal_encoded = context.store["h"].values[REG_CAL2]
        else:
            cal_encoded = None
        if cal_encoded is not None:
            response_data = f"{cal_encoded:06d}".encode()
    elif command == "c":
        if data == "1":
            context.store["h"].values[REG_CAL_SEL] = 1
        elif data == "2":
            context.store["h"].values[REG_CAL_SEL] = 2
        else:
            if context.store["h"].values[REG_CAL_SEL] == 1:
                write_two_regs(context, int(data), REG_CAL1)
                context.store["h"].values[REG_CAL_SEL] = 0
            elif context.store["h"].values[REG_CAL_SEL] == 2:
                write_two_regs(context, int(data), REG_CAL2)
                context.store["h"].values[REG_CAL_SEL] = 0
    elif command == "I":
        penning_state = context.store["h"].values[REG_PENNING_STATE]
        response_data = f"{penning_state:06d}".encode()
    elif command == "i":
        context.store["h"].values[REG_PENNING_STATE] = int(data)
    elif command == "W":
        penning_sync = context.store["h"].values[REG_PENNING_SYNC]
        response_data = f"{penning_sync:06d}".encode()
    elif command == "w":
        context.store["h"].values[REG_PENNING_SYNC] = int(data)
    elif command == "j":
        if data == "1":
            context.store["h"].values[REG_ATM_SEL] = 1
            context.store["h"].values[REG_ZERO_SEL] = 0
        elif data == "0":
            context.store["h"].values[REG_ZERO_SEL] = 1
            context.store["h"].values[REG_ATM_SEL] = 0
        else:
            if context.store["h"].values[REG_ATM_SEL] == 1:
                context.store["h"].values[REG_ATM_SEL] = 0
                if data != "100023":
                    response_data = b""
                else:
                    write_two_regs(context, int(data), REG_P)
            elif context.store["h"].values[REG_ZERO_SEL] == 1:
                context.store["h"].values[REG_ZERO_SEL] = 0
                if data not in ("000000", "000020"):
                    response_data = b""
                else:
                    write_two_regs(context, int(data), REG_P)
    return response_data
