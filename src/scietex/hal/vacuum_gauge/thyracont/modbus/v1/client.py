"""
Thyracont Modbus/TCP Version 1 Client Module.

This module provides a Modbus/TCP client for Thyracont vacuum gauges reached
through the Scietex Modbus gateway. The gateway translates standard Modbus
requests into the vendor's RS485 V1 protocol, so this client speaks plain
Modbus/TCP (FC03/FC06/FC16) and never touches the vendor framing.

The register map mirrors `ThyracontV1Translator`, which is the single source of
truth for the gateway-side translation:

    address 0   pressure, 32-bit, 2 registers
    address 2   setpoint 1, 32-bit, 2 registers
    address 4   setpoint 2, 32-bit, 2 registers
    address 6   calibration 1, 16-bit, 1 register
    address 7   calibration 2, 16-bit, 1 register
    address 8   Penning state, 16-bit, 1 register
    address 9   Penning sync, 16-bit, 1 register
    address 10  setpoint select (1 or 2), 16-bit
    address 11  setpoint value, 32-bit
    address 12  calibration select (1 or 2), 16-bit
    address 13  calibration value, 32-bit

Classes:
    ThyracontModbusV1Gauge: A Modbus/TCP client for Thyracont V1 gauges.
"""

from logging import Logger

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.pdu import ExceptionResponse
from scietex.hal.serial import ModbusOperationError
from scietex.hal.serial.utilities.numeric import combine_32bit, split_32bit

from ....base.protocol import VacuumGaugeProtocol
from ...rs485.v1.data import _pressure_decode, _pressure_encode

# Register addresses, mirroring `ThyracontV1Translator`.
_REG_PRESSURE = 0
_REG_SETPOINT_1 = 2
_REG_SETPOINT_2 = 4
_REG_CALIBRATION_1 = 6
_REG_CALIBRATION_2 = 7
_REG_PENNING_STATE = 8
_REG_PENNING_SYNC = 9
_REG_SETPOINT_SELECT = 10
_REG_SETPOINT_VALUE = 11
_REG_CALIBRATION_SELECT = 12
_REG_CALIBRATION_VALUE = 13


def _decode_pressure(raw: int) -> float | None:
    """
    Decode a six-digit vendor pressure value into millibars.

    The gateway returns the vendor's six-digit decimal as a 32-bit integer, so
    the value is formatted back to its string form before decoding.

    Args:
        raw: The 32-bit integer the gateway returned for the pressure register.

    Returns:
        Optional[float]: Pressure in millibars, or ``None`` when the value is
            not a valid six-digit encoding.
    """
    if raw <= 0:
        return None
    return _pressure_decode(f"{raw:06d}")


def _encode_pressure(pressure: float) -> int:
    """
    Encode a pressure in millibars into the six-digit vendor representation.

    Args:
        pressure: Pressure in millibars.

    Returns:
        int: The six-digit integer the gateway expects for the pressure register.

    Raises:
        ValueError: If the pressure is not positive.
    """
    if pressure <= 0:
        raise ValueError(f"Pressure must be positive, got {pressure}")
    return int(_pressure_encode(pressure))


class ThyracontModbusV1Gauge(VacuumGaugeProtocol):
    """
    Modbus/TCP client for a Thyracont V1 vacuum gauge behind the gateway.

    The client owns one TCP connection to the gateway and addresses the gauge by
    its Modbus unit id. It implements the full V1 control surface: pressure,
    setpoints, calibration, Penning state and Penning sync.

    Attributes:
        label (str): Human-readable gauge label.
        supports_penning (bool): Always ``True`` for V1.
        supports_setpoint (bool): Always ``True`` for V1.
        supports_calibration (bool): Always ``True`` for V1.
        supports_atmosphere (bool): Always ``True`` for V1.
        supports_zero (bool): Always ``True`` for V1.
    """

    supports_penning = True
    supports_setpoint = True
    supports_calibration = True
    supports_atmosphere = True
    supports_zero = True
    measurement_unit = "mbar"

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 1,
        label: str = "Thyracont Gauge",
        timeout: float = 1.0,
        logger: Logger | None = None,
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
        self._client: AsyncModbusTcpClient | None = None

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
            self._client = AsyncModbusTcpClient(self._host, port=self._port, timeout=self._timeout)
        if not await self._client.connect():
            raise ModbusOperationError(
                f"Failed to connect to vacuum gauge gateway at {self._host}:{self._port}"
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

    async def _read_registers(self, address: int, count: int) -> list[int]:
        """
        Read holding registers, raising on a Modbus exception response.

        Args:
            address: Starting register address.
            count: Number of registers to read.

        Returns:
            list[int]: The register values.

        Raises:
            ModbusOperationError: If the gateway returns an exception response.
        """
        response = await self._require_client().read_holding_registers(
            address, count=count, device_id=self.unit_id
        )
        if isinstance(response, ExceptionResponse):
            raise ModbusOperationError(
                f"Read of register {address} failed: exception code {response.exception_code}"
            )
        return list(response.registers)

    async def _write_register(self, address: int, value: int) -> None:
        """
        Write a single holding register, raising on a Modbus exception response.

        Args:
            address: Register address.
            value: Value to write.

        Raises:
            ModbusOperationError: If the gateway returns an exception response.
        """
        response = await self._require_client().write_register(
            address, value, device_id=self.unit_id
        )
        if isinstance(response, ExceptionResponse):
            raise ModbusOperationError(
                f"Write of register {address} failed: exception code {response.exception_code}"
            )

    async def _write_registers(self, address: int, values: list[int]) -> None:
        """
        Write multiple holding registers, raising on a Modbus exception response.

        Args:
            address: Starting register address.
            values: Values to write.

        Raises:
            ModbusOperationError: If the gateway returns an exception response.
        """
        response = await self._require_client().write_registers(
            address, values, device_id=self.unit_id
        )
        if isinstance(response, ExceptionResponse):
            raise ModbusOperationError(
                f"Write of registers {address} failed: exception code {response.exception_code}"
            )

    async def measure(self) -> float | None:
        """
        Read the current pressure.

        Returns:
            Optional[float]: Pressure in millibars, or ``None`` when the gauge
                reports no valid reading.
        """
        registers = await self._read_registers(_REG_PRESSURE, 2)
        return _decode_pressure(combine_32bit(registers[0], registers[1]))

    async def read_data(self) -> dict:
        """
        Read a snapshot of the gauge's current values.

        Returns:
            dict: ``pressure`` in millibars, plus ``penning_state`` and
                ``penning_sync`` when the gauge reports them.
        """
        data: dict = {"pressure": await self.measure()}
        penning = await self._read_registers(_REG_PENNING_STATE, 1)
        data["penning_state"] = bool(penning[0])
        sync = await self._read_registers(_REG_PENNING_SYNC, 1)
        data["penning_sync"] = bool(sync[0])
        return data

    async def set_pressure(self, pressure: float) -> None:
        """
        Write the pressure register.

        Args:
            pressure: Pressure in millibars.
        """
        raw = _encode_pressure(pressure)
        await self._write_registers(_REG_PRESSURE, list(split_32bit(raw)))

    async def get_setpoint(self, index: int = 1) -> float | None:
        """
        Read a setpoint.

        Args:
            index: Setpoint index, 1 or 2.

        Returns:
            Optional[float]: Setpoint pressure in millibars.
        """
        address = _REG_SETPOINT_1 if index == 1 else _REG_SETPOINT_2
        registers = await self._read_registers(address, 2)
        return _decode_pressure(combine_32bit(registers[0], registers[1]))

    async def set_setpoint(self, index: int, pressure: float) -> None:
        """
        Write a setpoint.

        The gateway requires the select register to be written before the value
        register, otherwise the write lands on whichever setpoint was selected
        last.

        Args:
            index: Setpoint index, 1 or 2.
            pressure: Setpoint pressure in millibars.
        """
        await self._write_register(_REG_SETPOINT_SELECT, index)
        raw = _encode_pressure(pressure)
        await self._write_registers(_REG_SETPOINT_VALUE, list(split_32bit(raw)))

    async def get_calibration(self, index: int = 1) -> float | None:
        """
        Read a calibration coefficient.

        Args:
            index: Calibration index, 1 or 2.

        Returns:
            Optional[float]: The calibration coefficient.
        """
        address = _REG_CALIBRATION_1 if index == 1 else _REG_CALIBRATION_2
        registers = await self._read_registers(address, 1)
        return float(registers[0])

    async def set_calibration(self, index: int, value: float) -> None:
        """
        Write a calibration coefficient.

        Args:
            index: Calibration index, 1 or 2.
            value: The calibration coefficient.
        """
        await self._write_register(_REG_CALIBRATION_SELECT, index)
        await self._write_registers(_REG_CALIBRATION_VALUE, list(split_32bit(int(value))))

    async def get_penning_state(self) -> bool:
        """
        Read the Penning gauge state.

        Returns:
            bool: Whether the Penning gauge is on.
        """
        registers = await self._read_registers(_REG_PENNING_STATE, 1)
        return bool(registers[0])

    async def set_penning_state(self, state: bool) -> None:
        """
        Set the Penning gauge state.

        Args:
            state: Whether to turn the Penning gauge on.
        """
        await self._write_register(_REG_PENNING_STATE, int(state))

    async def get_penning_sync(self) -> bool:
        """
        Read the Penning synchronization state.

        Returns:
            bool: Whether Penning sync is enabled.
        """
        registers = await self._read_registers(_REG_PENNING_SYNC, 1)
        return bool(registers[0])

    async def set_penning_sync(self, state: bool) -> None:
        """
        Set the Penning synchronization state.

        Args:
            state: Whether to enable Penning sync.
        """
        await self._write_register(_REG_PENNING_SYNC, int(state))

    async def set_atmosphere(self) -> None:
        """Set the atmosphere adjustment to 1000 mbar."""
        await self.set_pressure(1000.0)

    async def set_zero(self) -> None:
        """Set the zero adjustment to 0 mbar."""
        await self.set_pressure(1e-3)
