"""
Thyracont RS485 Version 2 Gateway Translator.

This module implements :class:`ThyracontV2Translator`, a read-only
`GatewayTranslator` plugin for `scietex.hal.serial` 2.0.0 that exposes a subset
of a Thyracont RS485 V2 vacuum gauge (e.g. MTM9D) behind the `ModbusGateway`.

The Thyracont V2 protocol is command-oriented rather than register-oriented: a
request is an ASCII frame carrying a two-character command (and optional data),
and the response is an ASCII data string. The translator maps standard
read-holding-registers (FC03) requests onto the corresponding vendor command and
maps the ASCII response back into a two-register float32 pair.

Register map (0-based PDU addresses, read-only)
-----------------------------------------------
Every supported value is an IEEE-754 float32 encoded across two 16-bit registers
in big-endian word order (first register = high 16 bits). Reads must request
exactly two registers (``count == 2``).

+---------+-------------+-----------------------------------+
| Address | Vendor cmd  | Meaning                           |
+=========+=============+===================================+
| 0-1     | MV          | Pressure (mbar)                   |
+---------+-------------+-----------------------------------+
| 2-3     | OH          | Gauge operating hours             |
+---------+-------------+-----------------------------------+
| 4-5     | OH          | Cathode operating hours           |
+---------+-------------+-----------------------------------+
| 6-7     | PM data="1" | Pirani wear (%)                   |
+---------+-------------+-----------------------------------+
| 8-9     | PM data="1" | Hours since zero adjustment       |
+---------+-------------+-----------------------------------+

Coverage limit
--------------
This translator is read-only: only FC03 reads of the five register pairs above
are supported. Writes, the model/serial strings (``TD``), measurement ranges,
temperatures, relays, streaming, and multi-count reads are out of scope and
raise :class:`~scietex.hal.serial.gateway.GatewayError`. A gauge without a
cathode reports no cathode hours (``None``); reading addresses 4-5 then raises
``GatewayError`` rather than returning a fabricated value.

Float32 encoding
----------------
The value is packed to its IEEE-754 bit pattern with ``struct.pack(">f", ...)``
and split into two 16-bit registers with ``split_32bit`` in big-endian word
order. The fixed-point helpers ``float_to_unsigned32`` / ``float_from_unsigned32``
are deliberately NOT used: they scale by a decimal factor instead of producing
the IEEE-754 float32 bit pattern the register map requires.
"""

import struct
from typing import Optional

from pymodbus.pdu import ModbusPDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersRequest,
    ReadHoldingRegistersResponse,
)

from scietex.hal.serial.gateway import GatewayError
from scietex.hal.serial.utilities.numeric import ByteOrder, split_32bit

from .data import AccessCode, decode_float, decode_operating_hours, decode_wear_status
from .request import ThyracontRequest

# Every supported read spans two 16-bit registers (one float32 value).
_FLOAT32_REGISTERS = 2

# Vendor command (and optional data) for each supported gateway register address.
_COMMAND: dict[int, tuple[str, Optional[bytes]]] = {
    0: ("MV", None),  # Pressure.
    2: ("OH", None),  # Gauge operating hours.
    4: ("OH", None),  # Cathode operating hours.
    6: ("PM", b"1"),  # Pirani wear.
    8: ("PM", b"1"),  # Pirani hours since zero adjustment.
}


def _float32_to_registers(value: float) -> list[int]:
    """Encode a float as two big-endian 16-bit registers (IEEE-754 float32)."""
    raw = struct.pack(">f", value)
    word = struct.unpack(">I", raw)[0]
    high, low = split_32bit(word, ByteOrder.BIG_ENDIAN)
    return [high, low]


class ThyracontV2Translator:
    """
    Map standard Modbus FC03 reads to and from the Thyracont RS485 V2 protocol.

    The gateway serializes bus access, so at most one vendor request is in
    flight per instance: `to_vendor` records the pending register address and
    `to_standard` consumes it to build the matching standard response.
    """

    def __init__(self) -> None:
        self._pending_address: Optional[int] = None

    def to_vendor(self, request: ModbusPDU) -> ModbusPDU:
        """
        Translate a standard FC03 read into a Thyracont V2 vendor request.

        Args:
            request (ModbusPDU): The decoded standard Modbus request.

        Returns:
            ModbusPDU: The vendor request PDU (a `ThyracontRequest`).

        Raises:
            GatewayError: If the request is not an FC03 two-register read of a
                supported address.
        """
        if not isinstance(request, ReadHoldingRegistersRequest):
            raise GatewayError(
                f"Unsupported request type: {type(request).__name__}; only FC03 reads are supported"
            )
        if request.count != _FLOAT32_REGISTERS:
            raise GatewayError(
                f"Unsupported register count: {request.count}; expected {_FLOAT32_REGISTERS}"
            )
        if request.address not in _COMMAND:
            raise GatewayError(f"Unsupported register address: {request.address}")
        command, data = _COMMAND[request.address]
        self._pending_address = request.address
        return ThyracontRequest(access_code=AccessCode.READ, command=command, data=data)

    def to_standard(self, response: ModbusPDU) -> ModbusPDU:
        """
        Translate a Thyracont V2 vendor response into a standard FC03 response.

        Args:
            response (ModbusPDU): The decoded vendor response PDU.

        Returns:
            ModbusPDU: A `ReadHoldingRegistersResponse` carrying the decoded
                value as two float32 registers.

        Raises:
            GatewayError: If there is no pending request, the response is not a
                `ThyracontRequest`, the device reported an error, or the response
                data is empty/malformed.
        """
        if self._pending_address is None:
            raise GatewayError("to_standard called without a pending request")
        address = self._pending_address
        if not isinstance(response, ThyracontRequest):
            raise GatewayError(f"Unexpected vendor response type: {type(response).__name__}")
        if response.function_code == AccessCode.ERROR.value:
            raise GatewayError(f"Device reported an error: {response.data!r}")
        value = self._decode(address, response.data)
        return ReadHoldingRegistersResponse(registers=_float32_to_registers(value))

    def _decode(self, address: int, data: str) -> float:
        """Decode a vendor response string for the given address into a float."""
        value: Optional[float]
        if address in (0, 1):
            value = decode_float(data)
        elif address in (2, 3):
            value = self._decode_operating_hours(data, "gauge")
        elif address in (4, 5):
            value = self._decode_operating_hours(data, "cathode")
        elif address in (6, 7):
            value = self._decode_wear(data, "wear")
        elif address in (8, 9):
            value = self._decode_wear(data, "hours_since_zero_adjustment")
        else:
            raise GatewayError(f"Unsupported register address: {address}")
        if value is None:
            raise GatewayError(f"Malformed vendor response for address {address}: {data!r}")
        return value

    @staticmethod
    def _decode_operating_hours(data: str, field: str) -> Optional[float]:
        """Extract one field from an operating-hours response string."""
        decoded = decode_operating_hours(data)
        if decoded is None:
            return None
        return decoded.get(field)

    @staticmethod
    def _decode_wear(data: str, field: str) -> Optional[float]:
        """Extract one numeric field from a wear-status response string."""
        decoded = decode_wear_status(data)
        if decoded is None:
            return None
        raw = decoded.get(field)
        return raw if isinstance(raw, float) else None
