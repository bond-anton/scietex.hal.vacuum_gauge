"""
Thyracont RS485 Version 1 Emulation Module.

This module provides an RS485 server emulator for a Thyracont vacuum gauge (e.g., VSP), extending
`scietex.hal.serial.server.RS485Server`. It simulates the gauge's behavior over the Thyracont RS485
protocol by managing a plain list of holding-register values for pressure, setpoints,
calibration values, and Penning gauge states. The emulator uses custom framing, decoding, and
request handling from the `Thyracont.rs485.v1` subpackage, with properties for easy access to
simulated data.

Classes:
    ThyracontEmulator: An RS485 server emulator for a Thyracont vacuum gauge, providing properties
        to get and set gauge parameters.
"""

from logging import Logger
from typing import Optional

from pymodbus.datastore import ModbusDeviceContext, ModbusSequentialDataBlock
from scietex.hal.serial.config import (
    ModbusSerialConnectionConfigModel,
    SerialConnectionConfigModel,
)
from scietex.hal.serial.server import RS485Server

from .data import _calibration_decode, _calibration_encode
from .decoder import ThyracontDecodePDU
from .emulation_utils import (
    REG_CAL1,
    REG_CAL2,
    REG_P,
    REG_PENNING_STATE,
    REG_PENNING_SYNC,
    REG_SP1,
    REG_SP2,
    pressure_from_reg,
    pressure_to_reg,
)
from .framer import ThyracontASCIIFramer
from .request import ThyracontRequest


def _decoder_with_store(store: list[int]) -> type[ThyracontDecodePDU]:
    """Return a ThyracontDecodePDU subclass bound to a specific register store."""

    class _BoundThyracontDecodePDU(ThyracontDecodePDU):
        def __init__(self, is_server: bool = False) -> None:
            super().__init__(is_server=is_server, store=store)

    return _BoundThyracontDecodePDU


class ThyracontEmulator(RS485Server):
    """
    Thyracont vacuum gauge RS485 emulator.

    An RS485 server emulator for a Thyracont vacuum gauge, extending
    `scietex.hal.serial.server.RS485Server`. It simulates gauge functionality by maintaining a
    plain list of 14 holding-register values, accessible via properties for pressure, setpoints
    (sp1, sp2), calibration values (cal1, cal2), and Penning gauge states (penning_state,
    penning_sync). The emulator uses Thyracont-specific protocol components for framing, decoding,
    and request handling.

    Attributes
    ----------
    devices : dict[int, ModbusSlaveContext]
        A dictionary mapping the device address to its Modbus device context, inherited from
        `RS485Server`.
    __address : int
        The device (slave) address (private, set during initialization).
    _store : list[int]
        A plain list of 14 holding-register values holding the emulated gauge state.
    con_params : SerialConnectionConfigModel | ModbusSerialConnectionConfigModel
        The serial connection configuration, inherited from `RS485Server`.
    logger : Optional[Logger]
        A logger instance for debugging, inherited from `RS485Server`.
    pressure : float
        Gets or sets the simulated pressure value in millibars (REG_P).
    cal1 : float
        Gets or sets the simulated calibration value 1 (REG_CAL1).
    cal2 : float
        Gets or sets the simulated calibration value 2 (REG_CAL2).
    penning_sync : bool
        Gets or sets the simulated Penning synchronization state (REG_PENNING_SYNC).

    Methods
    -------
    __init__(con_params, logger=None, address=1) -> None
        Initializes the emulator with connection parameters, logger, and address.
    sp1 : float
        Property. Gets or sets the simulated setpoint 1 pressure in millibars (REG_SP1).
    sp2 : float
        Property. Gets or sets the simulated setpoint 2 pressure in millibars (REG_SP2).
    penning_state : bool
        Property. Gets or sets the simulated Penning gauge state (REG_PENNING_STATE).
    """

    def __init__(
        self,
        con_params: SerialConnectionConfigModel | ModbusSerialConnectionConfigModel,
        logger: Optional[Logger] = None,
        address: Optional[int] = None,
    ) -> None:
        """
        Initialize an ThyracontEmulator instance.

        Sets up the emulator with a plain list of 14 holding-register values initialized to zero.
        Configures the server with the provided serial connection parameters, logger, and device
        address. Sets default values for pressure (1000 mbar), calibration coefficients (1.0), and
        Penning synchronization (True).

        Parameters
        ----------
        con_params : Union[SerialConnectionConfigModel, ModbusSerialConnectionConfigModel]
            The serial connection configuration (e.g., port, baudrate).
        logger : Optional[Logger], optional
            A logger instance for debugging. Defaults to None.
        address : Optional[int], optional
            The device (slave) address. Defaults to 1.
        """
        self._store: list[int] = [0] * 14
        self.__address: int = 1
        if address is not None:
            self.__address = address
        self.pressure = 1000  # Default pressure in mbar
        self.cal1 = 1.0  # Default calibration 1
        self.cal2 = 1.0  # Default calibration 2
        self.penning_sync = True  # Default Penning sync state
        super().__init__(
            con_params,
            devices={
                self.__address: ModbusDeviceContext(hr=ModbusSequentialDataBlock(0x01, [0] * 14))
            },
            custom_pdu=[ThyracontRequest],
            custom_framer=ThyracontASCIIFramer,
            custom_decoder=_decoder_with_store(self._store),
            logger=logger,
        )

    @property
    def pressure(self) -> Optional[float]:
        """
        Get the simulated pressure value.

        Retrieves the pressure value in millibars from the register store at REG_P.

        Returns
        -------
        float
            The current pressure value in millibars (mbar).
        """
        return pressure_from_reg(self._store, REG_P)

    @pressure.setter
    def pressure(self, p: float) -> None:
        """
        Set the simulated pressure value.

        Writes the pressure value in millibars to the register store at REG_P.

        Parameters
        ----------
        p : float
            The pressure value to set in millibars (mbar).
        """
        pressure_to_reg(self._store, p, REG_P)

    @property
    def sp1(self) -> Optional[float]:
        """
        Get the simulated setpoint 1 pressure.

        Retrieves the setpoint 1 pressure value in millibars from the register store
        at REG_SP1.

        Returns
        -------
        float
            The current setpoint 1 pressure in millibars (mbar).
        """
        return pressure_from_reg(self._store, REG_SP1)

    @sp1.setter
    def sp1(self, p: float) -> None:
        """
        Set the simulated setpoint 1 pressure.

        Writes the setpoint 1 pressure value in millibars to the register store at REG_SP1.

        Parameters
        ----------
        p : float
            The setpoint 1 pressure to set in millibars (mbar).
        """
        pressure_to_reg(self._store, p, REG_SP1)

    @property
    def sp2(self) -> Optional[float]:
        """
        Get the simulated setpoint 2 pressure.

        Retrieves the setpoint 2 pressure value in millibars from the register store
        at REG_SP2.

        Returns
        -------
        float
            The current setpoint 2 pressure in millibars (mbar).
        """
        return pressure_from_reg(self._store, REG_SP2)

    @sp2.setter
    def sp2(self, p: float) -> None:
        """
        Set the simulated setpoint 2 pressure.

        Writes the setpoint 2 pressure value in millibars to the register store at REG_SP2.

        Parameters
        ----------
        p : float
            The setpoint 2 pressure to set in millibars (mbar).
        """
        pressure_to_reg(self._store, p, REG_SP2)

    @property
    def cal1(self) -> Optional[float]:
        """
        Get the simulated calibration value 1.

        Retrieves the calibration value 1 from the register store at REG_CAL1 and decodes it.

        Returns
        -------
        float
            The current calibration value 1.
        """
        cal_str = f"{self._store[REG_CAL1]:06d}"
        return _calibration_decode(cal_str)

    @cal1.setter
    def cal1(self, cal: float) -> None:
        """
        Set the simulated calibration value 1.

        Encodes and writes the calibration value 1 to the register store at REG_CAL1.

        Parameters
        ----------
        cal : float
            The calibration value to set.
        """
        cal_encoded = int(_calibration_encode(cal))
        self._store[REG_CAL1] = cal_encoded

    @property
    def cal2(self) -> Optional[float]:
        """
        Get the simulated calibration value 2.

        Retrieves the calibration value 2 from the register store at REG_CAL2 and decodes it.

        Returns
        -------
        float
            The current calibration value 2.
        """
        cal_str = f"{self._store[REG_CAL2]:06d}"
        return _calibration_decode(cal_str)

    @cal2.setter
    def cal2(self, cal: float) -> None:
        """
        Set the simulated calibration value 2.

        Encodes and writes the calibration value 2 to the register store at REG_CAL2.

        Parameters
        ----------
        cal : float
            The calibration value to set.
        """
        cal_encoded = int(_calibration_encode(cal))
        self._store[REG_CAL2] = cal_encoded

    @property
    def penning_state(self) -> bool:
        """
        Get the simulated Penning gauge state.

        Retrieves the Penning gauge state from the register store at REG_PENNING_STATE and
        converts it to a boolean.

        Returns
        -------
        bool
            The current Penning gauge state (True if on, False if off).
        """
        return bool(self._store[REG_PENNING_STATE])

    @penning_state.setter
    def penning_state(self, state: bool) -> None:
        """
        Set the simulated Penning gauge state.

        Writes the Penning gauge state to the register store at REG_PENNING_STATE
        as an integer (1 or 0).

        Parameters
        ----------
        state : bool
            The state to set (True for on, False for off).
        """
        self._store[REG_PENNING_STATE] = int(bool(state))

    @property
    def penning_sync(self) -> bool:
        """
        Get the simulated Penning synchronization state.

        Retrieves the Penning synchronization state from the register store at
        REG_PENNING_SYNC and converts it to a boolean.

        Returns
        -------
        bool
            The current Penning synchronization state (True if on, False if off).
        """
        return bool(self._store[REG_PENNING_SYNC])

    @penning_sync.setter
    def penning_sync(self, state: bool) -> None:
        """
        Set the simulated Penning synchronization state.

        Writes the Penning synchronization state to the register store at REG_PENNING_SYNC as
        an integer (1 or 0).

        Parameters
        ----------
        state : bool
            The synchronization state to set (True for on, False for off).
        """
        self._store[REG_PENNING_SYNC] = int(bool(state))
