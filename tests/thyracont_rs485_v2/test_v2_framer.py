"""
Tests for the scietex.hal.vacuum_gauge.Thyracont.rs485.v2.framer module.

This module tests the ThyracontASCIIFramer class, ensuring correct frame encoding, decoding, and
incoming frame processing for the Thyracont RS485 V2 protocol.
"""

import pytest
from pymodbus.pdu import ModbusPDU

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.checksum import calc_checksum, check_checksum
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import AccessCode
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.decoder import ThyracontDecodePDU
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.framer import ThyracontASCIIFramer
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.request import ThyracontRequest
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.checksum import calc_checksum, check_checksum
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import AccessCode
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.decoder import ThyracontDecodePDU
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.framer import ThyracontASCIIFramer
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.request import ThyracontRequest


@pytest.fixture
def decoder():
    """Create an ThyracontDecodePDU instance."""
    dec = ThyracontDecodePDU(is_server=False)
    dec.register(ThyracontRequest)
    return dec


# pylint: disable=redefined-outer-name
@pytest.fixture
def framer(decoder):
    """Create an ThyracontASCIIFramer instance."""
    return ThyracontASCIIFramer(decoder=decoder)


# pylint: disable=redefined-outer-name
def test_framer_init(framer):
    """Test initialization of ThyracontASCIIFramer."""
    assert framer.START == b""
    assert framer.END == b"\r"
    assert framer.MIN_SIZE == 10
    assert isinstance(framer.decoder, ThyracontDecodePDU)


# pylint: disable=redefined-outer-name
def test_decode_complete_frame(decoder):
    """Test decoding a complete V2 frame."""
    framer = ThyracontASCIIFramer(decoder)
    msg = b"0010MV00"
    data = msg + bytes([calc_checksum(msg)]) + b"\r"
    used_len, dev_id, tid, frame_data = framer.decode(data)
    assert used_len == 10
    assert dev_id == 1
    assert tid == 0
    assert frame_data == b"0MV00"


# pylint: disable=redefined-outer-name
def test_decode_incomplete_frame(decoder):
    """Test decoding an incomplete frame (no end delimiter)."""
    framer = ThyracontASCIIFramer(decoder)
    data = b"0010MV00@"
    used_len, dev_id, tid, frame_data = framer.decode(data)
    assert used_len == 0
    assert dev_id == 0
    assert tid == 0
    assert frame_data == b""


# pylint: disable=redefined-outer-name
def test_decode_invalid_checksum(decoder):
    """Test decoding a frame with an invalid checksum."""
    framer = ThyracontASCIIFramer(decoder)
    msg = b"0010MV00"
    data = msg + b"A\r"  # 'A' (65) is a deliberately wrong checksum
    used_len, dev_id, tid, frame_data = framer.decode(data)
    assert used_len == 10
    assert dev_id == 0
    assert tid == 0
    assert frame_data == b""


# pylint: disable=redefined-outer-name
def test_encode_frame(decoder):
    """Test encoding a V2 frame."""
    framer = ThyracontASCIIFramer(decoder)
    payload = b"0MV00"
    frame = framer.encode(payload, 1, 0)
    expected_checksum = calc_checksum(b"0010MV00")
    assert frame == b"0010MV00" + bytes([expected_checksum]) + b"\r"
    assert check_checksum(b"0010MV00", expected_checksum)


# pylint: disable=redefined-outer-name
def test_build_frame_from_request(decoder):
    """Test building a frame from a ThyracontRequest PDU."""
    framer = ThyracontASCIIFramer(decoder)
    request = ThyracontRequest(access_code=AccessCode.READ, command="MV", dev_id=1)
    frame = framer.buildFrame(request)
    assert frame == framer.encode(b"0MV00", 1, 0)


# pylint: disable=redefined-outer-name
def test_process_incoming_frame_valid(framer):
    """Test processing a valid incoming frame."""
    msg = b"0010MV00"
    data = msg + bytes([calc_checksum(msg)]) + b"\r"
    used_len, result = framer.handleFrame(data, 0, 0)
    assert used_len == 10
    assert isinstance(result, ModbusPDU)
    assert result.dev_id == 1
    assert result.transaction_id == 0


# pylint: disable=redefined-outer-name
def test_process_incoming_frame_no_data(framer):
    """Test processing with no data."""
    used_len, result = framer.handleFrame(b"", 0, 0)
    assert used_len == 0
    assert result is None


if __name__ == "__main__":
    pytest.main()
