"""
Tests for the scietex.hal.vacuum_gauge.Thyracont.rs485.v2.decoder module.

This module tests the ThyracontDecodePDU class, ensuring correct initialization, PDU class lookup,
and decoding of Thyracont RS485 V2 frames into ThyracontRequest instances.
"""

import pytest

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.decoder import ThyracontDecodePDU
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation_utils import ThyracontV2State
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.request import ThyracontRequest
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.decoder import ThyracontDecodePDU
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation_utils import ThyracontV2State
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.request import ThyracontRequest


# Tests for initialization
def test_decoder_init_default():
    """Test default initialization of ThyracontDecodePDU."""
    decoder = ThyracontDecodePDU()
    assert decoder.pdu_table == {}
    assert decoder.pdu_sub_table == {}
    assert decoder.store is None
    assert decoder.state is None


def test_decoder_init_with_state():
    """Test initialization with an emulated device state."""
    state = ThyracontV2State()
    decoder = ThyracontDecodePDU(is_server=True, state=state)
    assert decoder.state is state


# Tests for lookupPduClass
def test_lookup_pdu_class_empty():
    """Test PDU class lookup with an empty lookup table."""
    decoder = ThyracontDecodePDU()
    assert decoder.lookupPduClass(b"0MV00") is None


def test_lookup_pdu_class_registered():
    """Test PDU class lookup with a registered ThyracontRequest."""
    decoder = ThyracontDecodePDU()
    decoder.pdu_table[0] = (ThyracontRequest, ThyracontRequest)
    assert decoder.lookupPduClass(b"0MV00") == ThyracontRequest


# Tests for decode
def test_decode_valid_read_frame():
    """Test decoding a valid READ frame with no offset on the access code."""
    decoder = ThyracontDecodePDU(state=ThyracontV2State())
    decoder.pdu_table[0] = (ThyracontRequest, ThyracontRequest)
    pdu = decoder.decode(b"0MV00")

    assert isinstance(pdu, ThyracontRequest)
    assert pdu.command == "MV"
    assert pdu.data == ""
    assert pdu.function_code == 0  # AccessCode.READ
    assert pdu.rtu_frame_size == 0


def test_decode_valid_streaming_frame():
    """Test decoding a STREAMING response frame."""
    decoder = ThyracontDecodePDU(state=ThyracontV2State())
    decoder.pdu_table[0] = (ThyracontRequest, ThyracontRequest)
    pdu = decoder.decode(b"6MV071.000e3")

    assert isinstance(pdu, ThyracontRequest)
    assert pdu.command == "MV"
    assert pdu.data == "1.000e3"
    assert pdu.function_code == 6  # AccessCode.STREAMING
    assert pdu.rtu_frame_size == 7


def test_decode_empty_frame():
    """Test decoding an empty frame."""
    decoder = ThyracontDecodePDU()
    decoder.pdu_table[0] = (ThyracontRequest, ThyracontRequest)
    assert decoder.decode(b"") is None


def test_decode_no_lookup():
    """Test decoding when no PDU class is registered."""
    decoder = ThyracontDecodePDU()
    assert decoder.decode(b"0MV00") is None


def test_decode_unknown_access_code():
    """Test decoding a frame with an unsupported access code returns None."""
    decoder = ThyracontDecodePDU()
    decoder.pdu_table[0] = (ThyracontRequest, ThyracontRequest)
    assert decoder.decode(b"XMV00") is None  # "X" is not a valid AccessCode


# pylint: disable=protected-access
def test_decode_state_injected():
    """Test that the emulated state is injected into the decoded PDU."""
    state = ThyracontV2State()
    decoder = ThyracontDecodePDU(state=state)
    decoder.pdu_table[0] = (ThyracontRequest, ThyracontRequest)
    pdu = decoder.decode(b"0MV00")
    assert pdu._state is state


if __name__ == "__main__":
    pytest.main()
