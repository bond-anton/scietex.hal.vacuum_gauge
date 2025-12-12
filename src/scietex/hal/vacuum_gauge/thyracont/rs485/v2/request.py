"""
Thyracont RS485 Version 2 Request Module.

This module defines a custom Modbus Protocol Data Unit (PDU) for Thyracont's RS485 protocol V2,
extending `pymodbus.pdu.ModbusPDU`. It encapsulates Thyracont-specific requests, which consist of a
single-byte access-code, two-character command, two bytes of data length followed by data bytes,
and integrates with a Modbus slave context via the `parse_command` utility.
The class handles encoding, decoding, and executing these requests, emulating the communication
behavior of a Thyracont vacuum gauge (e.g., MTM9D) over RS485.

Classes:
    ThyracontRequest: A custom Modbus PDU class for Thyracont RS485 requests, supporting command
        execution and response generation.
"""

from typing import Optional

from pymodbus.pdu import ModbusPDU
from pymodbus.datastore import ModbusDeviceContext

from .data import AccessCode

# from .emulation_utils import parse_command


class ThyracontRequest(ModbusPDU):
    """
    Thyracont custom protocol request.

    A custom Modbus PDU class for Thyracont's RS485 V2 protocol, designed to handle single-character
    commands (e.g., "M", "s") and associated data payloads (up to 6 bytes). It extends `ModbusPDU`
    to support encoding, decoding, and asynchronous execution of requests against a Modbus slave
    context, using `parse_command` from `emulation_utils` to process the request and generate a
    response.

    Attributes
    ----------
    function_code : int
        The function code, derived from the first byte of the command (default 0 if no command).
    rtu_frame_size : int
        The size of the data payload in bytes (up to 6).
    command : str
        The single-character command (e.g., "T", "M"), extracted from the input `command`.
    data : str
        The data payload as a string, decoded from up to 6 bytes of input `data`.
    dev_id : int
        The device (slave) ID, inherited from `ModbusPDU`.
    transaction_id : int
        The transaction ID, inherited from `ModbusPDU`.
    registers : list
        A list of response bytes, set after execution (not used in request encoding).

    Methods
    -------
    __init__(command: Optional[str] = None, data: Optional[bytes] = None, slave=1, transaction=0)
        -> None
        Initializes the request with command, data, slave ID, and transaction ID.
    encode() -> bytes
        Encodes the request data into bytes.
    decode(data: bytes) -> None
        Decodes a byte string into the request’s data attribute.
    update_datastore(context: ModbusSlaveContext) -> ModbusPDU
        Executes the request against a Modbus slave context and returns a response PDU.
    """

    function_code = 0
    rtu_frame_size = 0

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        access_code: Optional[AccessCode] = None,
        command: Optional[str] = None,
        data: Optional[bytes] = None,
        dev_id=1,
        transaction_id=0,
    ) -> None:
        """
        Initialize an ThyracontRequest instance.

        Sets up the request with a command, data payload, slave ID, and transaction ID. The command
        is limited to its first character, and the data is decoded from up to 6 bytes into a string.
        The `function_code` is derived from the command’s first byte.

        Parameters
        ----------
        command : Optional[str], optional
            The command string (e.g., "T", "M"); only the first character is used. Defaults to None,
            resulting in an empty command ("").
        data : Optional[bytes], optional
            The data payload in bytes (e.g., b"123456"); limited to 6 bytes and decoded to a string.
            Defaults to None, resulting in an empty data string ("").
        dev_id : int, optional
            The device (slave) ID. Defaults to 1.
        transaction_id : int, optional
            The transaction ID. Defaults to 0.
        """
        super().__init__(dev_id=dev_id, transaction_id=transaction_id)
        if access_code is not None:
            self.function_code = access_code.value
        self.command: str = ""
        if command is not None and len(command) > 1:
            self.command = command[:2]
        self.__data: str = ""
        self.rtu_frame_size = 0
        if data is not None:
            self.data = data.decode()

    @property
    def data(self) -> str:
        """Data property."""
        return self.__data

    @data.setter
    def data(self, new_data: str) -> None:
        self.__data = new_data
        try:
            self.rtu_frame_size = len(self.__data)
        except TypeError:
            self.rtu_frame_size = 0

    def encode(self) -> bytes:
        """
        Encode the request data into bytes.

        Converts the `data` attribute (a string) into a byte string for transmission. The command
        is not included in the encoded output, as it’s handled separately by the framer.

        Returns
        -------
        bytes
            The encoded data payload (e.g., b"123456").
        """
        payload: bytes = f"{self.function_code:1d}".encode() + self.command.encode()
        payload += f"{len(self.data):02d}".encode() + self.data.encode()
        return payload

    def decode(self, data: bytes) -> None:
        """
        Decode a byte string into the request’s data attribute.

        Updates the `data` attribute by decoding the input bytes into a string. The command is not
        modified, as it’s assumed to be set during initialization or handled by the framer.

        Parameters
        ----------
        data : bytes
            The byte string to decode (e.g., b"123456").
        """
        self.function_code = int(data[0:1], 10)
        if self.function_code not in (6, 7):
            self.function_code -= 1
        self.command = data[1:3].decode()
        self.rtu_frame_size = int(data[3:5], 10)
        self.data = data[5 : 5 + self.rtu_frame_size].decode()

    # pylint: disable=duplicate-code
    async def update_datastore(self, context: ModbusDeviceContext) -> ModbusPDU:
        """
        Execute the request against a Modbus slave context and return a response PDU.

        Processes the request by calling `parse_command` with the command and data, then constructs
        a response `ThyracontRequest` instance with the resulting data. The response includes the
        original command, slave ID, and transaction ID, and stores the response bytes in the
        `registers` attribute as a list.

        Parameters
        ----------
        context : ModbusSlaveContext
            The Modbus slave context containing the holding register store to update or read from.

        Returns
        -------
        ModbusPDU
            An `ThyracontRequest` instance representing the response, with `registers` set to the
            list of response bytes.
        """
        # data: bytes = parse_command(context, self.command, self.data)
        data: bytes = self.data.encode()
        response = ThyracontRequest(
            AccessCode.from_int(self.function_code + 1),
            self.command,
            data,
            dev_id=self.dev_id,
            transaction_id=self.transaction_id,
        )
        response.registers = list(data)
        return response
