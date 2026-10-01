"""
Shared pytest fixtures for the vacuum gauge test suite.

These fixtures are available to every test module under ``tests/``. Test modules
that define their own ``logger_fixture``/``vsp_fixture``/``modbus_config``
fixtures shadow these, so no existing test changes behaviour.
"""

import logging
import socket

import pytest

from scietex.hal.serial import VirtualSerialPair
from scietex.hal.serial.config import ModbusSerialConnectionConfig


@pytest.fixture
def logger_fixture():
    """Provide a logger for debugging."""
    return logging.getLogger("test_logger")


# pylint: disable=redefined-outer-name
@pytest.fixture
def vsp_fixture(logger_fixture):
    """Start a virtual serial pair and stop it on teardown."""
    vsp = VirtualSerialPair(logger=logger_fixture)
    vsp.start()
    yield vsp
    vsp.stop()


@pytest.fixture
def free_port() -> int:
    """Pick a free TCP port.

    The socket is closed before the port is used, so a concurrent process could
    in principle claim it in between. Tests bind immediately after, and the
    window is small enough that this is not a practical concern.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# pylint: disable=redefined-outer-name
@pytest.fixture
def modbus_config(vsp_fixture):
    """Provide a Modbus serial connection config for each virtual port."""
    return [
        ModbusSerialConnectionConfig(
            port=vsp_port,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=1.0,
        )
        for vsp_port in vsp_fixture.serial_ports
    ]
