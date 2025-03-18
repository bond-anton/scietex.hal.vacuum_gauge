"""
Erstevak RS485 Version 1 Decoder Module.

This module provides a custom Modbus Protocol Data Unit (PDU) decoder for Erstevak's RS485
protocol, extending `pymodbus.pdu.DecodePDU`. It is designed to decode Erstevak-specific frames,
which consist of a single-character command followed by a data payload, into `ErstevakRequest` PDU
instances. The decoder supports a simplified lookup mechanism tailored to Erstevak’s protocol,
where only one PDU type is expected.

Classes:
    ErstevakDecodePDU: A custom PDU decoder for Erstevak’s RS485 protocol, handling frame decoding
        into `ErstevakRequest` objects.
"""

from ..decoder import ErstevakRS485DecodePDU


class ErstevakDecodePDU(ErstevakRS485DecodePDU):
    """
    Erstevak custom RS485 V1 protocol decoder class.
    """
