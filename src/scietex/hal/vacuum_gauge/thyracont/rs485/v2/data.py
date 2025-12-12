"""
Thyracont RS485 Version 2 Data Module.
"""

from typing import Optional
from enum import Enum


class AccessCode(Enum):
    """Access codes for RS485 V2 protocol."""

    # Access Codes for Send Sequences (Master->Transmitter).
    READ = 0
    WRITE = 2
    FACTORY_DEFAULT = 4
    BINARY = 8
    # Special Access Codes for Receive Sequences (Transmitter->Master).
    STREAMING = 6
    ERROR = 7

    @classmethod
    def from_int(cls, value: int) -> "AccessCode":
        """
        Converts an integer value to the corresponding `AccessCode` member.

        Args:
            value (int): The integer code.

        Returns:
            AccessCode: The corresponding `AccessCode` member.

        Raises:
            ValueError: If the integer value does not match any supported access code.
        """
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(
            f"Unknown access code: {value}. Supported values are: {[m.value for m in cls]}"
        )


class ErrorMessage(Enum):
    """Error messages for RS485 V2 protocol."""

    NO_DEF = "NO_DEF"
    LOGIC = "_LOGIC"
    RANGE = "_RANGE"
    SENSOR_ERROR = "ERROR1"
    SYNTAX = "SYNTAX"
    LENGTH = "LENGTH"
    CD_RE = "_CD_RE"
    EP_RE = "_EP_RE"
    UNSUPPORTED_DATA = "_UNSUP"
    SENSOR_DISABLED = "_SEDIS"

    @classmethod
    def from_str(cls, value: str) -> "ErrorMessage":
        """
        Converts a string value to the corresponding `ErrorMessage` member.

        Args:
            value (str): The error message.

        Returns:
            ErrorMessage: The corresponding `ErrorMessage` member.

        Raises:
            ValueError: If the string value does not match any supported error message.
        """
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(
            f"Unknown error message: {value}. Supported values are: {[m.value for m in cls]}"
        )

    def description(self) -> str:
        """Error description."""
        description: dict[str, str] = {
            "NO_DEF": "Command is not valid (not defined) for device.",
            "_LOGIC": "Access Code is not valid or execution of command is not logical.",
            "_RANGE": "Value in send request is out of range.",
            "ERROR1": "Sensor is defect or stacked out.",
            "SYNTAX": "Command is valid, but the syntax in data is wrong "
            "or the selected mode in data is not valid for your device.",
            "LENGTH": "Command is valid, but the length of data is out of expected range.",
            "_CD_RE": "Calibration data read error.",
            "_EP_RE": "EEPROM Read Error.",
            "_UNSUP": "Unsupported Data (not valid value).",
            "_SEDIS": "Sensor element disabled.",
        }
        return description[self.value]


class Sensor(Enum):
    """Sensor enumeration."""

    AUTO = 0
    PIRANI = 1
    PIEZO = 2
    HOT_CATHODE = 3
    COLD_CATHODE = 4
    AMBIENT = 6
    RELATIVE = 7

    @classmethod
    def from_int(cls, value: int) -> "Sensor":
        """
        Converts an integer value to the corresponding `Sensor` member.

        Args:
            value (int): The integer code.

        Returns:
            Sensor: The corresponding `Sensor` member.

        Raises:
            ValueError: If the integer value does not match any sensor code.
        """
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(
            f"Unknown sensor code: {value}. Supported values are: {[m.value for m in cls]}"
        )


class StreamingMode(Enum):
    """Streaming mode enumeration."""

    V1 = 1
    V2 = 2
    V1_FRAMELESS = 3
    V2_FRAMELESS = 4


class DisplayOrientation(Enum):
    """Supported display orientations."""

    GAUGE_UP = 0
    GAUGE_DOWN = 1


class DisplayUnits(Enum):
    """Supported display units"""

    MBAR = "mbar"
    TORR = "torr"
    HPA = "hPa"

    @classmethod
    def from_str(cls, value: str) -> "DisplayUnits":
        """
        Converts a string value to the corresponding `DisplayUnits` member.

        Args:
            value (str): The error message.

        Returns:
            DisplayUnits: The corresponding `DisplayUnits` member.

        Raises:
            ValueError: If the string value does not match any supported units.
        """
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(
            f"Unknown display units: {value}. Supported values are: {[m.value for m in cls]}"
        )


class CathodeControlMode(Enum):
    """Supported Cathode control modes."""

    MANUAL = 0
    AUTO = 1


def decode_float(data: str) -> Optional[float]:
    """Decode string to float value."""
    if data is None or len(data) == 0:
        return None
    if data == "OR":  # Over range
        return 999999.0
    if data == "UR":  # Under range
        return 0.0
    try:
        return float(data)
    except (ValueError, TypeError):
        return None


def encode_float(value: float) -> str:
    """Encode float value to string."""
    mantissa, exp = f"{value:1.3e}".split("e")
    exp_val = int(exp)
    return mantissa + f"e{exp_val:d}"


def encode_float_1(value: float) -> str:
    """Encode float value to string."""
    mantissa, exp = f"{value:1.1e}".split("e")
    if mantissa[-1] == "0":
        mantissa = mantissa[0]
    exp_val = int(exp)
    return mantissa + f"e{exp_val:d}"


def decode_range(data: str) -> dict[str, Optional[float]]:
    """Decode string with range data to dict."""
    result: dict[str, Optional[float]] = {"high": None, "low": None}
    try:
        high, low = data.split("L")
        _, high = high.split("H")
        result["high"] = float(high)
        result["low"] = float(low)
    except (ValueError, TypeError):
        pass
    return result


def encode_range(limits: dict[str, float]) -> str:
    """Decode dict with range limits to range data string."""
    return f"H{encode_float_1(limits['high'])}L{encode_float_1(limits['low'])}"


def decode_sensor_transition(st_data: str) -> Optional[dict[str, Optional[int | float]]]:
    """Decode relay data to dict."""
    result: dict[str, Optional[int | float]] = {"mode": None, "from": None, "to": None, "D": None}
    try:
        if "D" in st_data:
            result["D"] = float(st_data[1:])
        elif "T" in st_data:
            f, t = st_data.split("T")
            _, f = f.split("F")
            result["to"] = float(t)
            result["from"] = float(f)
        else:
            result["mode"] = int(st_data)
    except (ValueError, TypeError):
        pass
    return result


def encode_sensor_transition(st_data: dict[str, Optional[int | float]]) -> Optional[bytes]:
    """Encode sensor transition data."""
    data: Optional[bytes] = None
    data_line: str = ""
    try:
        if st_data["mode"] is None:
            if st_data["from"] is not None and st_data["to"] is not None:
                data_line += f"F{encode_float_1(st_data['from'])}T{encode_float_1(st_data['to'])}"
            elif st_data["D"] is not None:
                data_line += f"D{int(st_data['D']):d}"
        else:
            data_line += f"{st_data['mode']}"
        if data_line:
            data = data_line.encode()
    except (KeyError, TypeError, ValueError):
        pass
    return data


def decode_relay_data(rl_data: str) -> Optional[dict[str, Optional[float | str]]]:
    """Decode relay data to dict."""
    result = {"on": 0.0, "off": 0.0, "D": None, "C": None, "mode": "pressure"}
    if rl_data in ("E", "!E", "U", "!U", "O", "!O", "C", "!C", "W", "!W", "T0", "T1"):
        result["mode"] = rl_data
    else:
        try:
            t, f = rl_data.split("F")
            _, t = t.split("T")
            result["on"] = float(t)
            if "D" in f:
                f, d = f.split("D")
                result["D"] = int(d)
            elif "C" in f:
                f, c = f.split("C")
                result["C"] = int(c)
            result["off"] = float(f)
        except (ValueError, TypeError):
            pass
    return result


def encode_relay_data(rl_data: dict) -> Optional[bytes]:
    """Encode relay data."""
    try:
        if rl_data["mode"] == "pressure":
            data = f"T{encode_float_1(rl_data['on'])}F{encode_float_1(rl_data['off'])}"
            if rl_data["D"] is not None:
                data += f"D{int(rl_data['D']):d}"
            if rl_data["C"] is not None:
                data += f"C{int(rl_data['C']):d}"
        else:
            data = rl_data["mode"]
        return data.encode()
    except (KeyError, TypeError, ValueError):
        pass
    return None


def decode_output_characteristic(oc_data: str) -> dict[str, Optional[str | int | float]]:
    """Decode output characteristics to convenient dictionary."""
    result: dict[str, Optional[str | int | float]] = {"mode": oc_data[:3]}
    if result["mode"] in ("Lin", "Log"):
        result.update(
            {
                "gain": None,
                "offset": None,
                "lower_limit": None,
                "upper_limit": None,
                "under_range": None,
                "over_range": None,
                "fault": None,
                "D": None,
            }
        )
        _, data = oc_data.split("G", 1)
        g, data = data.split("O", 1)
        result["gain"] = float(g)
        o, data = data.split("L", 1)
        result["offset"] = float(o)
        l, data = data.split("L", 1)
        result["lower_limit"] = float(l)
        l, data = data.split("U", 1)
        result["upper_limit"] = float(l)
        u, data = data.split("O", 1)
        result["under_range"] = float(u)
        o, data = data.split("F", 1)
        result["over_range"] = float(o)
        result["fault"] = float(data)
        if "D" in data:
            _, d = data.split("D")
            result["D"] = int(d)
    elif result["mode"] == "Tab":
        if "S" in oc_data:
            _, data = oc_data.split("S", 1)
            s, data = data.split("U")
            result.update({"size": int(s)})
            u, data = data.split("O")
            result["under_range"] = float(u)
            o, data = data.split("F")
            result["over_range"] = float(o)
            result["fault"] = float(data)
    else:
        result["mode"] = "Tab"
        if "P" in oc_data:
            p, u = oc_data.split("U")
            _, p = p.split("P")
            result.update({"pressure": float(p)})
            result.update({"voltage": float(u)})
    return result


def encode_tab_output_characteristic(oc: dict[str, Optional[str | int | float]]) -> str:
    """Encode Tab output characteristics from dictionary."""
    data = ""
    if "size" in oc:
        data = f"TabS{oc['size']}U{oc['under_range']}O{oc['over_range']}F{oc['fault']}"
    elif "node" in oc:
        data = f"TabE{oc['node']}P{oc['pressure']}U{oc['voltage']}"
    return data


def decode_operating_hours(oh_data: Optional[str]) -> Optional[dict[str, Optional[float]]]:
    """Decode operating-hours response."""
    if oh_data:
        try:
            result = {"gauge": 0.0, "cathode": None}
            if "C" in oh_data:
                g, c = oh_data.split("C")
                result["gauge"] = float(g) / 4
                result["cathode"] = float(c) / 4
            else:
                result["gauge"] = float(oh_data) / 4
            return result
        except (TypeError, ValueError):
            pass
    return None


def decode_wear_status(pm_data: Optional[str]) -> Optional[dict[str, Optional[float | str]]]:
    """Decode sensor wear estimation response."""
    if pm_data:
        try:
            result: Optional[dict[str, Optional[float | str]]]
            if "A" in pm_data:  # Pirani W[int]A[int]
                result = {"wear": 0.0, "status": None, "hours_since_calibration": None}
                w, a = pm_data.split("A")
                _, w = w.split("W")
                wear = float(w)
                if wear == 32767:
                    result["status"] = "not calculated"
                elif wear < 0:
                    result["status"] = "corrosion"
                else:
                    result["status"] = "contamination"
                result["wear"] = abs(wear)
                result["hours_since_zero_adjustment"] = float(a) / 4
            elif "S" in pm_data:  # Hot cathode F[int]S[int]
                result = {
                    "wear_1": 0.0,
                    "wear_2": 0.0,
                }
                f, s = pm_data.split("S")
                _, f = f.split("F")
                result["wear_1"] = float(f)
                result["wear_2"] = float(s)
            else:  # Cold cathode W[int]
                result = {"wear": float(pm_data[1:])}
            return result
        except (TypeError, ValueError):
            pass
    return None


def adjust_baudrate(baud: int, max_baud=250000) -> int:
    """Adjust baudrate."""
    _baud = max(9600, min(baud, max_baud))
    if baud <= 9600:
        _baud = 9600
    elif baud <= 14400:
        _baud = 14400
    elif baud <= 19200:
        _baud = 19200
    elif baud <= 28800:
        _baud = 28800
    elif baud <= 38400:
        _baud = 38400
    elif baud <= 57600:
        _baud = 57600
    elif baud <= 115200:
        _baud = 115200
    elif baud <= 230400:
        _baud = 230400
    else:
        _baud = 250000
    return _baud
