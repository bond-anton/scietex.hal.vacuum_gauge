"""
Thyracont RS485 Version 1 Gateway Translator.

This module implements :class:`ThyracontV1Translator`, a `GatewayTranslator`
plugin for `scietex.hal.serial` 2.0.0 that exposes a Thyracont RS485 V1 vacuum
gauge (e.g. VSP/MTM9D) behind the `ModbusGateway`.

The Thyracont V1 protocol is command-oriented rather than register-oriented: a
request is an ASCII frame carrying a single-character command and up to six
bytes of data, and the response is a six-digit decimal string (the vendor
stores every value as a raw integer and formats it with ``f"{value:06d}"``).
The translator maps standard read-holding-registers (FC03) and register-write
(FC06/FC16) requests onto the corresponding vendor command and maps the ASCII
response back into standard Modbus registers. Register values are passed
through as raw integers: a 32-bit value spans two 16-bit registers (little-
endian word order) and round-trips through the six-digit decimal string, while
a 16-bit value occupies a single register.

Register map (0-based PDU addresses)
------------------------------------

+---------+---------------------+----------------------------------------+
| Address | Read (FC03)         | Write (FC06/FC16)                      |
+=========+=====================+========================================+
| 0-1     | Pressure <- ``M``   | Pressure <- ``m`` + 6-digit (32-bit)   |
+---------+---------------------+----------------------------------------+
| 2-3     | SP1 <- ``S`` + 1    | (read-only)                            |
+---------+---------------------+----------------------------------------+
| 4-5     | SP2 <- ``S`` + 2    | (read-only)                            |
+---------+---------------------+----------------------------------------+
| 6       | CAL1 <- ``C`` + 1   | (read-only)                            |
+---------+---------------------+----------------------------------------+
| 7       | CAL2 <- ``C`` + 2   | (read-only)                            |
+---------+---------------------+----------------------------------------+
| 8       | Penning <- ``I``    | Penning state <- ``i`` + data          |
+---------+---------------------+----------------------------------------+
| 9       | Penning <- ``W``    | Penning sync <- ``w`` + data           |
+---------+---------------------+----------------------------------------+
| 10      | (write-only)        | SP select: write 1 or 2 -> ``s`` + 1/2 |
+---------+---------------------+----------------------------------------+
| 11      | (write-only)        | SP value: write 32-bit -> ``s`` + 6dig |
+---------+---------------------+----------------------------------------+
| 12      | (write-only)        | CAL select: write 1 or 2 -> ``c`` + 1/2|
+---------+---------------------+----------------------------------------+
| 13      | (write-only)        | CAL value: write 32-bit -> ``c`` + 6dig|
+---------+---------------------+----------------------------------------+

Coverage limits
---------------
The model string (``T`` command, e.g. "MTM09D") is not register-mappable and is
out of scope. The vendor protocol's setpoint and calibration writes are a
two-step select-then-write exchange, but the gateway is strictly one-request/
one-response. The two steps are therefore exposed as two *separate* registers
(10/11 for setpoints, 12/13 for calibration): the client issues two consecutive
writes, each of which maps to one vendor round-trip.

Stateful-select caveat
----------------------
The vendor select state is stateful across requests. Writing the value register
(11 or 13) without first writing the matching select register (10 or 12) writes
to whatever setpoint/calibration was last selected, or silently does nothing if
none has been selected since power-on. Always write the select register before
the value register.
"""

from dataclasses import dataclass
from typing import Optional

from pymodbus.pdu import ModbusPDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersRequest,
    ReadHoldingRegistersResponse,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)

from scietex.hal.serial.gateway import GatewayError
from scietex.hal.serial.utilities.numeric import combine_32bit, split_32bit

from .request import ThyracontRequest

# Standard Modbus function codes handled by this translator.
_FC_READ_HOLDING = ReadHoldingRegistersRequest.function_code  # 3
_FC_WRITE_SINGLE = WriteSingleRegisterRequest.function_code  # 6
_FC_WRITE_MULTIPLE = WriteMultipleRegistersRequest.function_code  # 16

# Vendor command (and optional data) and register count for each readable address.
_READ_COMMAND: dict[int, tuple[str, Optional[bytes], int]] = {
    0: ("M", None, 2),  # Pressure (32-bit).
    2: ("S", b"1", 2),  # Setpoint 1 (32-bit).
    4: ("S", b"2", 2),  # Setpoint 2 (32-bit).
    6: ("C", b"1", 1),  # Calibration 1 (16-bit).
    7: ("C", b"2", 1),  # Calibration 2 (16-bit).
    8: ("I", None, 1),  # Penning state (16-bit).
    9: ("W", None, 1),  # Penning sync (16-bit).
}

# Vendor command and value width (bits) for each writable address.
_WRITE_COMMAND: dict[int, tuple[str, int]] = {
    0: ("m", 32),  # Pressure.
    8: ("i", 16),  # Penning state.
    9: ("w", 16),  # Penning sync.
    10: ("s", 16),  # Setpoint select (1 or 2).
    11: ("s", 32),  # Setpoint value.
    12: ("c", 16),  # Calibration select (1 or 2).
    13: ("c", 32),  # Calibration value.
}

# Writable addresses whose 16-bit value is a select index and must be 1 or 2.
_SELECT_ADDRESSES = (10, 12)


@dataclass
class _PendingRequest:
    """
    State of the standard request being translated, recorded by `to_vendor` and
    consumed by `to_standard` to build the matching standard response.

    Attributes:
        function_code (int): The standard Modbus function code (3, 6 or 16).
        address (int): The starting register address.
        count (int): The number of registers (1 or 2).
        values (list[int]): The written register values (empty for reads).
    """

    function_code: int
    address: int
    count: int
    values: list[int]


class ThyracontV1Translator:
    """
    Map standard Modbus requests to and from the Thyracont RS485 V1 protocol.

    The gateway serializes bus access, so at most one vendor request is in
    flight per instance: `to_vendor` records the pending standard request and
    `to_standard` consumes it to build the matching standard response.
    """

    def __init__(self) -> None:
        self._pending: Optional[_PendingRequest] = None

    def to_vendor(self, request: ModbusPDU) -> ModbusPDU:
        """
        Translate a standard Modbus request into a Thyracont V1 vendor request.

        Args:
            request (ModbusPDU): The decoded standard Modbus request.

        Returns:
            ModbusPDU: The vendor request PDU (a `ThyracontRequest`).

        Raises:
            GatewayError: If the request is not a supported FC03/FC06/FC16
                access of a supported address/count.
        """
        # ReadInputRegistersRequest (FC04) subclasses ReadHoldingRegistersRequest,
        # so the function code must be checked to reject it.
        if (
            isinstance(request, ReadHoldingRegistersRequest)
            and request.function_code == _FC_READ_HOLDING
        ):
            return self._read_to_vendor(request)
        if isinstance(request, (WriteSingleRegisterRequest, WriteMultipleRegistersRequest)):
            return self._write_to_vendor(request)
        raise GatewayError(
            f"Unsupported request type: {type(request).__name__}; "
            "only FC03, FC06 and FC16 are supported"
        )

    def to_standard(self, response: ModbusPDU) -> ModbusPDU:
        """
        Translate a Thyracont V1 vendor response into a standard Modbus response.

        Args:
            response (ModbusPDU): The decoded vendor response PDU.

        Returns:
            ModbusPDU: A `ReadHoldingRegistersResponse`,
                `WriteSingleRegisterResponse` or `WriteMultipleRegistersResponse`.

        Raises:
            GatewayError: If there is no pending request, the response is not a
                `ThyracontRequest`, or the response data is empty/malformed.
        """
        if self._pending is None:
            raise GatewayError("to_standard called without a pending request")
        if not isinstance(response, ThyracontRequest):
            raise GatewayError(f"Unexpected vendor response type: {type(response).__name__}")
        pending = self._pending
        if not response.data:
            raise GatewayError(f"Empty vendor response for address {pending.address}")
        if pending.function_code == _FC_READ_HOLDING:
            return self._read_response(pending, response)
        if pending.function_code == _FC_WRITE_SINGLE:
            return WriteSingleRegisterResponse(
                address=pending.address, registers=[pending.values[0]]
            )
        if pending.function_code == _FC_WRITE_MULTIPLE:
            return WriteMultipleRegistersResponse(address=pending.address, count=pending.count)
        raise GatewayError(f"Unsupported function code: {pending.function_code}")

    def _read_to_vendor(self, request: ReadHoldingRegistersRequest) -> ModbusPDU:
        """Translate an FC03 read into the matching vendor read command."""
        target = _READ_COMMAND.get(request.address)
        if target is None:
            raise GatewayError(f"Unsupported register address: {request.address}")
        command, data, count = target
        if request.count != count:
            raise GatewayError(f"Unsupported register count: {request.count}; expected {count}")
        self._pending = _PendingRequest(
            function_code=request.function_code,
            address=request.address,
            count=count,
            values=[],
        )
        return ThyracontRequest(command=command, data=data)

    def _write_to_vendor(self, request: ModbusPDU) -> ModbusPDU:
        """Translate an FC06/FC16 write into the matching vendor write command."""
        target = _WRITE_COMMAND.get(request.address)
        if target is None:
            raise GatewayError(f"Unsupported register address: {request.address}")
        command, bits = target
        registers = list(request.registers)
        if bits == 32:
            if len(registers) != 2:
                raise GatewayError(f"Unsupported register count: {len(registers)}; expected 2")
            data = f"{combine_32bit(registers[0], registers[1]):06d}".encode()
        else:
            if len(registers) != 1:
                raise GatewayError(f"Unsupported register count: {len(registers)}; expected 1")
            value = registers[0]
            if request.address in _SELECT_ADDRESSES and value not in (1, 2):
                raise GatewayError(
                    f"Select register {request.address} requires value 1 or 2, got {value}"
                )
            data = str(value).encode()
        self._pending = _PendingRequest(
            function_code=request.function_code,
            address=request.address,
            count=len(registers),
            values=registers,
        )
        return ThyracontRequest(command=command, data=data)

    @staticmethod
    def _read_response(pending: _PendingRequest, response: ThyracontRequest) -> ModbusPDU:
        """Decode a six-digit decimal vendor response into standard registers."""
        data = response.data
        try:
            value = int(data)
        except ValueError as exc:
            raise GatewayError(
                f"Malformed vendor response for address {pending.address}: {data!r}"
            ) from exc
        if pending.count == 2:
            low, high = split_32bit(value)
            registers = [low, high]
        else:
            registers = [value]
        return ReadHoldingRegistersResponse(address=pending.address, registers=registers)
