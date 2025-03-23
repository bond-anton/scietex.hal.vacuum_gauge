"""
Thyracont RS485 Version 2 ASCII Framer Module.

This module implements a custom ASCII framer for Thyracont RS485 protocol V2,
extending the `pymodbus` `FramerAscii` class. It is designed to handle Thyracont-specific
Application Data Units (ADUs) without a traditional start byte, using a 3-byte device ID,
a custom checksum, and a carriage return (`\\r`) as the end delimiter. The framer supports
encoding and decoding of Modbus messages with a minimum frame size of 10 bytes, tailored for
Thyracont vacuum gauge RS485 V2 communication syntax.

Classes:
    ThyracontASCIIFramer: A custom ASCII framer for Thyracont RS485 protocol V2.
"""

from pymodbus.pdu import ModbusPDU
from ..framer import ThyracontRS485ASCIIFramer


class ThyracontASCIIFramer(ThyracontRS485ASCIIFramer):
    """
    Thyracont custom protocol ASCII framer.

    A custom ASCII framer for Thyracont RS485 protocol V2, extending `pymodbus.framer.FramerAscii`.
    Unlike the standard Modbus ASCII framer, it uses no start byte, a 3-digit device ID at the
    beginning of each frame, a custom single-byte checksum, and a carriage return (`\\r`) as the
    end delimiter. The minimum frame size is set to 10 bytes according to message format of V2
    protocol.
    """

    MIN_SIZE = 10

    def buildFrame(self, message: ModbusPDU) -> bytes:
        """Create a ready to send modbus packet.

        :param message: The populated request/response to send
        """
        frame = self.encode(message.encode(), message.dev_id, message.transaction_id)
        return frame
