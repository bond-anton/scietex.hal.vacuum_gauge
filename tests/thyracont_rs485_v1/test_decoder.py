"""
Tests for the scietex.hal.vacuum_gauge.Thyracont.rs485.v1.decoder module.

This module tests the ThyracontDecodePDU class, ensuring correct initialization, PDU class lookup,
and decoding of Thyracont RS485 frames into ThyracontRequest instances.
"""

import pytest

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v1.decoder import ThyracontDecodePDU
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v1.request import ThyracontRequest
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v1.decoder import ThyracontDecodePDU
    from scietex.hal.vacuum_gauge.thyracont.rs485.v1.request import ThyracontRequest


# Tests for ThyracontDecodePDU initialization
def test_decoder_init_default():
    """Test default initialization of ThyracontDecodePDU."""
    decoder = ThyracontDecodePDU()
    assert decoder.lookup == {}
    assert decoder.sub_lookup == {}


def test_decoder_init_server_mode():
    """Test initialization in server mode."""
    decoder = ThyracontDecodePDU(is_server=True)
    assert decoder.lookup == {}
    assert decoder.sub_lookup == {}


# Tests for lookupPduClass
def test_lookup_pdu_class_empty():
    """Test PDU class lookup with an empty lookup table."""
    decoder = ThyracontDecodePDU()
    pdu_class = decoder.lookupPduClass(b"M123456")
    assert pdu_class is None


def test_lookup_pdu_class_registered():
    """Test PDU class lookup with a registered ThyracontRequest."""
    decoder = ThyracontDecodePDU()
    decoder.lookup[0] = ThyracontRequest
    pdu_class = decoder.lookupPduClass(b"Tdata")
    assert pdu_class == ThyracontRequest  # Always returns lookup[0], ignores data


# Tests for decode
def test_decode_valid_frame():
    """Test decoding a valid Thyracont frame."""
    decoder = ThyracontDecodePDU()
    decoder.lookup[0] = ThyracontRequest
    frame = b"M123456"  # Command "M", data "123456"
    pdu = decoder.decode(frame)

    assert isinstance(pdu, ThyracontRequest)
    assert pdu.command == "M"
    assert pdu.data == "123456"
    assert pdu.registers == [49, 50, 51, 52, 53, 54]  # ASCII bytes for "123456"
    assert pdu.function_code == ord("M")
    assert pdu.rtu_frame_size == 6


def test_decode_empty_frame():
    """Test decoding an empty frame."""
    decoder = ThyracontDecodePDU()
    decoder.lookup[0] = ThyracontRequest
    pdu = decoder.decode(b"")
    assert pdu is None


def test_decode_no_lookup():
    """Test decoding when no PDU class is registered."""
    decoder = ThyracontDecodePDU()  # Empty lookup
    pdu = decoder.decode(b"M123456")
    assert pdu is None


def test_decode_single_byte_frame():
    """Test decoding a frame with only a command."""
    decoder = ThyracontDecodePDU()
    decoder.lookup[0] = ThyracontRequest
    frame = b"T"
    pdu = decoder.decode(frame)

    assert isinstance(pdu, ThyracontRequest)
    assert pdu.command == "T"
    assert pdu.data == ""
    assert pdu.registers == []  # No data bytes
    assert pdu.function_code == ord("T")
    assert pdu.rtu_frame_size == 0


def test_decode_invalid_command():
    """Test decoding a frame with an invalid (non-UTF-8) command."""
    decoder = ThyracontDecodePDU()
    decoder.lookup[0] = ThyracontRequest
    frame = b"\xff123456"  # Invalid UTF-8 command byte
    pdu = decoder.decode(frame)
    assert pdu is None


def test_decode_long_data():
    """Test decoding a frame with data longer than typical (no truncation here)."""
    decoder = ThyracontDecodePDU()
    decoder.lookup[0] = ThyracontRequest
    frame = b"s123456789"  # Command "s", data "123456789"
    pdu = decoder.decode(frame)

    assert isinstance(pdu, ThyracontRequest)
    assert pdu.command == "s"
    assert pdu.data == "123456"
    assert pdu.registers == [49, 50, 51, 52, 53, 54]  # ASCII bytes
    assert pdu.rtu_frame_size == 6


# Edge case: decode with invalid data type in lookup
def test_decode_invalid_pdu_class():
    """Test decoding when lookup contains an invalid PDU class."""
    decoder = ThyracontDecodePDU()
    decoder.lookup[0] = int  # Not a valid ModbusPDU subclass
    frame = b"M123456"
    with pytest.raises(TypeError):  # Expect instantiation failure
        decoder.decode(frame)


# Edge case: decode with malformed frame
def test_decode_malformed_frame():
    """Test decoding a frame with invalid data after a valid command."""
    decoder = ThyracontDecodePDU()
    decoder.lookup[0] = ThyracontRequest
    frame = b"M\xff\xfe"  # Valid command, invalid UTF-8 data
    pdu = decoder.decode(frame)
    assert pdu is None  # decode() catches ValueError from data.decode()


if __name__ == "__main__":
    pytest.main()
