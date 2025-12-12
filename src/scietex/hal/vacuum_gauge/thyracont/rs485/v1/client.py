"""
Thyracont RS485 Version 1 Client Module.

This module provides a custom RS485 client for interacting with a Thyracont vacuum gauge (e.g.,
MTM9D) over its RS485 protocol. It extends `scietex.hal.serial.client.RS485Client` and supports
two backends: `pymodbus` for Modbus-based communication and `pyserial` for direct serial
communication. The client uses custom framing, decoding, and request handling from the
`Thyracont.rs485.v1` subpackage to manage gauge operations such as pressure measurement,
calibration, setpoint adjustments, and Penning gauge control.

Classes:
    ThyracontVacuumGauge: An RS485 client class for Thyracont vacuum gauges, providing methods
        to read and write gauge data.
"""

from typing import Optional
import sys
import asyncio
from logging import Logger

import serial
from pymodbus.pdu import ModbusPDU

from scietex.hal.serial.config import (
    SerialConnectionConfigModel,
    ModbusSerialConnectionConfigModel,
)
from scietex.hal.serial.client import RS485Client

from .data import (
    _pressure_encode,
    _pressure_decode,
    _calibration_encode,
    _calibration_decode,
)
from ..checksum import check_checksum
from .framer import ThyracontASCIIFramer
from .decoder import ThyracontDecodePDU
from .request import ThyracontRequest


# Determine the correct TimeoutError based on Python version
if sys.version_info >= (3, 11):
    TimeoutErrorAlias = asyncio.TimeoutError
else:
    import asyncio.exceptions

    TimeoutErrorAlias = asyncio.exceptions.TimeoutError


class ThyracontVacuumGauge(RS485Client):
    """
    Thyracont vacuum gauge RS485 client.

    A custom RS485 client for interacting with a Thyracont vacuum gauge over its RS485 protocol.
    It extends `scietex.hal.serial.client.RS485Client` with Thyracont-specific framing
    (`ThyracontASCIIFramer`), decoding (`ThyracontDecodePDU`), and request handling
    (`ThyracontRequest`). The client supports two backends: `pymodbus` for Modbus-style
    communication and `pyserial` for direct serial interaction. It provides methods for reading
    the gauge model, measuring pressure, setting calibration and setpoints, and controlling
    the Penning gauge state.

    Attributes
    ----------
    timeout : float
        The timeout (in seconds) for communication requests (default 1.0).
    backend : str
        The communication backend, either "pymodbus" (default) or "pyserial".
    address : int
        The device (slave) address, inherited from `RS485Client`.
    con_params : SerialConnectionConfigModel | ModbusSerialConnectionConfigModel
        The serial connection configuration, inherited from `RS485Client`.
    label : str
        A label for the gauge (default "Thyracont Gauge"), inherited from `RS485Client`.
    logger : Optional[Logger]
        A logger instance for debugging, inherited from `RS485Client`.

    Methods
    -------
    __init__(connection_config, address=1, label=None, logger=None, timeout=None, backend=None)
        -> None
        Initializes the client with connection parameters and optional settings.
    request_gauge(command: str, data: Optional[bytes] = None) -> Optional[str]
        Sends a command to the gauge and returns the response data.
    _parse_response(response: bytes) -> dict
        Parses a raw serial response into a dictionary of components.
    get_model() -> Optional[str]
        Retrieves the gauge model identifier.
    measure() -> Optional[float]
        Measures the current pressure in millibars.
    set_pressure(pressure: float) -> Optional[float]
        Sets and returns the pressure value.
    get_calibration(cal_n: int = 1) -> Optional[float]
        Retrieves a calibration coefficient.
    set_calibration(cal_n: int = 1, value: float = 1.0) -> Optional[float]
        Sets a calibration coefficient.
    get_setpoint(sp_n: int = 1) -> Optional[float]
        Retrieves a setpoint pressure.
    set_setpoint(sp_n: int = 1, pressure: float = 1.0) -> Optional[float]
        Sets a setpoint pressure.
    set_atmosphere() -> Optional[float]
        Sets the atmosphere adjustment to 1000 mbar.
    set_zero() -> Optional[float]
        Sets the zero adjustment to 0 mbar.
    get_penning_state() -> Optional[bool]
        Retrieves the Penning gauge state.
    set_penning_state(state: bool) -> Optional[bool]
        Sets the Penning gauge state.
    get_penning_sync() -> Optional[bool]
        Retrieves the Penning synchronization state.
    set_penning_sync(state: bool) -> Optional[bool]
        Sets the Penning synchronization state.
    read_data() -> dict
        Reads and returns a dictionary of gauge data (currently only pressure).
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments,duplicate-code
    def __init__(
        self,
        connection_config: SerialConnectionConfigModel | ModbusSerialConnectionConfigModel,
        address: int = 1,
        label: Optional[str] = None,
        logger: Optional[Logger] = None,
        timeout: Optional[float] = None,
        backend: Optional[str] = None,
    ) -> None:
        """
        Initialize a ThyracontVacuumGauge client instance.

        Sets up the client with serial connection parameters, device address, and optional settings
        for label, logger, timeout, and backend. Configures the inherited `RS485Client` with
        Thyracont-specific framer, decoder, and response type.

        Parameters
        ----------
        connection_config : Union[SerialConnectionConfigModel, ModbusSerialConnectionConfigModel]
            The serial connection configuration (e.g., port, baudrate).
        address : int, optional
            The device (slave) address. Defaults to 1.
        label : Optional[str], optional
            A custom label for the gauge. Defaults to "Thyracont Gauge" if None.
        logger : Optional[Logger], optional
            A logger instance for debugging. Defaults to None.
        timeout : Optional[float], optional
            The communication timeout in seconds. Defaults to 1.0 if None.
        backend : Optional[str], optional
            The communication backend ("pymodbus" or "pyserial"). Defaults to "pymodbus" if None.
        """
        _label = "Thyracont Gauge"
        if label is not None:  # Corrected logic to use provided label
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

    # pylint: disable=duplicate-code
    async def request_gauge(self, command: str, data: Optional[bytes] = None) -> Optional[str]:
        """
        Send a command to the gauge and return the response data.

        Executes a request to the gauge using the specified command and optional data payload,
        handling communication via the selected backend ("pymodbus" or "pyserial"). Returns the
        response data as a string, or None if the request fails.

        Parameters
        ----------
        command : str
            The single-character command to send (e.g., "M", "s").
        data : Optional[bytes], optional
            The data payload to send with the command (e.g., b"123456"). Defaults to None.

        Returns
        -------
        Optional[str]
            The response data as a string (e.g., "123456"), or None if the request times out
            or fails.
        """
        result = None
        request = ThyracontRequest(
            command=command, data=data, dev_id=self.address, transaction_id=0
        )
        if self.backend == "pymodbus":
            try:
                response: Optional[ModbusPDU] = await asyncio.wait_for(
                    self.execute(request, no_response_expected=False),
                    timeout=self.timeout,
                )
                if response and hasattr(response, "data"):
                    self.logger.debug("Response: %s", response.data)
                    result = response.data
            except TimeoutErrorAlias:
                result = None
        elif self.backend == "pyserial":
            custom_framer = ThyracontASCIIFramer(ThyracontDecodePDU(is_server=False))
            encoded_frame = custom_framer.buildFrame(request)  # Corrected method name
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
            parsed = self._parse_response(serial_response)
            result = parsed["data"]
            con.close()
        return result

    def _parse_response(self, response: bytes) -> dict:
        """
        Parse a raw serial response into a dictionary of components.

        Analyzes a response frame from the gauge (e.g., b"001M123456X\\r") to extract the address,
        command, data, and checksum. Validates the checksum and address, logging errors if they
        don’t match expectations.

        Parameters
        ----------
        response : bytes
            The raw response frame from the gauge.

        Returns
        -------
        dict
            A dictionary with keys:
            - "addr": The device address (int) or None if invalid.
            - "cmd": The command character (str) or None if invalid.
            - "data": The data payload (str) or None if invalid.
            - "crc": The checksum byte (int) or None if invalid.
        """
        # pylint: disable=too-many-branches
        result: dict = {"addr": None, "cmd": None, "data": None, "crc": None}
        self.logger.debug("Parsing response %s", response)
        if response:
            if check_checksum(response[:-2], response[-2]):
                response_data: str = response.decode()[:-2]
                r_address: int = int(response_data[:3])
                if self.address == r_address:
                    result["addr"] = self.address
                    result["cmd"] = response_data[3]
                    result["data"] = response_data[4:]
                    result["crc"] = response[-2]
                else:
                    self.logger.error("Wrong address")
                    return result
            else:
                self.logger.error("Wrong checksum")
                return result
        return result

    async def get_model(self) -> Optional[str]:
        """
        Retrieve the gauge model identifier.

        Sends the "T" command to the gauge and returns the model string (e.g., "MTM09D").

        Returns
        -------
        Optional[str]
            The model identifier, or None if the request fails.
        """
        return await self.request_gauge("T")

    async def measure(self) -> Optional[float]:
        """
        Measure the current pressure in millibars.

        Sends the "M" command to read the current pressure and decodes it from the response.

        Returns
        -------
        Optional[float]
            The pressure value in millibars (mbar), or None if the request or decoding fails.
        """
        gauge_data: Optional[str] = await self.request_gauge("M")
        if gauge_data is not None:
            return _pressure_decode(gauge_data)
        return None

    async def set_pressure(self, pressure: float) -> Optional[float]:
        """
        Set and return the pressure value.

        Sends the "m" command with an encoded pressure value and returns the decoded response.

        Parameters
        ----------
        pressure : float
            The pressure value to set in millibars (mbar).

        Returns
        -------
        Optional[float]
            The set pressure value in millibars (mbar), or None if the request fails.
        """
        gauge_data = await self.request_gauge("m", _pressure_encode(pressure).encode())
        if gauge_data is not None:
            return _pressure_decode(gauge_data)
        return None

    async def get_calibration(self, cal_n: int = 1) -> Optional[float]:
        """
        Retrieve a calibration coefficient.

        Sends the "C" command with the calibration number (1 or 2) and decodes the response.

        Parameters
        ----------
        cal_n : int, optional
            The calibration number (1 or 2). Defaults to 1.

        Returns
        -------
        Optional[float]
            The calibration coefficient, or None if the request or decoding fails.
        """
        gauge_data = await self.request_gauge("C", str(cal_n).encode())
        if gauge_data is not None:
            return _calibration_decode(gauge_data)
        return None

    async def set_calibration(self, cal_n: int = 1, value: float = 1.0) -> Optional[float]:
        """
        Set a calibration coefficient.

        Sends the "c" command to select the calibration number (1 or 2), then sets the value if
        selection is confirmed, and returns the decoded result.

        Parameters
        ----------
        cal_n : int, optional
            The calibration number (1 or 2). Defaults to 1.
        value : float, optional
            The calibration value to set. Defaults to 1.0.

        Returns
        -------
        Optional[float]
            The set calibration value, or None if the request or confirmation fails.
        """
        gauge_data = await self.request_gauge("c", str(cal_n).encode())
        if gauge_data and gauge_data == str(cal_n):
            data = _calibration_encode(value).encode()
            data_str = await self.request_gauge("c", data)
            if data_str is not None:
                return _calibration_decode(data_str)
        return None

    async def get_setpoint(self, sp_n: int = 1) -> Optional[float]:
        """
        Retrieve a setpoint pressure.

        Sends the "S" command with the setpoint number (1 or 2) and decodes the response.

        Parameters
        ----------
        sp_n : int, optional
            The setpoint number (1 or 2). Defaults to 1.

        Returns
        -------
        Optional[float]
            The setpoint pressure in millibars (mbar), or None if the request or decoding fails.
        """
        data = await self.request_gauge("S", str(sp_n).encode())
        if data is not None:
            return _pressure_decode(data)
        return None

    async def set_setpoint(self, sp_n: int = 1, pressure: float = 1.0) -> Optional[float]:
        """
        Set a setpoint pressure.

        Sends the "s" command to select the setpoint number (1 or 2), then sets the pressure if
        selection is confirmed, and returns the decoded result.

        Parameters
        ----------
        sp_n : int, optional
            The setpoint number (1 or 2). Defaults to 1.
        pressure : float, optional
            The setpoint pressure to set in millibars (mbar). Defaults to 1.0.

        Returns
        -------
        Optional[float]
            The set setpoint pressure in millibars (mbar), or None if the request
            or confirmation fails.
        """
        gauge_data = await self.request_gauge("s", str(sp_n).encode())
        if gauge_data and int(gauge_data) == sp_n:
            data = _pressure_encode(pressure).encode()
            data_str = await self.request_gauge("s", data)
            if data_str is not None:
                return _pressure_decode(data_str)
        return None

    async def set_atmosphere(self) -> Optional[float]:
        """
        Set the atmosphere adjustment to 1000 mbar.

        Sends the "j" command with data "1" to initiate atmosphere adjustment, then sets 1000 mbar
        if confirmed, and returns the decoded result.

        Returns
        -------
        Optional[float]
            The adjusted pressure (1000 mbar) if successful, or None if the request
            or confirmation fails.
        """
        gauge_data = await self.request_gauge("j", str(1).encode())
        if gauge_data and int(gauge_data) == 1:
            data = _pressure_encode(1000).encode()
            data_str = await self.request_gauge("j", data)
            if data_str is not None:
                return _pressure_decode(data_str)
        return None

    async def set_zero(self) -> Optional[float]:
        """
        Set the zero adjustment to 0 mbar.

        Sends the "j" command with data "0" to initiate zero adjustment, then sets 0 mbar if
        confirmed, and returns the decoded result.

        Returns
        -------
        Optional[float]
            The adjusted pressure (0 mbar) if successful, or None if the request
            or confirmation fails.
        """
        gauge_data = await self.request_gauge("j", str(0).encode())
        if gauge_data and int(gauge_data) == 0:
            data = _pressure_encode(0).encode()
            data_str = await self.request_gauge("j", data)
            if data_str is not None:
                return _pressure_decode(data_str)
        return None

    async def get_penning_state(self) -> Optional[bool]:
        """
        Retrieve the Penning gauge state.

        Sends the "I" command to read the Penning gauge state and converts it to a boolean.

        Returns
        -------
        Optional[bool]
            The Penning gauge state (True if on, False if off), or None if the request fails.
        """
        data = await self.request_gauge("I")
        if data:
            return bool(int(data))
        return None

    async def set_penning_state(self, state: bool) -> Optional[bool]:
        """
        Set the Penning gauge state.

        Sends the "i" command with the state (0 or 1) and returns the confirmed state.

        Parameters
        ----------
        state : bool
            The state to set (True for on, False for off).

        Returns
        -------
        Optional[bool]
            The set Penning gauge state, or None if the request fails.
        """
        gauge_data = str(int(bool(state))).encode()
        data_str = await self.request_gauge("i", gauge_data)
        if data_str is not None:
            return bool(int(data_str))
        return None

    async def get_penning_sync(self) -> Optional[bool]:
        """
        Retrieve the Penning synchronization state.

        Sends the "W" command to read the Penning synchronization state and converts it
        to a boolean.

        Returns
        -------
        Optional[bool]
            The Penning synchronization state (True if on, False if off), or None
            if the request fails.
        """
        data = await self.request_gauge("W")
        if data:
            return bool(int(data))
        return None

    async def set_penning_sync(self, state: bool) -> Optional[bool]:
        """
        Set the Penning synchronization state.

        Sends the "w" command with the state (padded to 6 digits) and returns the confirmed state.

        Parameters
        ----------
        state : bool
            The synchronization state to set (True for on, False for off).

        Returns
        -------
        Optional[bool]
            The set Penning synchronization state, or None if the request fails.
        """
        gauge_data = f"{int(bool(state)):06d}".encode()
        data_str = await self.request_gauge("w", gauge_data)
        if data_str is not None:
            return bool(int(data_str))
        return None

    async def read_data(self) -> dict:
        """
        Read and return a dictionary of gauge data.

        Currently, retrieves only the pressure value, but can be extended to include
        additional data.

        Returns
        -------
        dict
            A dictionary with at least the key "pressure" mapping to the current pressure value
            (float or None).
        """
        pressure = await self.measure()
        data = {
            "pressure": pressure,
        }
        return data
