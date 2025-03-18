"""
Tests for the scietex.hal.vacuum_gauge.erstevak.rs485.v1.framer module.

This module tests the ErstevakASCIIFramer class and its helper functions, ensuring correct
checksum calculation, frame encoding, decoding, and incoming frame processing for the Erstevak
RS485 protocol.
"""

import pytest
from pymodbus.pdu import ModbusPDU

try:
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v1.request import ErstevakRequest
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v1.decoder import ErstevakDecodePDU
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.checksum import calc_checksum, check_checksum
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v1.framer import ErstevakASCIIFramer
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.erstevak.rs485.v1.request import ErstevakRequest
    from scietex.hal.vacuum_gauge.erstevak.rs485.v1.decoder import ErstevakDecodePDU
    from scietex.hal.vacuum_gauge.erstevak.rs485.checksum import calc_checksum, check_checksum
    from scietex.hal.vacuum_gauge.erstevak.rs485.v1.framer import ErstevakASCIIFramer


@pytest.fixture
def decoder():
    """Create an ErstevakDecodePDU instance."""
    dec = ErstevakDecodePDU(is_server=False)
    dec.register(ErstevakRequest)
    return dec


# Fixture for framer instance
# pylint: disable=redefined-outer-name
@pytest.fixture
def framer(decoder):
    """Create an ErstevakASCIIFramer instance."""
    return ErstevakASCIIFramer(decoder=decoder)


# Tests for helper functions
def testcalc_checksum():
    """Test checksum calculation."""
    msg = b"001T"  # Device ID "001" + data "T"
    checksum = calc_checksum(msg)
    assert checksum == sum([48, 48, 49, ord("T")]) % 64 + 64  # ASCII: 0=48, 1=49
    assert 64 <= checksum <= 127  # Within printable ASCII range


def testcheck_checksum_valid():
    """Test checksum verification with a valid checksum."""
    msg = b"001T"
    checksum = calc_checksum(msg)
    assert check_checksum(msg, checksum) is True


def testcheck_checksum_invalid():
    """Test checksum verification with an invalid checksum."""
    msg = b"001T"
    checksum = calc_checksum(msg) + 1  # Deliberately wrong
    assert check_checksum(msg, checksum) is False


# Tests for ErstevakASCIIFramer
# pylint: disable=redefined-outer-name
def test_framer_init(framer):
    """Test initialization of ErstevakASCIIFramer."""
    assert framer.START == b""
    assert framer.END == b"\r"
    assert framer.MIN_SIZE == 6
    assert isinstance(framer.decoder, ErstevakDecodePDU)


# pylint: disable=redefined-outer-name
def test_decode_complete_frame(decoder):
    """Test decoding a complete frame."""
    framer = ErstevakASCIIFramer(decoder)
    msg = b"001T"
    data = msg + bytes([calc_checksum(msg)]) + b"\r"
    used_len, dev_id, tid, frame_data = framer.decode(data)
    assert used_len == 6
    assert dev_id == 1
    assert tid == 0
    assert frame_data == b"T"


# pylint: disable=redefined-outer-name
def test_decode_incomplete_frame(decoder):
    """Test decoding an incomplete frame (no end delimiter)."""
    framer = ErstevakASCIIFramer(decoder)
    data = b"001T@"
    used_len, dev_id, tid, frame_data = framer.decode(data)
    assert used_len == 0
    assert dev_id == 0
    assert tid == 0
    assert frame_data == b""


# pylint: disable=redefined-outer-name
def test_decode_frame_too_short(decoder):
    """Test decoding a frame shorter than MIN_SIZE."""
    framer = ErstevakASCIIFramer(decoder)
    data = b"00\r"
    used_len, dev_id, tid, frame_data = framer.decode(data)
    assert used_len == 0
    assert dev_id == 0
    assert tid == 0
    assert frame_data == b""


# pylint: disable=redefined-outer-name
def test_decode_invalid_checksum(decoder):
    """Test decoding a frame with an invalid checksum."""
    framer = ErstevakASCIIFramer(decoder)
    data = b"001SA\r"  # Checksum 65 (A) is wrong;
    used_len, dev_id, tid, frame_data = framer.decode(data)
    assert used_len == 6
    assert dev_id == 0
    assert tid == 0
    assert frame_data == b""


# pylint: disable=redefined-outer-name
def test_decode_multiple_frames(decoder):
    """Test decoding multiple frames in one data chunk."""
    framer = ErstevakASCIIFramer(decoder)
    msg1 = b"001S"
    msg1 = msg1 + bytes([calc_checksum(msg1)]) + b"\r"
    msg2 = b"002M"
    msg2 = msg2 + bytes([calc_checksum(msg2)]) + b"\r"
    data = msg1 + msg2
    # First frame: "00103"
    used_len1, dev_id1, _, frame_data1 = framer.decode(data)
    assert used_len1 == 6
    assert dev_id1 == 1
    assert frame_data1 == b"S"
    # Second frame: "00204"
    used_len2, dev_id2, _, frame_data2 = framer.decode(data[used_len1:])
    assert used_len2 == 6
    assert dev_id2 == 2
    assert frame_data2 == b"M"


# pylint: disable=redefined-outer-name
def test_encode_frame(decoder):
    """Test encoding a frame."""
    framer = ErstevakASCIIFramer(decoder)
    data = b"S"
    device_id = 1
    frame = framer.encode(data, device_id, 0)
    expected_checksum = calc_checksum(b"001S")
    assert frame == b"001S" + bytes([expected_checksum]) + b"\r"
    assert check_checksum(b"001S", expected_checksum)


# pylint: disable=redefined-outer-name,protected-access
def test_encode_different_device_id(decoder):
    """Test encoding with a different device ID."""
    framer = ErstevakASCIIFramer(decoder)
    data = b"M"
    device_id = 123
    frame = framer.encode(data, device_id, 0)
    expected_checksum = calc_checksum(b"123M")
    assert frame == b"123M" + bytes([expected_checksum]) + b"\r"
    assert check_checksum(b"123M", expected_checksum)


# pylint: disable=redefined-outer-name,protected-access
def test_process_incoming_frame_valid(framer):
    """Test processing a valid incoming frame."""
    data = b"001T"
    data = data + bytes([calc_checksum(data)]) + b"\r"
    used_len, result = framer._processIncomingFrame(data)
    assert used_len == 6
    assert isinstance(result, ModbusPDU)
    assert result.dev_id == 1
    assert result.transaction_id == 0


# pylint: disable=redefined-outer-name,protected-access
def test_process_incoming_frame_invalid_checksum(framer):
    """Test processing a frame with an invalid PDU."""
    data = b"001XX@\r"
    used_len, result = framer._processIncomingFrame(data)
    assert used_len == 7
    assert result is None


# pylint: disable=redefined-outer-name,protected-access
def test_process_incoming_frame_no_data(framer):
    """Test processing with no data."""
    used_len, result = framer._processIncomingFrame(b"")
    assert used_len == 0
    assert result is None


if __name__ == "__main__":
    pytest.main()
