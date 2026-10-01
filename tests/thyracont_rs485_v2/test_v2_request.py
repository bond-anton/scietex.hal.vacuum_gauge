"""
Tests for the scietex.hal.vacuum_gauge.Thyracont.rs485.v2.request module.

This module tests the ThyracontRequest class, ensuring correct initialization, encoding, decoding,
and execution of Thyracont RS485 V2 requests against an emulated device state.
"""

import pytest

try:
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import AccessCode
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation_utils import ThyracontV2State
    from src.scietex.hal.vacuum_gauge.thyracont.rs485.v2.request import ThyracontRequest
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.data import AccessCode
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.emulation_utils import ThyracontV2State
    from scietex.hal.vacuum_gauge.thyracont.rs485.v2.request import ThyracontRequest


@pytest.fixture
def state():
    """Create an emulated device state."""
    return ThyracontV2State()


# Tests for initialization
# pylint: disable=protected-access
def test_request_init_default():
    """Test default initialization of ThyracontRequest."""
    request = ThyracontRequest()
    assert request.command == ""
    assert request.function_code == 0
    assert request.data == ""
    assert request.rtu_frame_size == 0
    assert request.dev_id == 1
    assert request.transaction_id == 0
    assert request._state is None


def test_request_init_with_access_code():
    """Test initialization with an access code."""
    request = ThyracontRequest(access_code=AccessCode.READ, command="MV")
    assert request.function_code == 0  # AccessCode.READ.value
    assert request.command == "MV"
    assert request.data == ""


def test_request_init_with_data():
    """Test initialization with command and data."""
    request = ThyracontRequest(
        access_code=AccessCode.READ, command="PM", data=b"1", dev_id=2, transaction_id=3
    )
    assert request.command == "PM"
    assert request.function_code == 0
    assert request.data == "1"
    assert request.rtu_frame_size == 1
    assert request.dev_id == 2
    assert request.transaction_id == 3


def test_request_init_command_truncated():
    """Test that the command is limited to its first two characters."""
    request = ThyracontRequest(access_code=AccessCode.READ, command="MVExtra")
    assert request.command == "MV"


# Tests for encode
def test_request_encode_read():
    """Test encoding a read request with no data."""
    request = ThyracontRequest(access_code=AccessCode.READ, command="MV")
    assert request.encode() == b"0MV00"


def test_request_encode_with_data():
    """Test encoding a request with data."""
    request = ThyracontRequest(access_code=AccessCode.READ, command="PM", data=b"1")
    assert request.encode() == b"0PM011"


# Tests for decode
def test_request_decode_read():
    """Test decoding a READ frame (access code 0, no offset)."""
    request = ThyracontRequest()
    request.decode(b"0MV00")
    assert request.function_code == 0
    assert request.command == "MV"
    assert request.data == ""
    assert request.rtu_frame_size == 0


def test_request_decode_streaming():
    """Test decoding a STREAMING response frame (access code 6)."""
    request = ThyracontRequest()
    request.decode(b"6MV071.000e3")
    assert request.function_code == 6  # AccessCode.STREAMING
    assert request.command == "MV"
    assert request.data == "1.000e3"
    assert request.rtu_frame_size == 7


def test_request_decode_error():
    """Test decoding an ERROR response frame (access code 7)."""
    request = ThyracontRequest()
    request.decode(b"7MV11SYNTAX")
    assert request.function_code == 7  # AccessCode.ERROR
    assert request.command == "MV"
    assert request.data == "SYNTAX"


# Tests for datastore_update
# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_datastore_update_read_pressure(state):
    """Test executing a pressure read request ('MV')."""
    state.pressure = 1000.0
    request = ThyracontRequest(
        access_code=AccessCode.READ, command="MV", dev_id=2, transaction_id=1, state=state
    )
    response = await request.datastore_update(None, 1)
    assert isinstance(response, ThyracontRequest)
    assert response.command == "MV"
    assert response.function_code == 6  # AccessCode.STREAMING
    assert response.data == "1.000e3"
    assert response.registers == list("1.000e3".encode())
    assert response.dev_id == 2
    assert response.transaction_id == 1


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_datastore_update_model(state):
    """Test executing a model query request ('TD')."""
    request = ThyracontRequest(
        access_code=AccessCode.READ, command="TD", dev_id=1, transaction_id=4, state=state
    )
    response = await request.datastore_update(None, 1)
    assert response.command == "TD"
    assert response.function_code == 6
    assert response.data == "MTM9D"
    assert response.registers == list("MTM9D".encode())


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_datastore_update_unsupported_command(state):
    """Test executing an unsupported command, which yields an ERROR response."""
    request = ThyracontRequest(
        access_code=AccessCode.READ, command="XX", dev_id=1, transaction_id=0, state=state
    )
    response = await request.datastore_update(None, 1)
    assert response.command == "XX"
    assert response.function_code == 7  # AccessCode.ERROR
    assert response.data == "Unsupported command: XX"


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_datastore_update_without_state():
    """Test that a request without state raises RuntimeError."""
    request = ThyracontRequest(access_code=AccessCode.READ, command="MV")
    with pytest.raises(RuntimeError):
        await request.datastore_update(None, 1)


if __name__ == "__main__":
    pytest.main()
