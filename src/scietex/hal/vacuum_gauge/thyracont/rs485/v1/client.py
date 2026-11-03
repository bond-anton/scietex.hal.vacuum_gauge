"""
Thyracont RS485 Version 1 Client Module.

This module provides a direct RS485 client for a Thyracont vacuum gauge speaking
protocol V1. Until now V1 existed only as a gateway bundle (framer, decoder, PDU,
translator, emulator): the gauge could be bridged to Modbus but never polled
directly over a serial port. This client closes that gap.

V1 is a command-oriented ASCII protocol. A request is a single-character command
plus up to six bytes of data; a response is a six-digit decimal string. It is
unrelated to Modbus on the wire — the gateway translator maps Modbus requests
onto V1 commands, and this client issues the commands directly.

Command coverage
----------------
Only the commands the V1 emulator implements are exposed. The V1 wire format is
reconstructed from this codebase rather than taken from a vendor document (see
``docs/protocol-v1.md``), so a command with no emulator branch has no second
implementation to cross-check against and is not implemented here:

+---------+--------+-----------------------------------------------+
| Command | Access | Meaning                                       |
+=========+========+===============================================+
| ``T``   | read   | Gauge type (six characters, not numeric)      |
+---------+--------+-----------------------------------------------+
| ``M``   | read   | Pressure                                      |
+---------+--------+-----------------------------------------------+
| ``m``   | write  | Pressure                                      |
+---------+--------+-----------------------------------------------+
| ``S``   | read   | Setpoint 1 or 2 (data selects which)          |
+---------+--------+-----------------------------------------------+
| ``s``   | write  | Setpoint select, then value                   |
+---------+--------+-----------------------------------------------+
| ``C``   | read   | Calibration 1 or 2 (data selects which)       |
+---------+--------+-----------------------------------------------+
| ``c``   | write  | Calibration select, then value                |
+---------+--------+-----------------------------------------------+
| ``I``   | read   | Penning state                                 |
+---------+--------+-----------------------------------------------+
| ``i``   | write  | Penning state                                 |
+---------+--------+-----------------------------------------------+
| ``W``   | read   | Penning sync                                  |
+---------+--------+-----------------------------------------------+
| ``w``   | write  | Penning sync                                  |
+---------+--------+-----------------------------------------------+
| ``j``   | write  | Atmosphere / zero adjustment                  |
+---------+--------+-----------------------------------------------+

The V2 comparison table lists further V1 commands (``A/a``, ``K/k``, ``D/d``,
``F``, ``H/h``, ``P/p``, ``U/u``) but none of them has an encoder, decoder,
translator address or emulator branch anywhere in the package, so their data
encoding is not determinable from source. They are deliberately absent.

Response handling
-----------------
A V1 response carries no status field: it is the device address, the command,
the data and a checksum. The gauge signals a rejected command with an empty
payload, so an empty response is treated as a failure rather than a value.

Classes:
    ThyracontRS485V1Gauge: An RS485 client for Thyracont V1 vacuum gauges.
"""

import asyncio
import sys
from collections.abc import Callable
from functools import wraps
from logging import Logger
from typing import Any

import serial
from pymodbus.pdu import ModbusPDU
from scietex.hal.serial import ModbusOperationError
from scietex.hal.serial.client import RS485Client
from scietex.hal.serial.config import (
    ModbusSerialConnectionConfigModel,
    SerialConnectionConfigModel,
)

from ....base.capabilities import (
    CalibrationCapabilities,
    GaugeCapabilities,
    PenningCapabilities,
    RelayCapabilities,
)
from ....base.protocol import VacuumGaugeProtocol
from ..checksum import check_checksum
from .data import _calibration_decode, _calibration_encode, _pressure_decode, _pressure_encode
from .decoder import ThyracontDecodePDU
from .framer import ThyracontASCIIFramer
from .request import ThyracontRequest

# Determine the correct TimeoutError based on Python version
if sys.version_info >= (3, 11):
    TimeoutErrorAlias = asyncio.TimeoutError
else:
    TimeoutErrorAlias = asyncio.exceptions.TimeoutError

# Adjustment payloads. The gauge accepts only these exact strings; anything else
# is answered with an empty payload and changes nothing.
_ATMOSPHERE_PAYLOAD = "100023"
_ZERO_PAYLOAD = "000000"

# Setpoint and calibration selectors are 1-based.
_SELECTORS = (1, 2)

# Error literals the gauge echoes instead of a value. They are the same strings
# the V2 protocol defines in ``ErrorMessage``; the V1 hardware shares them even
# though V1 has no access code to flag an error frame. A response equal to one
# of these is a rejection, not data.
_ERROR_LITERALS = frozenset(
    {
        "NO_DEF",
        "_LOGIC",
        "_RANGE",
        "ERROR1",
        "SYNTAX",
        "LENGTH",
        "_CD_RE",
        "_EP_RE",
        "_UNSUP",
        "_SEDIS",
    }
)


def parse_pressure(func: Callable) -> Callable:
    """Decode a pressure response wrapper."""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> float | None:
        """Decode the six-digit pressure string."""
        result: str | None = await func(*args, **kwargs)
        if result is not None:
            return _pressure_decode(result)
        return None

    return wrapper


def parse_calibration(func: Callable) -> Callable:
    """Decode a calibration response wrapper."""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> float | None:
        """Decode the calibration string."""
        result: str | None = await func(*args, **kwargs)
        if result is not None:
            return _calibration_decode(result)
        return None

    return wrapper


def parse_bool(func: Callable) -> Callable:
    """Parse boolean response wrapper."""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> bool:
        """Parse bool response."""
        result: str | None = await func(*args, **kwargs)
        if result is not None:
            try:
                return bool(int(result))
            except (TypeError, ValueError):
                return False
        return False

    return wrapper


# pylint: disable=too-many-public-methods
class ThyracontRS485V1Gauge(RS485Client, VacuumGaugeProtocol):
    """
    Thyracont vacuum gauge RS485 V1 client.

    V1 exposes a narrow control surface: pressure, two setpoints, two
    calibration points, the Penning state and a two-point adjustment. There is
    no display, no degas, no filament control and no factory-default command,
    so those capabilities are not claimed.

    The Penning sync flag is not claimed: the gauge answers the ``w`` write
    with an error literal (``_RANGE`` on a cathode-less Pirani gauge), so
    :meth:`set_penning_sync` logs the rejection rather than reporting success.
    Callers must consult :attr:`capabilities` before invoking it.

    The optional protocol methods V1 cannot serve are inherited from
    :class:`VacuumGaugeProtocol` and raise ``NotImplementedError``; callers must
    consult :attr:`capabilities` before invoking one.

    Attributes:
        capabilities (GaugeCapabilities): The V1 control surface.
    """

    capabilities = GaugeCapabilities(
        penning=PenningCapabilities(state=True, sync=False),
        relay=RelayCapabilities(count=2, modes=("pressure",)),
        calibration=CalibrationCapabilities(high=True, low=True),
    )
    measurement_unit = "mbar"
    display_name = "Thyracont RS485 V1"
    transport = "rs485"

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        connection_config: SerialConnectionConfigModel | ModbusSerialConnectionConfigModel,
        address: int = 1,
        label: str | None = None,
        logger: Logger | None = None,
        timeout: float | None = None,
        backend: str | None = None,
    ) -> None:
        """
        Initialize a ThyracontRS485V1Gauge client instance.

        Parameters
        ----------
        connection_config : Union[SerialConnectionConfigModel, ModbusSerialConnectionConfigModel]
            The serial connection configuration (e.g., port, baudrate).
        address : int, optional
            The device (slave) address. Defaults to 1.
        label : Optional[str], optional
            A custom label for the gauge. Defaults to "Vacuum Gauge" if None.
        logger : Optional[Logger], optional
            A logger instance for debugging. Defaults to None.
        timeout : Optional[float], optional
            The communication timeout in seconds. Defaults to 1.0 if None.
        backend : Optional[str], optional
            The communication backend ("pymodbus" or "pyserial"). Defaults to "pymodbus" if None.
        """
        _label = "Vacuum Gauge"
        if label is not None:
            _label = label
        self.timeout: float = 1.0
        if timeout is not None:
            self.timeout = timeout
        super().__init__(
            con_params=connection_config,
            address=address,
            label=_label,
            custom_framer=ThyracontASCIIFramer,
            custom_decoder=ThyracontDecodePDU,
            custom_response=[ThyracontRequest],
            logger=logger,
        )
        self.backend = "pymodbus"
        if backend == "pyserial":
            self.backend = "pyserial"

    async def connect(self) -> None:
        """Open the serial connection.

        `RS485Client` opens the port lazily inside each request, so there is
        nothing to do here. The method exists because `VacuumGaugeProtocol`
        requires it and the worker calls it before polling.
        """

    async def request_gauge(self, command: str, data: str | None = None) -> str | None:
        """
        Send a command to the gauge and return the response data.

        Parameters
        ----------
        command : str
            The single-character V1 command.
        data : Optional[str], optional
            Up to six characters of command data. Defaults to None.

        Returns
        -------
        Optional[str]
            The response payload, or None when the gauge did not answer, the
            frame failed its checksum, the payload was empty, or the gauge
            rejected the command with an error literal (``_RANGE``,
            ``_LOGIC``, ...). A rejection is logged at error level so it is
            distinguishable from a timeout.
        """
        result = None
        request = ThyracontRequest(
            command=command,
            data=data.encode() if data is not None else None,
            dev_id=self.address,
            transaction_id=0,
        )
        self.logger.debug("REQ: %s", request)
        if self.backend == "pymodbus":
            try:
                response: ModbusPDU | None = await asyncio.wait_for(
                    self.execute(request, no_response_expected=False),
                    timeout=self.timeout,
                )
                if response and hasattr(response, "data"):
                    self.logger.debug("Response: %s", response.data)
                    result = response.data
            except (TimeoutErrorAlias, ModbusOperationError) as exc:
                # scietex.hal.serial 2.x raises ModbusOperationError on bus/device
                # failure; the gauge API contract is "None on failure".
                self.logger.debug("Request failed: %s", exc)
                result = None
        elif self.backend == "pyserial":
            custom_framer = ThyracontASCIIFramer(ThyracontDecodePDU(is_server=False))
            encoded_frame = custom_framer.buildFrame(request)
            self.logger.debug("Encoded Frame: %s", encoded_frame)
            inter_byte_timeout = 0.01
            if hasattr(self.con_params, "inter_byte_timeout") and isinstance(
                self.con_params.inter_byte_timeout, float
            ):
                inter_byte_timeout = self.con_params.inter_byte_timeout
            con = serial.Serial(
                port=self.con_params.port,
                baudrate=self.con_params.baudrate,
                bytesize=self.con_params.bytesize,
                stopbits=self.con_params.stopbits,
                parity=self.con_params.parity,
                timeout=self.con_params.timeout,
                inter_byte_timeout=inter_byte_timeout,
            )
            con.write(encoded_frame)
            serial_response = con.readline()
            self.logger.debug("SERIAL READ: %s", serial_response)
            result = self._parse_response(serial_response)
            con.close()
        if result in _ERROR_LITERALS:
            self.logger.error("Gauge rejected %r: %s", command, result)
            return None
        return result

    def _parse_response(self, response: bytes) -> str | None:
        """
        Parse a raw serial response into its data payload.

        A V1 frame is ``<address:3><command:1><data:0..6><checksum:1>CR``. There
        is no access code and no length field, so the payload is everything
        between the command and the checksum.

        Parameters
        ----------
        response : bytes
            The raw frame read from the port.

        Returns
        -------
        Optional[str]
            The payload, or None when the frame is empty, fails its checksum,
            comes from another address, or carries no data.
        """
        self.logger.debug("Parsing response %s", response)
        if not response:
            return None
        if not check_checksum(response[:-2], response[-2]):
            self.logger.error("Wrong checksum")
            return None
        try:
            response_data: str = response.decode()[:-2]
            r_address: int = int(response_data[:3])
        except (UnicodeDecodeError, ValueError):
            self.logger.error("Malformed response %s", response)
            return None
        if self.address != r_address:
            self.logger.error("Wrong address")
            return None
        payload = response_data[4:]
        # An empty payload is how the gauge rejects a command; it is not a value.
        return payload or None

    async def get_model(self) -> str | None:
        """Retrieve the gauge type.

        The response is six characters, not a number, so it is returned as-is.
        """
        return await self.request_gauge(command="T")

    @parse_pressure
    async def measure(self) -> float | None:
        """Read the pressure in millibars."""
        return await self.request_gauge(command="M")

    async def set_pressure(self, pressure: float) -> bool:
        """Write the pressure setpoint value.

        The gauge echoes the written data, so a non-empty response means the
        command was accepted, not that the value was stored.
        """
        payload = _pressure_encode(pressure)
        result = await self.request_gauge(command="m", data=payload)
        return result is not None

    @parse_pressure
    async def get_setpoint(self, number: int) -> float | None:
        """Read setpoint ``number`` (1 or 2) in millibars."""
        if number not in _SELECTORS:
            raise ValueError(f"Setpoint number must be 1 or 2, got {number}")
        return await self.request_gauge(command="S", data=str(number))

    async def set_setpoint(self, number: int, pressure: float) -> bool:
        """Write setpoint ``number`` (1 or 2) in millibars.

        V1 writes a setpoint in two steps: a select command naming the setpoint,
        then a value command. The gauge clears the selection after the write, so
        the two commands must not be interleaved with another setpoint write.
        """
        if number not in _SELECTORS:
            raise ValueError(f"Setpoint number must be 1 or 2, got {number}")
        selected = await self.request_gauge(command="s", data=str(number))
        if selected is None:
            return False
        written = await self.request_gauge(command="s", data=_pressure_encode(pressure))
        return written is not None

    @parse_calibration
    async def get_calibration(self, number: int) -> float | None:
        """Read calibration point ``number`` (1 or 2)."""
        if number not in _SELECTORS:
            raise ValueError(f"Calibration number must be 1 or 2, got {number}")
        return await self.request_gauge(command="C", data=str(number))

    async def set_calibration(self, number: int, value: float) -> bool:
        """Write calibration point ``number`` (1 or 2).

        Like the setpoint write this is a select followed by a value, and the
        selection is cleared after the write.
        """
        if number not in _SELECTORS:
            raise ValueError(f"Calibration number must be 1 or 2, got {number}")
        selected = await self.request_gauge(command="c", data=str(number))
        if selected is None:
            return False
        written = await self.request_gauge(command="c", data=_calibration_encode(value))
        return written is not None

    async def get_relay(self, index: int) -> dict[str, Any] | None:
        """Read one relay's settings.

        V1 relays are pressure thresholds, so the result carries ``on`` and
        ``off`` set to the same pressure and ``mode`` set to ``"pressure"``.

        Args:
            index: Relay index, 1 or 2.

        Returns:
            dict[str, Any] | None: Relay settings, or ``None`` when the gauge
                reports no value.
        """
        pressure = await self.get_setpoint(index)
        if pressure is None:
            return None
        return {"on": pressure, "off": pressure, "mode": "pressure"}

    async def set_relay(self, index: int, settings: dict[str, Any]) -> None:
        """Write one relay's settings.

        Args:
            index: Relay index, 1 or 2.
            settings: Relay settings. ``on`` is the threshold pressure in
                millibars; ``mode`` must be ``"pressure"`` when present.

        Raises:
            ValueError: If the settings select a mode V1 does not support.
        """
        mode = settings.get("mode", "pressure")
        if mode != "pressure":
            raise ValueError(f"V1 relays only support the 'pressure' mode, got {mode!r}")
        if not await self.set_setpoint(index, settings["on"]):
            self.logger.error("Relay %s write rejected by the gauge", index)

    @parse_bool
    async def get_penning(self) -> bool:
        """Read the Penning (cold cathode) state."""
        return await self.request_gauge(command="I")

    async def set_penning(self, state: bool) -> None:
        """Switch the Penning (cold cathode) on or off.

        The gauge echoes the written value, so a non-empty response means the
        command was accepted. A rejected command is logged rather than raised:
        the protocol contract has no return value.
        """
        result = await self.request_gauge(command="i", data="1" if state else "0")
        if result is None:
            self.logger.error("Penning state write rejected by the gauge")

    @parse_bool
    async def get_penning_sync(self) -> bool:
        """Read the Penning sync flag."""
        return await self.request_gauge(command="W")

    async def set_penning_sync(self, state: bool) -> None:
        """Set the Penning sync flag.

        Like :meth:`set_penning`, a rejected write is logged, not raised.
        """
        result = await self.request_gauge(command="w", data="1" if state else "0")
        if result is None:
            self.logger.error("Penning sync write rejected by the gauge")

    async def adjust_high(self, pressure: float | None = None) -> None:
        """Run the atmosphere (high) adjustment.

        The adjustment is a three-step sequence: select the atmosphere mode,
        then send the fixed payload ``100023``. The gauge clears the selection
        after the payload, so the two commands must not be interleaved with
        another adjustment.

        Args:
            pressure: Ignored. V1 has no way to pass a reference pressure; the
                gauge uses its current reading.
        """
        _ = pressure
        selected = await self.request_gauge(command="j", data="1")
        if selected is None:
            self.logger.error("Atmosphere adjustment selection rejected by the gauge")
            return
        if await self.request_gauge(command="j", data=_ATMOSPHERE_PAYLOAD) is None:
            self.logger.error("Atmosphere adjustment payload rejected by the gauge")

    async def adjust_low(self, pressure: float | None = None) -> None:
        """Run the zero (low) adjustment.

        Like the atmosphere adjustment this is a select followed by the fixed
        payload ``000000``, and the selection is cleared after the payload.

        Args:
            pressure: Ignored. V1 has no way to pass a reference pressure; the
                gauge uses its current reading.
        """
        _ = pressure
        selected = await self.request_gauge(command="j", data="0")
        if selected is None:
            self.logger.error("Zero adjustment selection rejected by the gauge")
            return
        if await self.request_gauge(command="j", data=_ZERO_PAYLOAD) is None:
            self.logger.error("Zero adjustment payload rejected by the gauge")

    async def read_data(self) -> dict:
        """Read the gauge snapshot.

        Only ``pressure`` is guaranteed; V1 has no other continuously readable
        value that the protocol contract requires.
        """
        pressure = await self.measure()
        return {"pressure": pressure}
