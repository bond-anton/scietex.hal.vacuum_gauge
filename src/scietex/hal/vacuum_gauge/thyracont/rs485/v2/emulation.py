"""
Thyracont RS485 Version 2 Emulation Module.

This module provides an RS485 server emulator for a Thyracont vacuum gauge (e.g., MTM9D), extending
`scietex.hal.serial.server.RS485Server`. It simulates the gauge's behavior over the Thyracont RS485
V2 protocol by managing a `ThyracontV2State` dataclass, which holds pressure, operating hours, wear
statistics, and identification strings. The emulator uses custom framing, decoding, and request
handling from the `Thyracont.rs485.v2` subpackage, with properties for easy access to simulated
data.

Classes:
    ThyracontV2Emulator: An RS485 server emulator for a Thyracont vacuum gauge, providing properties
        to get and set gauge parameters.
"""

from logging import Logger
from typing import Optional

from pymodbus.datastore import ModbusDeviceContext
from scietex.hal.serial.config import (
    ModbusSerialConnectionConfigModel,
    SerialConnectionConfigModel,
)
from scietex.hal.serial.server import RS485Server

from .decoder import ThyracontDecodePDU
from .emulation_utils import ThyracontV2State
from .framer import ThyracontASCIIFramer
from .request import ThyracontRequest


def _decoder_with_state(state: ThyracontV2State) -> type[ThyracontDecodePDU]:
    """Return a ThyracontDecodePDU subclass bound to a specific device state."""

    class _BoundThyracontDecodePDU(ThyracontDecodePDU):
        def __init__(self, is_server: bool = False) -> None:
            super().__init__(is_server=is_server, state=state)

    return _BoundThyracontDecodePDU


class ThyracontV2Emulator(RS485Server):
    """
    Thyracont vacuum gauge RS485 V2 emulator.

    An RS485 server emulator for a Thyracont vacuum gauge, extending
    `scietex.hal.serial.server.RS485Server`. It simulates gauge functionality by maintaining a
    `ThyracontV2State` dataclass, accessible via properties for pressure, operating hours, wear
    statistics, and identification strings. The emulator uses Thyracont-specific protocol
    components for framing, decoding, and request handling.

    Attributes
    ----------
    devices : dict[int, ModbusDeviceContext]
        A dictionary mapping the device address to its Modbus device context, inherited from
        `RS485Server`.
    _state : ThyracontV2State
        The emulated device state holding pressure, hours, wear, and identification data.
    con_params : SerialConnectionConfigModel | ModbusSerialConnectionConfigModel
        The serial connection configuration, inherited from `RS485Server`.
    logger : Optional[Logger]
        A logger instance for debugging, inherited from `RS485Server`.
    pressure : float
        Gets or sets the simulated pressure value in millibars.
    gauge_hours : float
        Gets or sets the simulated gauge operating hours.
    cathode_hours : Optional[float]
        Gets or sets the simulated cathode operating hours (None means no cathode).
    wear : float
        Gets or sets the simulated sensor wear percentage (Pirani).
    hours_since_zero_adjustment : float
        Gets or sets the simulated hours since the last zero adjustment.
    model : str
        Gets or sets the simulated gauge model identifier.
    product_name : str
        Gets or sets the simulated product name.
    device_sn : str
        Gets or sets the simulated device serial number.
    head_sn : str
        Gets or sets the simulated head serial number.
    device_version : str
        Gets or sets the simulated device version.
    firmware_version : str
        Gets or sets the simulated firmware version.
    bootloader_version : str
        Gets or sets the simulated bootloader version.
    """

    def __init__(
        self,
        con_params: SerialConnectionConfigModel | ModbusSerialConnectionConfigModel,
        logger: Optional[Logger] = None,
        address: Optional[int] = None,
    ) -> None:
        """
        Initialize a ThyracontV2Emulator instance.

        Sets up the emulator with a `ThyracontV2State` holding default values (pressure 1000 mbar,
        gauge hours 0, no cathode, model "MTM9D"). Configures the server with the provided serial
        connection parameters, logger, and device address.

        Parameters
        ----------
        con_params : Union[SerialConnectionConfigModel, ModbusSerialConnectionConfigModel]
            The serial connection configuration (e.g., port, baudrate).
        logger : Optional[Logger], optional
            A logger instance for debugging. Defaults to None.
        address : Optional[int], optional
            The device (slave) address. Defaults to 1.
        """
        self._state: ThyracontV2State = ThyracontV2State()
        self.__address: int = 1
        if address is not None:
            self.__address = address
        super().__init__(
            con_params,
            devices={self.__address: ModbusDeviceContext()},
            custom_pdu=[ThyracontRequest],
            custom_framer=ThyracontASCIIFramer,
            custom_decoder=_decoder_with_state(self._state),
            logger=logger,
        )

    @property
    def pressure(self) -> float:
        """Get the simulated pressure value in millibars."""
        return self._state.pressure

    @pressure.setter
    def pressure(self, p: float) -> None:
        """Set the simulated pressure value in millibars."""
        self._state.pressure = p

    @property
    def gauge_hours(self) -> float:
        """Get the simulated gauge operating hours."""
        return self._state.gauge_hours

    @gauge_hours.setter
    def gauge_hours(self, hours: float) -> None:
        """Set the simulated gauge operating hours."""
        self._state.gauge_hours = hours

    @property
    def cathode_hours(self) -> Optional[float]:
        """Get the simulated cathode operating hours (None means no cathode)."""
        return self._state.cathode_hours

    @cathode_hours.setter
    def cathode_hours(self, hours: Optional[float]) -> None:
        """Set the simulated cathode operating hours (None means no cathode)."""
        self._state.cathode_hours = hours

    @property
    def wear(self) -> float:
        """Get the simulated sensor wear percentage (Pirani)."""
        return self._state.wear

    @wear.setter
    def wear(self, wear: float) -> None:
        """Set the simulated sensor wear percentage (Pirani)."""
        self._state.wear = wear

    @property
    def hours_since_zero_adjustment(self) -> float:
        """Get the simulated hours since the last zero adjustment."""
        return self._state.hours_since_zero_adjustment

    @hours_since_zero_adjustment.setter
    def hours_since_zero_adjustment(self, hours: float) -> None:
        """Set the simulated hours since the last zero adjustment."""
        self._state.hours_since_zero_adjustment = hours

    @property
    def model(self) -> str:
        """Get the simulated gauge model identifier."""
        return self._state.model

    @model.setter
    def model(self, model: str) -> None:
        """Set the simulated gauge model identifier."""
        self._state.model = model

    @property
    def product_name(self) -> str:
        """Get the simulated product name."""
        return self._state.product_name

    @product_name.setter
    def product_name(self, name: str) -> None:
        """Set the simulated product name."""
        self._state.product_name = name

    @property
    def device_sn(self) -> str:
        """Get the simulated device serial number."""
        return self._state.device_sn

    @device_sn.setter
    def device_sn(self, sn: str) -> None:
        """Set the simulated device serial number."""
        self._state.device_sn = sn

    @property
    def head_sn(self) -> str:
        """Get the simulated head serial number."""
        return self._state.head_sn

    @head_sn.setter
    def head_sn(self, sn: str) -> None:
        """Set the simulated head serial number."""
        self._state.head_sn = sn

    @property
    def device_version(self) -> str:
        """Get the simulated device version."""
        return self._state.device_version

    @device_version.setter
    def device_version(self, version: str) -> None:
        """Set the simulated device version."""
        self._state.device_version = version

    @property
    def firmware_version(self) -> str:
        """Get the simulated firmware version."""
        return self._state.firmware_version

    @firmware_version.setter
    def firmware_version(self, version: str) -> None:
        """Set the simulated firmware version."""
        self._state.firmware_version = version

    @property
    def bootloader_version(self) -> str:
        """Get the simulated bootloader version."""
        return self._state.bootloader_version

    @bootloader_version.setter
    def bootloader_version(self, version: str) -> None:
        """Set the simulated bootloader version."""
        self._state.bootloader_version = version
