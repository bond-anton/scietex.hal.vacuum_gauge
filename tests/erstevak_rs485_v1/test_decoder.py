"""
Tests for the scietex.hal.vacuum_gauge.erstevak.rs485.v1.decoder module.

This module tests the ErstevakDecodePDU class, ensuring correct initialization, PDU class lookup,
and decoding of Erstevak RS485 frames into ErstevakRequest instances.
"""

import pytest

try:
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v1.decoder import ErstevakDecodePDU
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v1.request import ErstevakRequest
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.erstevak.rs485.v1.decoder import ErstevakDecodePDU
    from scietex.hal.vacuum_gauge.erstevak.rs485.v1.request import ErstevakRequest


# Tests for ErstevakDecodePDU initialization
def test_decoder_init_default():
    """Test default initialization of ErstevakDecodePDU."""
    decoder = ErstevakDecodePDU()
    assert decoder.lookup == {}
    assert decoder.sub_lookup == {}


def test_decoder_init_server_mode():
    """Test initialization in server mode."""
    decoder = ErstevakDecodePDU(is_server=True)
    assert decoder.lookup == {}
    assert decoder.sub_lookup == {}


# Tests for lookupPduClass
def test_lookup_pdu_class_empty():
    """Test PDU class lookup with an empty lookup table."""
    decoder = ErstevakDecodePDU()
    pdu_class = decoder.lookupPduClass(b"M123456")
    assert pdu_class is None


def test_lookup_pdu_class_registered():
    """Test PDU class lookup with a registered ErstevakRequest."""
    decoder = ErstevakDecodePDU()
    decoder.lookup[0] = ErstevakRequest
    pdu_class = decoder.lookupPduClass(b"Tdata")
    assert pdu_class == ErstevakRequest  # Always returns lookup[0], ignores data


# Tests for decode
def test_decode_valid_frame():
    """Test decoding a valid Erstevak frame."""
    decoder = ErstevakDecodePDU()
    decoder.lookup[0] = ErstevakRequest
    frame = b"M123456"  # Command "M", data "123456"
    pdu = decoder.decode(frame)

    assert isinstance(pdu, ErstevakRequest)
    assert pdu.command == "M"
    assert pdu.data == "123456"
    assert pdu.registers == [49, 50, 51, 52, 53, 54]  # ASCII bytes for "123456"
    assert pdu.function_code == ord("M")
    assert pdu.rtu_frame_size == 6


def test_decode_empty_frame():
    """Test decoding an empty frame."""
    decoder = ErstevakDecodePDU()
    decoder.lookup[0] = ErstevakRequest
    pdu = decoder.decode(b"")
    assert pdu is None


def test_decode_no_lookup():
    """Test decoding when no PDU class is registered."""
    decoder = ErstevakDecodePDU()  # Empty lookup
    pdu = decoder.decode(b"M123456")
    assert pdu is None


def test_decode_single_byte_frame():
    """Test decoding a frame with only a command."""
    decoder = ErstevakDecodePDU()
    decoder.lookup[0] = ErstevakRequest
    frame = b"T"
    pdu = decoder.decode(frame)

    assert isinstance(pdu, ErstevakRequest)
    assert pdu.command == "T"
    assert pdu.data == ""
    assert pdu.registers == []  # No data bytes
    assert pdu.function_code == ord("T")
    assert pdu.rtu_frame_size == 0


def test_decode_invalid_command():
    """Test decoding a frame with an invalid (non-UTF-8) command."""
    decoder = ErstevakDecodePDU()
    decoder.lookup[0] = ErstevakRequest
    frame = b"\xff123456"  # Invalid UTF-8 command byte
    pdu = decoder.decode(frame)
    assert pdu is None


def test_decode_long_data():
    """Test decoding a frame with data longer than typical (no truncation here)."""
    decoder = ErstevakDecodePDU()
    decoder.lookup[0] = ErstevakRequest
    frame = b"s123456789"  # Command "s", data "123456789"
    pdu = decoder.decode(frame)

    assert isinstance(pdu, ErstevakRequest)
    assert pdu.command == "s"
    assert pdu.data == "123456"
    assert pdu.registers == [49, 50, 51, 52, 53, 54]  # ASCII bytes
    assert pdu.rtu_frame_size == 6


# Edge case: decode with invalid data type in lookup
def test_decode_invalid_pdu_class():
    """Test decoding when lookup contains an invalid PDU class."""
    decoder = ErstevakDecodePDU()
    decoder.lookup[0] = int  # Not a valid ModbusPDU subclass
    frame = b"M123456"
    with pytest.raises(TypeError):  # Expect instantiation failure
        decoder.decode(frame)


# Edge case: decode with malformed frame
def test_decode_malformed_frame():
    """Test decoding a frame with invalid data after a valid command."""
    decoder = ErstevakDecodePDU()
    decoder.lookup[0] = ErstevakRequest
    frame = b"M\xff\xfe"  # Valid command, invalid UTF-8 data
    pdu = decoder.decode(frame)
    assert pdu is None  # decode() catches ValueError from data.decode()


if __name__ == "__main__":
    pytest.main()
