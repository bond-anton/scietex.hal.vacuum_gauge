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

from dataclasses import dataclass, field

from .data import encode_float, encode_float_1


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
    relays : dict[int, dict]
        Relay settings keyed by relay number (1 or 2). Each entry carries
        ``on``/``off`` pressures, a ``mode`` and optional ``D``/``C``
        hysteresis values.
    display_units : str
        Front-panel display unit. Defaults to "mbar".
    display_orientation : int
        Front-panel display orientation, 0 or 1. Defaults to 0.
    display_data_source : int
        Sensor shown on the front panel. Defaults to 0 (auto).
    degas : bool
        Whether degas is running. Defaults to False.
    digital_logic : bool
        Digital I/O logic polarity. Defaults to False.
    cathode_control : bool
        Whether the cathode is switched on. Defaults to False.
    cathode_control_mode : int
        Cathode control mode, 0 (manual) or 1 (auto). Defaults to 0.
    filament_control : int
        Filament control mode. Defaults to 0.
    filament_number : int
        Active filament number. Defaults to 1.
    filament_status : int
        Filament status code. Defaults to 0.
    gas_correction : dict[int, float]
        Gas correction factor keyed by sensor number. Defaults to 1.0 per
        sensor.
    panel_locked : bool
        Whether the front panel is locked. Defaults to False.
    controller_enabled : bool
        Whether the internal controller is enabled. Defaults to False.
    low_pass_filter : dict[int, int]
        Low-pass filter level keyed by sensor number. Defaults to 0.
    output_characteristic : str
        Output characteristic string. Defaults to a linear characteristic.
    sensor_transition : str
        Sensor transition rule string. Defaults to "T0".
    """

    pressure: float = 1000.0
    gauge_hours: float = 0.0
    cathode_hours: float | None = None
    wear: float = 0.0
    hours_since_zero_adjustment: float = 0.0
    model: str = "MTM9D"
    product_name: str = "Thyracont MTM9D"
    device_sn: str = "00000000"
    head_sn: str = "00000000"
    device_version: str = "1.0"
    firmware_version: str = "1.0"
    bootloader_version: str = "1.0"
    relays: dict[int, dict] = field(
        default_factory=lambda: {
            1: {"on": 1e-3, "off": 1e-3, "mode": "pressure", "D": None, "C": None},
            2: {"on": 1e-1, "off": 1e-1, "mode": "pressure", "D": None, "C": None},
        }
    )
    display_units: str = "mbar"
    display_orientation: int = 0
    display_data_source: int = 0
    degas: bool = False
    digital_logic: bool = False
    cathode_control: bool = False
    cathode_control_mode: int = 0
    filament_control: int = 0
    filament_number: int = 1
    filament_status: int = 0
    gas_correction: dict[int, float] = field(
        default_factory=lambda: {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0}
    )
    panel_locked: bool = False
    controller_enabled: bool = False
    low_pass_filter: dict[int, int] = field(default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0})
    output_characteristic: str = "LinG1.0O0.0L1.0e-3U1.0e3O1.0e3F1.0e4"
    sensor_transition: str = "T0"


# pylint: disable=too-many-branches,too-many-return-statements
def parse_command(
    state: ThyracontV2State, command: str, data: str, factory_default: bool = False
) -> str:
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
    factory_default : bool
        Whether the request carried the factory-default access code. A reset
        restores the command's default instead of applying ``data``.

    Returns
    -------
    str
        The response data string.

    Raises
    ------
    ValueError
        If the command (or command data) is not supported by the emulator.
    """
    if factory_default:
        return _apply_factory_default(state, command, data)
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
    if command in ("R1", "R2"):
        return _parse_relay(state, int(command[1]), data)
    if command == "DU":
        if data:
            state.display_units = data
        return state.display_units
    if command == "DO":
        if data:
            state.display_orientation = int(bool(int(data)))
        return f"{state.display_orientation}"
    if command == "DD":
        if data:
            state.display_data_source = int(data)
        return f"{state.display_data_source}"
    if command == "DG":
        if data:
            state.degas = bool(int(data))
        return f"{int(state.degas)}"
    if command == "DL":
        if data:
            state.digital_logic = bool(int(data))
        return f"{int(state.digital_logic)}"
    if command == "CA":
        return f"{int(state.cathode_control)}"
    if command == "CC":
        if data:
            state.cathode_control = bool(int(data))
        return f"{int(state.cathode_control)}"
    if command == "CM":
        if data:
            state.cathode_control_mode = int(bool(int(data)))
        return f"{state.cathode_control_mode}"
    if command == "FC":
        if data:
            state.filament_control = int(data)
        return f"{state.filament_control}"
    if command == "FN":
        return f"{state.filament_number}"
    if command == "FS":
        return f"{state.filament_status}"
    if command in ("AH", "AL"):
        # Adjustment writes the reference pressure into the state so a test can
        # assert the gauge received it; the response is the echoed value.
        if data:
            state.pressure = float(data)
        return encode_float_1(state.pressure)
    if command == "PS":
        if data:
            state.panel_locked = bool(int(data))
        return f"{int(state.panel_locked)}"
    if command == "CS":
        if data:
            state.controller_enabled = bool(int(data))
        return f"{int(state.controller_enabled)}"
    if command == "LF":
        return _parse_low_pass_filter(state, data)
    if command == "OC":
        return state.output_characteristic
    if command == "ST":
        return state.sensor_transition
    if command.startswith("C") and command[1:].isdigit():
        return _parse_gas_correction(state, int(command[1:]), data)
    raise ValueError(f"Unsupported command: {command}")


def _parse_relay(state: ThyracontV2State, index: int, data: str) -> str:
    """
    Read or write one relay and return its wire representation.

    A write carries ``T<on>F<off>`` optionally followed by ``D<hysteresis>`` or
    ``C<hysteresis>``; a bare mode token (``E``, ``U``, ``O``, ``C``, ``W``,
    ``T0``, ``T1``) selects a non-pressure mode instead.

    Args:
        state: The emulated device state.
        index: Relay number, 1 or 2.
        data: The write payload, empty for a read.

    Returns:
        str: The relay's wire representation.
    """
    relay = state.relays[index]
    if data:
        if data in ("E", "U", "O", "C", "W", "T0", "T1"):
            relay["mode"] = data
        else:
            try:
                on_part, off_part = data.split("F")
                _, on_value = on_part.split("T")
                relay["on"] = float(on_value)
                if "D" in off_part:
                    off_value, hysteresis = off_part.split("D")
                    relay["D"] = int(hysteresis)
                elif "C" in off_part:
                    off_value, hysteresis = off_part.split("C")
                    relay["C"] = int(hysteresis)
                relay["off"] = float(off_value)
                relay["mode"] = "pressure"
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Unsupported relay data: {data}") from exc
    if relay["mode"] != "pressure":
        return relay["mode"]
    result = f"T{encode_float_1(relay['on'])}F{encode_float_1(relay['off'])}"
    if relay["D"] is not None:
        result += f"D{int(relay['D'])}"
    if relay["C"] is not None:
        result += f"C{int(relay['C'])}"
    return result


def _parse_gas_correction(state: ThyracontV2State, sensor: int, data: str) -> str:
    """
    Read or write one sensor's gas correction factor.

    Args:
        state: The emulated device state.
        sensor: Sensor number.
        data: The write payload, empty for a read.

    Returns:
        str: The correction factor in wire form.
    """
    if data:
        state.gas_correction[sensor] = float(data)
    return encode_float_1(state.gas_correction[sensor])


def _parse_low_pass_filter(state: ThyracontV2State, data: str) -> str:
    """
    Read or write a sensor's low-pass filter level.

    A write carries ``D<sensor>F<level>``; a read carries the bare sensor number.
    A factory-default reset carries no payload and clears every sensor.

    Args:
        state: The emulated device state.
        data: The command payload.

    Returns:
        str: The filter level in wire form.
    """
    if not data:
        for sensor in state.low_pass_filter:
            state.low_pass_filter[sensor] = 0
        return "0"
    if data.startswith("D"):
        sensor_part, level_part = data[1:].split("F")
        sensor = int(sensor_part)
        state.low_pass_filter[sensor] = int(level_part)
        return f"{state.low_pass_filter[sensor]}"
    return f"{state.low_pass_filter[int(data)]}"


def _apply_factory_default(state: ThyracontV2State, command: str, data: str) -> str:
    """
    Restore one command's setting to its factory default and return the value.

    Args:
        state: The emulated device state.
        command: The two-character command being reset.
        data: The command payload, which selects the target for indexed commands.

    Returns:
        str: The restored value in wire form.

    Raises:
        ValueError: If the command has no factory default.
    """
    if command in ("R1", "R2"):
        index = int(command[1])
        state.relays[index] = {
            "on": 1e-3 if index == 1 else 1e-1,
            "off": 1e-3 if index == 1 else 1e-1,
            "mode": "pressure",
            "D": None,
            "C": None,
        }
        return _parse_relay(state, index, "")
    if command == "DU":
        state.display_units = "mbar"
        return state.display_units
    if command == "DO":
        state.display_orientation = 0
        return "0"
    if command == "DD":
        state.display_data_source = 0
        return "0"
    if command == "DL":
        state.digital_logic = False
        return "0"
    if command == "DG":
        state.degas = False
        return "0"
    if command == "PS":
        state.panel_locked = False
        return "0"
    if command == "CS":
        state.controller_enabled = False
        return "0"
    if command == "CM":
        state.cathode_control_mode = 0
        return "0"
    if command == "CC":
        state.cathode_control = False
        return "0"
    if command == "FC":
        state.filament_control = 0
        return "0"
    if command == "LF":
        for sensor in state.low_pass_filter:
            state.low_pass_filter[sensor] = 0
        return "0"
    if command == "OC":
        state.output_characteristic = "LinG1.0O0.0L1.0e-3U1.0e3O1.0e3F1.0e4"
        return state.output_characteristic
    if command == "ST":
        state.sensor_transition = "T0"
        return state.sensor_transition
    if command.startswith("C") and command[1:].isdigit():
        sensor = int(command[1:])
        state.gas_correction[sensor] = 1.0
        return encode_float_1(1.0)
    if command == "PM":
        # Read-only query: a factory-default request has nothing to restore,
        # so answer with the current wear data.
        return f"W{int(state.wear)}A{int(state.hours_since_zero_adjustment * 4)}"
    raise ValueError(f"Command {command} has no factory default")
