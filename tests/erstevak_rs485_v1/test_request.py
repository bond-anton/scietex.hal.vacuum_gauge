"""
Tests for the scietex.hal.vacuum_gauge.erstevak.rs485.v1.request module.

This module tests the ErstevakRequest class, ensuring correct initialization, encoding, decoding,
and execution of Erstevak-specific RS485 requests against a Modbus slave context.
"""

import pytest
from pymodbus.datastore import ModbusSlaveContext, ModbusSequentialDataBlock

try:
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v1.request import ErstevakRequest
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v1.emulation_utils import REG_P
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.erstevak.rs485.v1.request import ErstevakRequest
    from scietex.hal.vacuum_gauge.erstevak.rs485.v1.emulation_utils import REG_P


# Fixture for ModbusSlaveContext
@pytest.fixture
def context():
    """Create a ModbusSlaveContext with initialized holding registers."""
    data_block = ModbusSequentialDataBlock(0, [0] * 14)  # 14 registers for emulation_utils
    return ModbusSlaveContext(hr=data_block)


# Tests for ErstevakRequest initialization
def test_request_init_default():
    """Test default initialization of ErstevakRequest."""
    request = ErstevakRequest()
    assert request.command == ""
    assert request.function_code == 0
    assert request.data == ""
    assert request.rtu_frame_size == 0
    assert request.dev_id == 1
    assert request.transaction_id == 0


def test_request_init_with_command_and_data():
    """Test initialization with command and data."""
    request = ErstevakRequest(command="Mread", data=b"123456", slave=2, transaction=3)
    assert request.command == "M"  # Only first character
    assert request.function_code == ord("M")
    assert request.data == "123456"
    assert request.rtu_frame_size == 6
    assert request.dev_id == 2
    assert request.transaction_id == 3


def test_request_init_long_data():
    """Test initialization with data longer than 6 bytes (truncated)."""
    request = ErstevakRequest(data=b"123456789")
    assert request.data == "123456"  # Truncated to 6 bytes
    assert request.rtu_frame_size == 6


# Tests for encode
def test_request_encode():
    """Test encoding the request data."""
    request = ErstevakRequest(command="M", data=b"123456")
    encoded = request.encode()
    assert encoded == b"123456"
    assert request.command == "M"  # Command not included in encode


def test_request_encode_empty():
    """Test encoding with empty data."""
    request = ErstevakRequest(command="T")
    encoded = request.encode()
    assert encoded == b""


# Tests for decode
def test_request_decode():
    """Test decoding data into the request."""
    request = ErstevakRequest(command="s")
    request.decode(b"987620")
    assert request.data == "987620"
    assert request.rtu_frame_size == 6
    assert request.command == "s"  # Command unchanged


def test_request_decode_empty():
    """Test decoding empty data."""
    request = ErstevakRequest(command="T")
    request.decode(b"")
    assert request.data == ""
    assert request.rtu_frame_size == 0


# Tests for update_datastore
# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_update_datastore_read_pressure(context):
    """Test executing a pressure read request ('M')."""
    # Set pressure to 1.234e-3 mbar (encoded as "123417")
    context.store["h"].values[REG_P] = 0xE219  # Low 16 bits
    context.store["h"].values[REG_P + 1] = 0x0001  # High 16 bits
    request = ErstevakRequest(command="M", slave=2, transaction=1)
    response = await request.update_datastore(context)
    print(context.store["h"].values)
    assert isinstance(response, ErstevakRequest)
    assert response.command == "M"
    assert response.data == "123417"
    assert response.registers == [49, 50, 51, 52, 49, 55]  # ASCII bytes for "123403"
    assert response.dev_id == 2
    assert response.transaction_id == 1


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_update_datastore_write_pressure(context):
    """Test executing a pressure write request ('m')."""
    request = ErstevakRequest(command="m", data=b"987620", slave=3, transaction=2)
    response = await request.update_datastore(context)

    assert isinstance(response, ErstevakRequest)
    assert response.command == "m"
    assert response.data == "987620"  # Echoes input data
    assert response.registers == [57, 56, 55, 54, 50, 48]  # ASCII bytes for "987620"
    assert response.dev_id == 3
    assert response.transaction_id == 2
    # Verify written value
    p_encoded = int("987620")
    assert context.store["h"].values[REG_P] == p_encoded & 0xFFFF
    assert context.store["h"].values[REG_P + 1] == (p_encoded >> 16) & 0xFFFF


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_update_datastore_gauge_type(context):
    """Test executing a gauge type request ('T')."""
    request = ErstevakRequest(command="T", slave=1, transaction=4)
    response = await request.update_datastore(context)

    assert isinstance(response, ErstevakRequest)
    assert response.command == "T"
    assert response.data == "MTM09D"
    assert response.registers == [77, 84, 77, 48, 57, 68]  # ASCII bytes for "MTM09D"
    assert response.dev_id == 1
    assert response.transaction_id == 4


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_update_datastore_empty_command(context):
    """Test executing a request with no command."""
    request = ErstevakRequest(data=b"123456", slave=5, transaction=6)
    response = await request.update_datastore(context)

    assert isinstance(response, ErstevakRequest)
    assert response.command == ""
    assert response.data == "123456"  # Default response echoes data
    assert response.registers == [49, 50, 51, 52, 53, 54]  # ASCII bytes for "123456"
    assert response.dev_id == 5
    assert response.transaction_id == 6


# Edge case: decode with invalid UTF-8 data
def test_request_decode_invalid_utf8():
    """Test decoding invalid UTF-8 data."""
    request = ErstevakRequest(command="M")
    with pytest.raises(UnicodeDecodeError):
        request.decode(b"\xff\xfe")  # Invalid UTF-8 sequence


# Edge case: update_datastore with invalid context interaction
# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_update_datastore_invalid_data(context):
    """Test executing a request with invalid data for a command."""
    request = ErstevakRequest(command="m", data=b"abc123")  # Invalid integer for pressure
    response = await request.update_datastore(context)
    assert response.data == "abc123"  # Echoes input despite failure
    assert response.registers == [97, 98, 99, 49, 50, 51]  # ASCII bytes for "abc123"
    # Context unchanged due to ValueError in parse_command
    assert context.store["h"].values[REG_P] == 0
    assert context.store["h"].values[REG_P + 1] == 0


if __name__ == "__main__":
    pytest.main()
