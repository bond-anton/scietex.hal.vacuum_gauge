"""
Erstevak RS485 Version 2 Decoder Module.

This module provides a custom Modbus Protocol Data Unit (PDU) decoder for Erstevak's RS485
protocol, extending `pymodbus.pdu.DecodePDU`. It is designed to decode Erstevak-specific frames,
which consist of a single-character command followed by a data payload, into `ErstevakRequest` PDU
instances. The decoder supports a simplified lookup mechanism tailored to Erstevak’s protocol,
where only one PDU type is expected.

Classes:
    ErstevakDecodePDU: A custom PDU decoder for Erstevak’s RS485 protocol, handling frame decoding
        into `ErstevakRequest` objects.
"""

from typing import Optional
from pymodbus import ModbusException
from pymodbus.pdu import ModbusPDU

from ..decoder import ErstevakRS485DecodePDU
from .request import AccessCode


class ErstevakDecodePDU(ErstevakRS485DecodePDU):
    """
    Erstevak custom RS485 V2 protocol decoder class.
    """

    def decode(self, frame: bytes) -> Optional[ModbusPDU]:
        """
        Decode an Erstevak RS485 V2 frame into an `ErstevakRequest` instance.

        Parses the frame by extracting the first byte as an Access Code, following two bytes as
        command string, and the remaining bytes as data length and data bytes.
        Creates an `ErstevakRequest` instance with the command and data, then decodes the data
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
            An `ErstevakRequest` instance if decoding succeeds, otherwise None.

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
            access_code: AccessCode = AccessCode.from_int(frame[0])
            command: str = frame[1:3].decode()

            pdu_type = self.lookupPduClass(frame)
            if pdu_type is None:
                return None
            pdu_class = pdu_type(
                access_code=access_code,  # type: ignore[call-arg]
                command=command,  # type: ignore[call-arg]
                data=frame[3:],  # type: ignore[call-arg]
            )
            pdu_class.decode(frame[3:])
            pdu_class.registers = list(frame)[3:]
            return pdu_class
        except (ModbusException, ValueError, IndexError):
            return None
