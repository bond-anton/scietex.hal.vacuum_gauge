"""
Erstevak RS485 Version 2 Request Module.

This module defines a custom Modbus Protocol Data Unit (PDU) for Erstevak's RS485 protocol V2,
extending `pymodbus.pdu.ModbusPDU`. It encapsulates Erstevak-specific requests, which consist of a
single-byte access-code, two-character command, two bytes of data length followed by data bytes,
and integrates with a Modbus slave context via the `parse_command` utility.
The class handles encoding, decoding, and executing these requests, emulating the communication
behavior of an Erstevak vacuum gauge (e.g., MTM9D) over RS485.

Classes:
    ErstevakRequest: A custom Modbus PDU class for Erstevak RS485 requests, supporting command
        execution and response generation.
"""

from typing import Optional
from enum import Enum

from pymodbus.pdu import ModbusPDU
from pymodbus.datastore import ModbusSlaveContext

# from .emulation_utils import parse_command


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


class ErstevakRequest(ModbusPDU):
    """
    Erstevak custom protocol request.

    A custom Modbus PDU class for Erstevak's RS485 V2 protocol, designed to handle single-character
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
        slave=1,
        transaction=0,
    ) -> None:
        """
        Initialize an ErstevakRequest instance.

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
        slave : int, optional
            The device (slave) ID. Defaults to 1.
        transaction : int, optional
            The transaction ID. Defaults to 0.
        """
        super().__init__(dev_id=slave, transaction_id=transaction)
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
        self.rtu_frame_size = len(self.__data)

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
    async def update_datastore(self, context: ModbusSlaveContext) -> ModbusPDU:
        """
        Execute the request against a Modbus slave context and return a response PDU.

        Processes the request by calling `parse_command` with the command and data, then constructs
        a response `ErstevakRequest` instance with the resulting data. The response includes the
        original command, slave ID, and transaction ID, and stores the response bytes in the
        `registers` attribute as a list.

        Parameters
        ----------
        context : ModbusSlaveContext
            The Modbus slave context containing the holding register store to update or read from.

        Returns
        -------
        ModbusPDU
            An `ErstevakRequest` instance representing the response, with `registers` set to the
            list of response bytes.
        """
        # data: bytes = parse_command(context, self.command, self.data)
        data: bytes = self.data.encode()
        response = ErstevakRequest(
            AccessCode.from_int(self.function_code + 1),
            self.command,
            data,
            slave=self.dev_id,
            transaction=self.transaction_id,
        )
        response.registers = list(data)
        return response
