"""
Erstevak RS485 Version 1 ASCII Framer Module.

This module implements a custom ASCII framer for Erstevak RS485 protocol V1,
extending the `pymodbus` `FramerAscii` class. It is designed to handle Erstevak-specific
Application Data Units (ADUs) without a traditional start byte, using a 3-byte device ID,
a custom checksum, and a carriage return (`\\r`) as the end delimiter. The framer supports
encoding and decoding of Modbus messages with a minimum frame size of 6 bytes, tailored for
Erstevak vacuum gauge RS485 V1 communication syntax.

Classes:
    ErstevakASCIIFramer: A custom ASCII framer for Erstevak RS485 protocol V1.
"""

from ..framer import ErstevakRS485ASCIIFramer


class ErstevakASCIIFramer(ErstevakRS485ASCIIFramer):
    """
    Erstevak custom protocol ASCII framer.
    """
