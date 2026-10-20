"""
Thyracont Modbus/TCP Version 2 Client Module.

This module provides a Modbus/TCP client for Thyracont V2 vacuum gauges reached
through the Scietex Modbus gateway. The gateway translates standard Modbus
requests into the vendor's RS485 V2 protocol, so this client speaks plain
Modbus/TCP and never touches the vendor framing.

The V2 protocol is read-only: the gateway exposes FC03 reads only, and every
supported value is a float32 spanning two registers. The register map mirrors
`ThyracontV2Translator`:

    address 0   pressure
    address 2   gauge operating hours
    address 4   cathode operating hours
    address 6   Pirani wear
    address 8   Pirani hours since zero adjustment

Classes:
    ThyracontModbusV2Gauge: A Modbus/TCP client for Thyracont V2 gauges.
"""

import struct
from logging import Logger
from typing import Optional

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.pdu import ExceptionResponse

from scietex.hal.serial import ModbusOperationError
from scietex.hal.serial.utilities.numeric import ByteOrder, combine_32bit

from ....base.protocol import VacuumGaugeProtocol

# Register addresses, mirroring `ThyracontV2Translator`.
_REG_PRESSURE = 0
_REG_GAUGE_HOURS = 2
_REG_CATHODE_HOURS = 4
_REG_PIRANI_WEAR = 6
_REG_PIRANI_HOURS = 8

# Every V2 value spans two 16-bit registers holding one float32.
_FLOAT32_REGISTERS = 2


def _registers_to_float(registers: list[int]) -> float:
    """
    Decode two big-endian 16-bit registers into a float32 value.

    Args:
        registers: The two register values, high word first.

    Returns:
        float: The decoded value.
    """
    word = combine_32bit(registers[0], registers[1], ByteOrder.BIG_ENDIAN)
    return struct.unpack(">f", struct.pack(">I", word))[0]


class ThyracontModbusV2Gauge(VacuumGaugeProtocol):
    """
    Modbus/TCP client for a Thyracont V2 vacuum gauge behind the gateway.

    The V2 protocol is read-only, so every control capability flag is ``False``
    and only the read methods are implemented.

    Attributes:
        label (str): Human-readable gauge label.
        supports_penning (bool): Always ``False`` for V2.
        supports_setpoint (bool): Always ``False`` for V2.
        supports_calibration (bool): Always ``False`` for V2.
        supports_atmosphere (bool): Always ``False`` for V2.
        supports_zero (bool): Always ``False`` for V2.
    """

    supports_penning = False
    supports_setpoint = False
    supports_calibration = False
    supports_atmosphere = False
    supports_zero = False

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 1,
        label: str = "Thyracont Gauge",
        timeout: float = 1.0,
        logger: Optional[Logger] = None,
    ) -> None:
        """
        Initialize the client.

        Args:
            host: Gateway host name or address.
            port: Gateway TCP port.
            unit_id: Modbus unit id the gateway routes to the gauge.
            label: Human-readable gauge label.
            timeout: Per-request timeout in seconds.
            logger: Optional logger for diagnostics.
        """
        self.label = label
        self.unit_id = unit_id
        self.logger = logger
        self._host = host
        self._port = port
        self._timeout = timeout
        # `AsyncModbusTcpClient` binds to the running event loop in its
        # constructor, so it cannot be built here: the client is created in
        # `connect()`, which always runs inside the loop.
        self._client: Optional[AsyncModbusTcpClient] = None

    async def connect(self) -> None:
        """
        Open the TCP connection to the gateway.

        Raises:
            ModbusOperationError: If the gateway is unreachable. pymodbus
                reports a failed connect by returning ``False`` rather than
                raising, so the result is checked here; otherwise a caller
                would treat an unreachable gauge as connected and only fail
                later, on the first read.
        """
        if self._client is None:
            self._client = AsyncModbusTcpClient(
                self._host, port=self._port, timeout=self._timeout
            )
        if not await self._client.connect():
            raise ModbusOperationError(
                f"Failed to connect to vacuum gauge gateway at "
                f"{self._host}:{self._port}"
            )

    async def close(self) -> None:
        """Close the TCP connection to the gateway."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def _require_client(self) -> AsyncModbusTcpClient:
        """
        Return the connected client, or raise if ``connect()`` was not called.

        Raises:
            RuntimeError: If the client has not been connected.
        """
        if self._client is None:
            raise RuntimeError("Gauge is not connected; call connect() first")
        return self._client

    async def _read_float(self, address: int) -> float:
        """
        Read a float32 value from two holding registers.

        Args:
            address: Starting register address.

        Returns:
            float: The decoded value.

        Raises:
            ModbusOperationError: If the gateway returns an exception response.
        """
        response = await self._require_client().read_holding_registers(
            address, count=_FLOAT32_REGISTERS, device_id=self.unit_id
        )
        if isinstance(response, ExceptionResponse):
            raise ModbusOperationError(
                f"Read of register {address} failed: exception code {response.exception_code}"
            )
        return _registers_to_float(list(response.registers))

    async def measure(self) -> Optional[float]:
        """
        Read the current pressure.

        Returns:
            Optional[float]: Pressure in millibars.
        """
        return await self._read_float(_REG_PRESSURE)

    async def read_data(self) -> dict:
        """
        Read a snapshot of the gauge's current values.

        Returns:
            dict: ``pressure`` in millibars, plus operating hours and Pirani
                wear statistics.
        """
        return {
            "pressure": await self._read_float(_REG_PRESSURE),
            "gauge_hours": await self._read_float(_REG_GAUGE_HOURS),
            "cathode_hours": await self._read_float(_REG_CATHODE_HOURS),
            "pirani_wear": await self._read_float(_REG_PIRANI_WEAR),
            "pirani_hours": await self._read_float(_REG_PIRANI_HOURS),
        }
