"""
Thyracont RS485 Version 1 Decoder Module.

This module provides a custom Modbus Protocol Data Unit (PDU) decoder for Thyracont's RS485
protocol, extending `pymodbus.pdu.DecodePDU`. It is designed to decode Thyracont-specific frames,
which consist of a single-character command followed by a data payload, into `ThyracontRequest` PDU
instances. The decoder supports a simplified lookup mechanism tailored to Thyracont’s protocol,
where only one PDU type is expected.

Classes:
    ThyracontDecodePDU: A custom PDU decoder for Thyracont’s RS485 protocol, handling frame decoding
        into `ThyracontRequest` objects.
"""

from ..decoder import ThyracontRS485DecodePDU


class ThyracontDecodePDU(ThyracontRS485DecodePDU):
    """
    Thyracont custom RS485 V1 protocol decoder class.
    """
