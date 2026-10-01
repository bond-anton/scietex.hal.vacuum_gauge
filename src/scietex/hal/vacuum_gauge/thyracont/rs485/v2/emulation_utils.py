"""
Thyracont RS485 Version 2 Emulation Utilities Module.

This module provides the emulated device state and command parsing for a Thyracont vacuum gauge
(e.g., MTM9D) speaking the RS485 V2 protocol. Unlike V1, the V2 protocol is command-oriented rather
than register-oriented, so the emulator state is a plain dataclass and command responses are ASCII
strings generated directly from that state.

Classes:
    ThyracontV2State: Dataclass holding the emulated device state.

Functions:
    parse_command(state, command, data) -> str: Parses a V2 command and returns the response data.
"""

from dataclasses import dataclass
from typing import Optional

from .data import encode_float


# pylint: disable=too-many-instance-attributes
@dataclass
class ThyracontV2State:
    """
    Emulated device state for a Thyracont RS485 V2 vacuum gauge.

    Attributes
    ----------
    pressure : float
        Current pressure in millibars. Defaults to 1000.0.
    gauge_hours : float
        Operating hours of the gauge (in hours). Defaults to 0.0.
    cathode_hours : Optional[float]
        Operating hours of the cathode (in hours). None means no cathode. Defaults to None.
    wear : float
        Sensor wear percentage (Pirani). Defaults to 0.0.
    hours_since_zero_adjustment : float
        Hours since the last zero adjustment. Defaults to 0.0.
    model : str
        Gauge model identifier. Defaults to "MTM9D".
    product_name : str
        Product name. Defaults to "Thyracont MTM9D".
    device_sn : str
        Device serial number. Defaults to "00000000".
    head_sn : str
        Head serial number. Defaults to "00000000".
    device_version : str
        Device version. Defaults to "1.0".
    firmware_version : str
        Firmware version. Defaults to "1.0".
    bootloader_version : str
        Bootloader version. Defaults to "1.0".
    """

    pressure: float = 1000.0
    gauge_hours: float = 0.0
    cathode_hours: Optional[float] = None
    wear: float = 0.0
    hours_since_zero_adjustment: float = 0.0
    model: str = "MTM9D"
    product_name: str = "Thyracont MTM9D"
    device_sn: str = "00000000"
    head_sn: str = "00000000"
    device_version: str = "1.0"
    firmware_version: str = "1.0"
    bootloader_version: str = "1.0"


# pylint: disable=too-many-branches,too-many-return-statements
def parse_command(state: ThyracontV2State, command: str, data: str) -> str:
    """
    Parse a Thyracont RS485 V2 command and return the response data string.

    The response is the DATA portion of a V2 frame (without access code, command, or length).
    Unknown commands raise :class:`ValueError` so the caller can translate them into an ERROR reply.

    Parameters
    ----------
    state : ThyracontV2State
        The emulated device state to read from.
    command : str
        The two-character command (e.g., "MV", "OH", "PM").
    data : str
        The data payload associated with the command (e.g., "1" for Pirani wear status).

    Returns
    -------
    str
        The response data string.

    Raises
    ------
    ValueError
        If the command (or command data) is not supported by the emulator.
    """
    if command in ("MV", "M0", "M1", "M2", "M3", "M4"):
        return encode_float(state.pressure)
    if command == "OH":
        if state.cathode_hours is None:
            return f"{int(state.gauge_hours * 4)}"
        return f"{int(state.gauge_hours * 4)}C{int(state.cathode_hours * 4)}"
    if command == "PM":
        if data == "1":  # Pirani
            return f"W{int(state.wear)}A{int(state.hours_since_zero_adjustment * 4)}"
        raise ValueError(f"Unsupported command data: {command} {data}")
    if command == "TD":
        return state.model
    if command == "PN":
        return state.product_name
    if command == "SD":
        return state.device_sn
    if command == "SH":
        return state.head_sn
    if command == "VD":
        return state.device_version
    if command == "VF":
        return state.firmware_version
    if command == "VB":
        return state.bootloader_version
    if command == "MR":
        return "H1.0e3L1.0e-3"
    raise ValueError(f"Unsupported command: {command}")
