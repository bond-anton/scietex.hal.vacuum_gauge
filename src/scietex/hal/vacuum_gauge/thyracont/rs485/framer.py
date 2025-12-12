"""
Thyracont RS485 ASCII Framer Module.

This module implements a custom ASCII framer for Thyracont's RS485 protocol,
extending the `pymodbus` `FramerAscii` class. It is designed to handle Thyracont-specific
Application Data Units (ADUs) without a traditional start byte, using a 3-byte device ID, a custom
checksum, and a carriage return (`\\r`) as the end delimiter. The framer supports encoding and
decoding of Modbus messages with a minimum frame size of 4 bytes, tailored for Thyracont vacuum
gauge communication over RS485.

Classes:
    ThyracontASCIIFramer: A custom ASCII framer for Thyracont's RS485 protocol, overriding
        `FramerAscii` methods for encoding, decoding, and processing incoming frames.
"""

from typing import Optional
from pymodbus.exceptions import ModbusIOException
from pymodbus.framer import FramerAscii
from pymodbus.pdu import ModbusPDU

from .checksum import calc_checksum, check_checksum


class ThyracontRS485ASCIIFramer(FramerAscii):
    """
    Thyracont custom protocol ASCII framer.

    A custom ASCII framer for Thyracont's RS485 protocol, extending `pymodbus.framer.FramerAscii`.
    Unlike the standard Modbus ASCII framer, it uses no start byte, a 3-digit device ID at the
    beginning of each frame, a custom single-byte checksum, and a carriage return (`\\r`) as the
    end delimiter. The minimum frame size is reduced to 4 bytes to accommodate Thyracont's compact
    message format.

    Attributes
    ----------
    START : bytes
        The start delimiter for the frame (empty for Thyracont protocol).
    END : bytes
        The end delimiter for the frame (`b"\\r"`).
    MIN_SIZE : int
        The minimum frame size required for decoding (4 bytes: 3 for device ID + 1 for checksum).

    Methods
    -------
    decode(data: bytes) -> tuple[int, int, int, bytes]
        Decodes an incoming frame into device ID, transaction ID, and message data.
    encode(data: bytes, device_id: int, _tid: int) -> bytes
        Encodes a message into an Thyracont ASCII frame with device ID and checksum.
    _processIncomingFrame(data: bytes) -> tuple[int, Optional[ModbusPDU]]
        Processes incoming data to extract and decode a complete frame.
    """

    START = b""  # no starting byte.
    END = b"\r"
    EMPTY = b""
    MIN_SIZE = 6  # Lower data min size to 4 bytes.

    def decode(self, data: bytes) -> tuple[int, int, int, bytes]:
        """
        Customized decode ADU function.

        Decodes a Thyracont RS485 ASCII frame from raw bytes into its components: the number of
        bytes used, the device ID, a placeholder transaction ID (always 0), and the message data.
        The frame format is `<3-digit-device-id><message><1-byte-checksum>\\r`.
        If the frame is incomplete or invalid (e.g., missing end byte or incorrect checksum),
        it returns an empty message.

        Parameters
        ----------
        data : bytes
            The raw byte stream containing one or more frames.

        Returns
        -------
        tuple[int, int, int, bytes]
            A tuple containing:
            - len_used (int): Number of bytes consumed from `data`.
            - dev_id (int): Device (slave) ID extracted from the first 3 bytes.
            - tid (int): Transaction ID (always 0, as not used in this protocol).
            - frame_data (bytes): The decoded message data, excluding device ID and checksum, or
              `self.EMPTY` if decoding fails.
        """
        len_used = 0
        len_data = len(data)
        while True:
            if len_data - len_used < self.MIN_SIZE:
                break
            data_buffer = data[len_used:]
            if (data_end := data_buffer.find(self.END)) == -1:
                break
            dev_id = int(data_buffer[0:3], 10)  # First 3 bytes for device (slave) id
            checksum = data_buffer[data_end - 1]
            msg = data_buffer[0 : data_end - 1]
            len_used += data_end + 1
            if not check_checksum(msg, checksum):
                break
            return len_used, dev_id, 0, msg[3:]
        return len_used, 0, 0, self.EMPTY

    def encode(self, payload: bytes, device_id: int, _tid: int) -> bytes:
        """
        Customized encode ADU function.

        Encodes a message into a Thyracont RS485 ASCII frame by prepending a 3-digit device ID,
        appending a calculated checksum, and framing it with the `START` (empty) and `END` (`\\r`)
        delimiters. The transaction ID (`_tid`) is ignored as it’s not part of this protocol.

        Parameters
        ----------
        payload : bytes
            The message data to encode (e.g., Modbus PDU).
        device_id : int
            The device (slave) ID to include in the frame, formatted as a 3-digit string.
        _tid : int
            The transaction ID (unused in this protocol, included for compatibility).

        Returns
        -------
        bytes
            The fully encoded frame, e.g., `b"001<message><checksum>\\r"`.
        """
        dev_id = f"{device_id:03d}".encode()  # encode device id into first 3 bytes.
        checksum = calc_checksum(dev_id + payload)
        frame = self.START + dev_id + payload + bytes([checksum]) + self.END
        return frame

    def handleFrame(
        self, data: bytes, exp_devid: int, exp_tid: int
    ) -> tuple[int, Optional[ModbusPDU]]:
        """
        Process new packet pattern.

        Processes incoming data to extract and decode a complete Thyracont ASCII frame. It uses the
        `decode` method to parse the frame and the inherited `decoder` to interpret the message
        data as a Modbus PDU. If decoding fails or the PDU is invalid, it raises a
        `ModbusIOException`.

        Parameters
        ----------
        data : bytes
            The raw byte stream containing one or more frames.
        exp_devid : int
            Device id (unused in this protocol, included for compatibility).
        exp_tid : int
            Transaction ID (unused in this protocol, included for compatibility).

        Returns
        -------
        tuple[int, Optional[ModbusPDU]]
            A tuple containing:
            - used_len (int): Number of bytes consumed from `data`.
            - res (Optional[ModbusPDU]): The decoded Modbus PDU with `dev_id` and `transaction_id`
              set, or None if no valid frame is found.

        Raises
        ------
        ModbusIOException
            If the decoded frame data cannot be interpreted as a valid Modbus PDU.
        """
        if not data:
            return 0, None
        used_len, dev_id, tid, frame_data = self.decode(data)
        if not frame_data:
            return used_len, None
        if (res := self.decoder.decode(frame_data)) is None:
            raise ModbusIOException("Unable to decode request")
        res.dev_id = dev_id
        res.transaction_id = tid
        return used_len, res
