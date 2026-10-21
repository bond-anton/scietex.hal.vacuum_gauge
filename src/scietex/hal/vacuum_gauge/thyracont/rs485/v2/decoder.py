"""
Thyracont RS485 Version 2 Decoder Module.

This module provides a custom Modbus Protocol Data Unit (PDU) decoder for Thyracont's RS485
protocol, extending `pymodbus.pdu.DecodePDU`. It is designed to decode Thyracont-specific frames,
which consist of a single-character command followed by a data payload, into `ThyracontRequest` PDU
instances. The decoder supports a simplified lookup mechanism tailored to Thyracont’s protocol,
where only one PDU type is expected.

Classes:
    ThyracontDecodePDU: A custom PDU decoder for Thyracont’s RS485 protocol, handling frame decoding
        into `ThyracontRequest` objects.
"""

from pymodbus import ModbusException
from pymodbus.pdu import ModbusPDU

from ..decoder import ThyracontRS485DecodePDU
from .data import AccessCode


class ThyracontDecodePDU(ThyracontRS485DecodePDU):
    """
    Thyracont custom RS485 V2 protocol decoder class.
    """

    def decode(self, frame: bytes) -> ModbusPDU | None:
        """
        Decode a Thyracont RS485 V2 frame into an `ThyracontRequest` instance.

        Parses the frame by extracting the first byte as an Access Code, following two bytes as
        command string, and the remaining bytes as data length and data bytes.
        Creates an `ThyracontRequest` instance with the command and data, then decodes the data
        portion into the instance’s `data` attribute. The frame’s bytes (excluding the command)
        are also stored in the `registers` attribute as a list. Returns None if decoding fails
        due to an empty frame or exceptions.

        Parameters
        ----------
        frame : bytes
            The raw frame to decode, expected to be in the format
            `<access_code 1-byte><command 2-bytes><data_len><data>` (e.g., b"0MV06123456").

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
            access_code: AccessCode = AccessCode.from_int(int(chr(frame[0])))
            command: str = frame[1:3].decode()
            pdu_class = self.lookupPduClass(frame)
            if pdu_class is None:
                return None
            pdu = pdu_class(
                access_code=access_code,  # ty: ignore[unknown-argument]
                command=command,  # ty: ignore[unknown-argument]
                data=frame,  # ty: ignore[unknown-argument]
                state=self.state,  # ty: ignore[unknown-argument]
            )
            pdu.decode(frame)
            pdu.registers = list(frame)[3:]
            return pdu
        except (ModbusException, ValueError, IndexError):
            return None
