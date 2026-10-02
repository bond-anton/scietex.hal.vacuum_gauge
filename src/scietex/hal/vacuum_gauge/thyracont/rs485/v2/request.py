"""
Thyracont RS485 Version 2 Request Module.

This module defines a custom Modbus Protocol Data Unit (PDU) for Thyracont's RS485 protocol V2,
extending `pymodbus.pdu.ModbusPDU`. It encapsulates Thyracont-specific requests, which consist of a
single-byte access-code, two-character command, two bytes of data length followed by data bytes,
and integrates with an emulated device state via the `parse_command` utility.
The class handles encoding, decoding, and executing these requests, emulating the communication
behavior of a Thyracont vacuum gauge (e.g., MTM9D) over RS485.

Classes:
    ThyracontRequest: A custom Modbus PDU class for Thyracont RS485 requests, supporting command
        execution and response generation.
"""

from typing import Optional

from pymodbus.pdu import ModbusPDU

from .data import AccessCode
from .emulation_utils import ThyracontV2State, parse_command


class ThyracontRequest(ModbusPDU):
    """
    Thyracont custom protocol request.

    A custom Modbus PDU class for Thyracont's RS485 V2 protocol, designed to handle two-character
    commands (e.g., "MV", "OH") and associated data payloads. It extends `ModbusPDU` to support
    encoding, decoding, and asynchronous execution of requests against an emulated device state,
    using `parse_command` from `emulation_utils` to process the request and generate a response.

    Attributes
    ----------
    function_code : int
        The access code (e.g., `AccessCode.READ.value`), derived from the first byte of the frame.
    rtu_frame_size : int
        The size of the data payload in bytes.
    command : str
        The two-character command (e.g., "MV", "OH"), extracted from the input `command`.
    data : str
        The data payload as a string, decoded from the input `data`.
    dev_id : int
        The device (slave) ID, inherited from `ModbusPDU`.
    transaction_id : int
        The transaction ID, inherited from `ModbusPDU`.
    registers : list
        A list of response bytes, set after execution (not used in request encoding).
    _state : Optional[ThyracontV2State]
        The emulated device state the request operates on (None for client-side requests).

    Methods
    -------
    __init__(access_code=None, command=None, data=None, dev_id=1, transaction_id=0, state=None)
        -> None
        Initializes the request with access code, command, data, IDs, and emulated state.
    encode() -> bytes
        Encodes the request into bytes.
    decode(data: bytes) -> None
        Decodes a byte string into the request's attributes.
    datastore_update(context, device_id) -> ModbusPDU
        Executes the request against the emulated state and returns a response PDU.
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
        state: Optional[ThyracontV2State] = None,
    ) -> None:
        """
        Initialize an ThyracontRequest instance.

        Sets up the request with an access code, command, data payload, slave ID, transaction ID,
        and emulated device state. The command is limited to its first two characters, and the data
        is decoded from bytes into a string. The `function_code` is set from the access code.

        Parameters
        ----------
        access_code : Optional[AccessCode], optional
            The access code (e.g., `AccessCode.READ`). Defaults to None, leaving `function_code` 0.
        command : Optional[str], optional
            The command string (e.g., "MV", "OH"); only the first two characters are used.
            Defaults to None, resulting in an empty command ("").
        data : Optional[bytes], optional
            The data payload in bytes, decoded to a string. Defaults to None, resulting in an empty
            data string ("").
        dev_id : int, optional
            The device (slave) ID. Defaults to 1.
        transaction_id : int, optional
            The transaction ID. Defaults to 0.
        state : Optional[ThyracontV2State], optional
            The emulated device state the request operates on. Defaults to None.
        """
        super().__init__(dev_id=dev_id, transaction_id=transaction_id)
        if access_code is not None:
            self.function_code = access_code.value
        self._state: Optional[ThyracontV2State] = state
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

        Builds the V2 payload `<access code><command><data length><data>` from the access code
        (`function_code`), command, and data attributes.

        Returns
        -------
        bytes
            The encoded payload (e.g., b"0MV00").
        """
        payload: bytes = f"{self.function_code:1d}".encode() + self.command.encode()
        payload += f"{len(self.data):02d}".encode() + self.data.encode()
        return payload

    def decode(self, data: bytes) -> None:
        """
        Decode a byte string into the request's attributes.

        Parses the frame in the format `<access code 1-byte><command 2-bytes><data length
        2-bytes><data>` and updates `function_code`, `command`, `rtu_frame_size`, and `data`.
        The access code is mapped directly to its integer value with no offset.

        Parameters
        ----------
        data : bytes
            The byte string to decode (e.g., b"0MV00").
        """
        self.function_code = int(data[0:1], 10)
        self.command = data[1:3].decode()
        self.rtu_frame_size = int(data[3:5], 10)
        self.data = data[5 : 5 + self.rtu_frame_size].decode()

    # pylint: disable=duplicate-code
    async def datastore_update(self, context, device_id) -> ModbusPDU:
        """
        Execute the request against the emulated state and return a response PDU.

        Processes the request by calling `parse_command` with the command and data, then constructs
        a response `ThyracontRequest` instance. On success the response access code is the
        transmitter's success code for the request's access code (read -> 1, write -> 3,
        factory default -> 5, binary -> 9); on a parse error it uses `AccessCode.ERROR` with the
        error string as data. The response bytes are stored in the `registers` attribute as a list.

        Parameters
        ----------
        context : object
            The server context (ignored; state lives in `self._state`).
        device_id : int
            The device address (ignored; state lives in `self._state`).

        Returns
        -------
        ModbusPDU
            An `ThyracontRequest` instance representing the response, with `registers` set to the
            list of response bytes.

        Raises
        ------
        RuntimeError
            If the request was constructed without an emulated state (client-side requests).
        """
        _ = context, device_id  # State lives in self._state, not the pymodbus datastore.
        state = self._state
        if state is None:
            raise RuntimeError("ThyracontRequest has no state; datastore_update requires state=")
        try:
            data: str = parse_command(state, self.command, self.data)
            access_code: AccessCode = AccessCode.response_for(self.function_code)
        except ValueError as exc:
            data = str(exc)
            access_code = AccessCode.ERROR
        response = ThyracontRequest(
            access_code,
            self.command,
            data.encode(),
            dev_id=self.dev_id,
            transaction_id=self.transaction_id,
            state=state,
        )
        response.registers = list(data.encode())
        return response
