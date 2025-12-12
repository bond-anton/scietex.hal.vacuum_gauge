"""
Thyracont RS485 Decoder Module.

This module provides a custom Modbus Protocol Data Unit (PDU) decoder for Thyracont's RS485
protocol, extending `pymodbus.pdu.DecodePDU`. It is designed to decode Thyracont-specific frames,
which consist of a single-character command followed by a data payload, into `ThyracontRequest` PDU
instances. The decoder supports a simplified lookup mechanism tailored to Thyracont’s protocol,
where only one PDU type is expected.

Classes:
    ThyracontDecodePDU: A custom PDU decoder for Thyracont’s RS485 protocol, handling frame decoding
        into `ThyracontRequest` objects.
"""

from typing import Optional
from pymodbus import ModbusException
from pymodbus.pdu import ModbusPDU, DecodePDU


class ThyracontRS485DecodePDU(DecodePDU):
    """
    Thyracont custom protocol decoder class.

    A custom PDU decoder for Thyracont’s RS485 protocol, extending `pymodbus.pdu.DecodePDU`.
    It decodes incoming frames into `ThyracontRequest` instances based on a single-character
    command and a variable-length data payload. Unlike standard Modbus decoders, it assumes
    a single PDU type (keyed to function code 0) and does not use a complex function code lookup,
    reflecting the simplicity of Thyracont’s protocol.

    Attributes
    ----------
    pdu_table : dict[int, tuple[type[ModbusPDU], type[ModbusPDU]]]
        A dictionary mapping function codes to PDU classes (only 0 is used, initially empty).
    pdu_sub_table : dict[
            int, dict[int, tuple[type[ModbusPDU], type[ModbusPDU]]]]
        A nested dictionary for sub-function code lookups (unused in this implementation).
    is_server : bool
        Indicates whether the decoder is used in server mode (inherited from `DecodePDU`).

    Methods
    -------
    __init__(is_server: bool = False) -> None
        Initializes the decoder with an empty lookup table.
    lookupPduClass(data: bytes) -> Optional[type[ModbusPDU]]
        Retrieves the PDU class for decoding (always `ThyracontRequest` or None).
    decode(frame: bytes) -> Optional[ModbusPDU]
        Decodes a Thyracont frame into an `ThyracontRequest` instance.
    """

    def __init__(self, is_server: bool = False) -> None:
        """
        Initialize an ThyracontDecodePDU instance.

        Sets up the decoder with an empty lookup table for PDU classes and an unused sub-function
        lookup dictionary. The `is_server` parameter is passed to the base class to configure
        server-side behavior, though it has no specific effect in this implementation.

        Parameters
        ----------
        is_server : bool, optional
            Whether the decoder is used in server mode. Defaults to False (client mode).
        """
        super().__init__(is_server)
        self.pdu_table: dict[int, tuple[type[ModbusPDU], type[ModbusPDU]]] = {}
        self.pdu_sub_table: dict[int, dict[int, tuple[type[ModbusPDU], type[ModbusPDU]]]] = {}

    def lookupPduClass(self, data: bytes) -> Optional[type[ModbusPDU]]:
        """
        Retrieve the PDU class for decoding based on the frame data.

        Returns the PDU class associated with function code 0 from the `lookup` dictionary,
        ignoring the input `data`. This reflects Thyracont’s protocol, which uses a single PDU type
        (`ThyracontRequest`) regardless of the command. If no class is registered (lookup is empty),
        returns None.

        Parameters
        ----------
        data : bytes
            The frame data (unused in this implementation).

        Returns
        -------
        Optional[type[ModbusPDU]]
            The PDU class (`ThyracontRequest`) if registered in `lookup[0]`, otherwise None.
        """
        _ = data  # Unused parameter, kept for compatibility
        function_code = 0
        return self.pdu_table.get(function_code, (None, None))[self.pdu_inx]

    def decode(self, frame: bytes) -> Optional[ModbusPDU]:
        """
        Decode a Thyracont frame into an `ThyracontRequest` instance.

        Parses the frame by extracting the first byte as a command character and the remaining
        bytes as data. Creates an `ThyracontRequest` instance with the command and data, then
        decodes the data portion into the instance’s `data` attribute. The frame’s bytes (excluding
        the command) are also stored in the `registers` attribute as a list. Returns None if
        decoding fails due to an empty frame or exceptions.

        Parameters
        ----------
        frame : bytes
            The raw frame to decode, expected to be in the format `<command><data>`
            (e.g., b"M123456").

        Returns
        -------
        Optional[ModbusPDU]
            An `ThyracontRequest` instance if decoding succeeds, otherwise None.

        Raises
        ------
        ModbusException
            Caught internally if PDU instantiation or decoding fails (returns None).
        ValueError
            Caught internally if decoding the command or data fails (returns None).
        IndexError
            Caught internally if the frame is too short (returns None).
        """
        if not frame:
            return None
        try:
            function_code = 0
            # pdu_type = self.lookupPduClass(frame)
            # if pdu_type is None:
            #     return None
            if not (pdu_class := self.pdu_table.get(function_code, (None, None))[self.pdu_inx]):
                return None
            command: str = frame[0:1].decode()
            pdu = pdu_class(command=command, data=frame[1:])  # type: ignore[call-arg]
            pdu.decode(frame[1:])
            pdu.registers = list(frame)[1:7]
            return pdu
        except (ModbusException, ValueError, IndexError):
            return None
