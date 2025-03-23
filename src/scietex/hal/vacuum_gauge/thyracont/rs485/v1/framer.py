"""
Thyracont RS485 Version 1 ASCII Framer Module.

This module implements a custom ASCII framer for Thyracont RS485 protocol V1,
extending the `pymodbus` `FramerAscii` class. It is designed to handle Thyracont-specific
Application Data Units (ADUs) without a traditional start byte, using a 3-byte device ID,
a custom checksum, and a carriage return (`\\r`) as the end delimiter. The framer supports
encoding and decoding of Modbus messages with a minimum frame size of 6 bytes, tailored for
Thyracont vacuum gauge RS485 V1 communication syntax.

Classes:
    ThyracontASCIIFramer: A custom ASCII framer for Thyracont RS485 protocol V1.
"""

from ..framer import ThyracontRS485ASCIIFramer


class ThyracontASCIIFramer(ThyracontRS485ASCIIFramer):
    """
    Thyracont custom protocol ASCII framer.
    """
