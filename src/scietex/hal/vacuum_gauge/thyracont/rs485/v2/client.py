"""
Thyracont RS485 Version 2 Client Module.

This module provides a custom RS485 client for interacting with a Thyracont vacuum gauge (e.g.,
MTM9D) over its RS485 protocol. It extends `scietex.hal.serial.client.RS485Client` and supports
two backends: `pymodbus` for Modbus-based communication and `pyserial` for direct serial
communication. The client uses custom framing, decoding, and request handling from the
`Thyracont.rs485.v2` subpackage to manage gauge operations such as pressure measurement,
calibration, setpoint adjustments, and Penning gauge control.

Classes:
    ThyracontVacuumGauge: An RS485 client class for Thyracont vacuum gauges, providing methods
        to read and write gauge data.
"""

from typing import Optional, Callable
import sys
import asyncio
from functools import wraps
from logging import Logger

import serial
from pymodbus.pdu import ModbusPDU

from scietex.hal.serial.config import (
    SerialConnectionConfigModel,
    ModbusSerialConnectionConfigModel,
)
from scietex.hal.serial.client import RS485Client

from .data import (
    AccessCode,
    ErrorMessage,
    Sensor,
    DisplayOrientation,
    DisplayUnits,
    CathodeControlMode,
    StreamingMode,
    encode_float_1,
    encode_float,
    decode_float,
    decode_range,
    decode_relay_data,
    encode_relay_data,
    decode_sensor_transition,
    encode_sensor_transition,
    decode_output_characteristic,
    encode_tab_output_characteristic,
    decode_operating_hours,
    decode_wear_status,
    adjust_baudrate,
)
from ..checksum import check_checksum
from .framer import ThyracontASCIIFramer
from .decoder import ThyracontDecodePDU
from .request import ThyracontRequest


# Determine the correct TimeoutError based on Python version
if sys.version_info >= (3, 11):
    TimeoutErrorAlias = asyncio.TimeoutError
else:
    # import asyncio.exceptions
    TimeoutErrorAlias = asyncio.exceptions.TimeoutError


def check_success(func: Callable) -> Callable:
    """Check success wrapper."""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> bool:
        """Check if no error is returned."""
        failed: Optional[str] = await func(*args, **kwargs)
        if not failed:
            return True
        return False

    return wrapper


def parse_float(func: Callable) -> Callable:
    """Parse integer response wrapper."""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Optional[float]:
        """Parse integer response."""
        result: Optional[str] = await func(*args, **kwargs)
        if result is not None:
            try:
                return float(result)
            except (TypeError, ValueError):
                return None
        return None

    return wrapper


def parse_int(func: Callable) -> Callable:
    """Parse integer response wrapper."""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Optional[int]:
        """Parse integer response."""
        result: Optional[str] = await func(*args, **kwargs)
        if result is not None:
            try:
                return int(result)
            except (TypeError, ValueError):
                return None
        return None

    return wrapper


def parse_bool(func: Callable) -> Callable:
    """Parse boolean response wrapper."""

    @wraps(func)
    async def wrapper(*args, **kwargs) -> bool:
        """Parse bool response."""
        result: Optional[str] = await func(*args, **kwargs)
        if result is not None:
            try:
                return bool(int(result))
            except (TypeError, ValueError):
                return False
        return False

    return wrapper


# pylint: disable=too-many-public-methods
class ThyracontVacuumGauge(RS485Client):
    """
    Thyracont vacuum gauge RS485 V2 client.
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments,duplicate-code
    def __init__(
        self,
        connection_config: SerialConnectionConfigModel | ModbusSerialConnectionConfigModel,
        address: int = 1,
        label: Optional[str] = None,
        logger: Optional[Logger] = None,
        timeout: Optional[float] = None,
        backend: Optional[str] = None,
    ) -> None:
        """
        Initialize an ThyracontVacuumGauge client instance.

        Sets up the client with serial connection parameters, device address, and optional settings
        for label, logger, timeout, and backend. Configures the inherited `RS485Client` with
        Thyracont-specific framer, decoder, and response type.

        Parameters
        ----------
        connection_config : Union[SerialConnectionConfigModel, ModbusSerialConnectionConfigModel]
            The serial connection configuration (e.g., port, baudrate).
        address : int, optional
            The device (slave) address. Defaults to 1.
        label : Optional[str], optional
            A custom label for the gauge. Defaults to "Thyracont Gauge" if None.
        logger : Optional[Logger], optional
            A logger instance for debugging. Defaults to None.
        timeout : Optional[float], optional
            The communication timeout in seconds. Defaults to 1.0 if None.
        backend : Optional[str], optional
            The communication backend ("pymodbus" or "pyserial"). Defaults to "pymodbus" if None.
        """
        _label = "Vacuum Gauge"
        if label is not None:  # Corrected logic to use provided label
            _label = label
        self.timeout: float = 1.0
        if timeout is not None:
            self.timeout = timeout
        super().__init__(
            con_params=connection_config,
            address=address,
            label=_label,
            custom_framer=ThyracontASCIIFramer,
            custom_decoder=ThyracontDecodePDU,
            custom_response=[ThyracontRequest],
            logger=logger,
        )
        self.backend = "pymodbus"
        if backend == "pyserial":
            self.backend = "pyserial"

    # pylint: disable=duplicate-code
    async def request_gauge(
        self, access_code: AccessCode, command: str, data: Optional[bytes] = None
    ) -> Optional[str]:
        """
        Send a command to the gauge and return the response data.
        """
        result = None
        request = ThyracontRequest(
            access_code=access_code,
            command=command,
            data=data,
            dev_id=self.address,
            transaction_id=0,
        )
        self.logger.debug("REQ: %s", request)
        if self.backend == "pymodbus":
            try:
                response: Optional[ModbusPDU] = await asyncio.wait_for(
                    self.execute(request, no_response_expected=False),
                    timeout=self.timeout,
                )
                if response and hasattr(response, "data"):
                    self.logger.debug("Response: %s", response.data)
                    if response.function_code == 7:
                        self.process_error_response(response.data)
                        response.rtu_frame_size -= len(response.data)
                        response.data = None
                    result = response.data
            except TimeoutErrorAlias:
                result = None
        elif self.backend == "pyserial":
            custom_framer = ThyracontASCIIFramer(ThyracontDecodePDU(is_server=False))
            encoded_frame = custom_framer.buildFrame(request)  # Corrected method name
            self.logger.debug("Encoded Frame: %s", encoded_frame)
            inter_byte_timeout = 0.01
            if hasattr(self.con_params, "inter_byte_timeout") and isinstance(
                self.con_params.inter_byte_timeout, float
            ):
                inter_byte_timeout = self.con_params.inter_byte_timeout
            con = serial.Serial(
                port=self.con_params.port,
                baudrate=self.con_params.baudrate,
                bytesize=self.con_params.bytesize,
                stopbits=self.con_params.stopbits,
                parity=self.con_params.parity,
                timeout=self.con_params.timeout,
                inter_byte_timeout=inter_byte_timeout,
            )
            con.write(encoded_frame)
            serial_response = con.readline()
            self.logger.debug("SERIAL READ: %s", serial_response)
            parsed = self._parse_response(serial_response)
            result = parsed["data"]
            con.close()
        return result

    def _parse_response(self, response: bytes) -> dict:
        """
        Parse a raw serial response into a dictionary of components.
        """
        # pylint: disable=too-many-branches
        result: dict = {
            "addr": None,
            "access_code": None,
            "cmd": None,
            "data_len": None,
            "data": None,
            "crc": None,
        }
        self.logger.debug("Parsing response %s", response)
        if response:
            if check_checksum(response[:-2], response[-2]):
                response_data: str = response.decode()[:-2]
                r_address: int = int(response_data[:3])
                if self.address == r_address:
                    result["addr"] = self.address
                    result["access_code"] = int(response_data[3])
                    result["cmd"] = response_data[4:6]
                    result["data_len"] = int(response_data[6:8])
                    if result["data_len"] > 0:
                        result["data"] = response_data[8 : 8 + result["data_len"]]
                    result["crc"] = response[-2]
                else:
                    self.logger.error("Wrong address")
                    return result
                if result["access_code"] == 7:  # Error
                    self.process_error_response(result["data"].encode())
                    result["data"] = None
                    result["data_len"] = 0
            else:
                self.logger.error("Wrong checksum")
                return result
        return result

    def process_error_response(self, data: bytes | str):
        """Process error."""
        if isinstance(data, bytes):
            err_msg = ErrorMessage.from_str(data.decode()).description()
        elif isinstance(data, str):
            err_msg = ErrorMessage.from_str(data).description()
        else:
            err_msg = "Unknown error"
        self.logger.error("ERROR: %s", err_msg)

    async def get_model(self) -> Optional[str]:
        """Retrieve the gauge model identifier."""
        return await self.request_gauge(access_code=AccessCode.READ, command="TD")

    async def get_product_name(self) -> Optional[str]:
        """Retrieve the gauge product name identifier."""
        return await self.request_gauge(access_code=AccessCode.READ, command="PN")

    async def get_device_sn(self) -> Optional[str]:
        """Retrieve device serial number."""
        return await self.request_gauge(access_code=AccessCode.READ, command="SD")

    async def get_head_sn(self) -> Optional[str]:
        """Retrieve the head serial number."""
        return await self.request_gauge(access_code=AccessCode.READ, command="SH")

    async def get_device_version(self) -> Optional[str]:
        """Retrieve the device version identifier."""
        return await self.request_gauge(access_code=AccessCode.READ, command="VD")

    async def get_firmware_version(self) -> Optional[str]:
        """Retrieve the firmware version identifier."""
        return await self.request_gauge(access_code=AccessCode.READ, command="VF")

    async def get_bootloader_version(self) -> Optional[str]:
        """Retrieve the bootloader version identifier."""
        return await self.request_gauge(access_code=AccessCode.READ, command="VB")

    @check_success
    async def restart_gauge(self) -> Optional[str]:
        """Restart the gauge."""
        return await self.request_gauge(access_code=AccessCode.WRITE, command="DR")

    async def get_operating_hours(self) -> Optional[dict[str, Optional[float]]]:
        """Retrieve operating-hours statistics."""
        oh_data: Optional[str] = await self.request_gauge(access_code=AccessCode.READ, command="OH")
        return decode_operating_hours(oh_data)

    async def get_sensor_statistics(
        self, sensor: Sensor | int
    ) -> Optional[dict[str, Optional[float | str]]]:
        """Retrieve sensor statistics and wear status."""
        _sensor: Sensor = sensor if isinstance(sensor, Sensor) else Sensor.from_int(sensor)
        if _sensor not in (Sensor.PIRANI, Sensor.HOT_CATHODE, Sensor.COLD_CATHODE):
            return None
        pm_data: Optional[str] = await self.request_gauge(
            access_code=AccessCode.READ, command="PM", data=f"{_sensor.value}".encode()
        )
        return decode_wear_status(pm_data)

    @parse_int
    async def get_response_delay(self) -> Optional[str]:
        """Retrieve current response delay in microseconds."""
        return await self.request_gauge(access_code=AccessCode.READ, command="RD")

    async def set_response_delay(self, us: int, store: Optional[bool] = None) -> Optional[int]:
        """Set response delay in microseconds."""
        delay = max(0, min(us, 99999))
        data = f"{'S' if store else ''}{delay}".encode()
        await self.request_gauge(access_code=AccessCode.WRITE, command="RD", data=data)
        return await self.get_response_delay()

    async def reset_response_delay(self) -> Optional[int]:
        """Reset response delay to default value."""
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="RD")
        return await self.get_response_delay()

    @check_success
    async def set_baudrate(
        self, baudrate: int, store: Optional[bool] = None, max_baudrate: int = 250000
    ) -> Optional[str]:
        """Set communication baudrate."""
        br = adjust_baudrate(baudrate, max_baudrate)
        return await self.request_gauge(
            access_code=AccessCode.WRITE, command="BR", data=f"{'S' if store else ''}{br}".encode()
        )

    @check_success
    async def set_device_address(self, da: int) -> Optional[str]:
        """Set device address."""
        return await self.request_gauge(
            access_code=AccessCode.WRITE, command="DA", data=f"{max(1, min(da, 16))}".encode()
        )

    @check_success
    async def reset_device_address(self) -> Optional[str]:
        """Reset device address to default value."""
        return await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="DA")

    async def get_measurement_range(self) -> Optional[dict[str, Optional[float]]]:
        """
        Retrieve the gauge measurement range.
        """
        result: Optional[str] = await self.request_gauge(access_code=AccessCode.READ, command="MR")
        if result is not None:
            return decode_range(result)
        return None

    async def streaming_mode(
        self,
        mode: Optional[StreamingMode | int] = None,
        additional_data: Optional[list[int | str]] = None,
    ) -> bool:
        """Enable/disable streaming mode."""
        data: str = f"{StreamingMode.V1.value}"
        if mode is not None:
            if isinstance(mode, StreamingMode):
                data = f"{mode.value}"
            elif isinstance(mode, int):
                data = f"{max(0, min(4, mode))}"
        if additional_data is not None:
            for data_channel in additional_data:
                data += f"D{data_channel}"
        result: Optional[str] = await self.request_gauge(
            access_code=AccessCode.WRITE, command="SM", data=data.encode()
        )
        if result:
            return False
        return True

    async def measure(self, sensor: Optional[Sensor | int] = None) -> Optional[float]:
        """
        Measure the current pressure in millibars.

        Sends the "MV" command to read the current pressure and decodes it from the response.

        Returns
        -------
        Optional[float]
            The pressure value in millibars (mbar), or None if the request or decoding fails.
        """
        _sensor: Sensor = Sensor.AUTO
        if sensor is not None:
            _sensor = sensor if isinstance(sensor, Sensor) else Sensor.from_int(sensor)
        cmd: str = f"M{_sensor.value if _sensor.value > 0 else 'V'}"
        gauge_data: Optional[str] = await self.request_gauge(
            access_code=AccessCode.READ, command=cmd
        )
        if gauge_data is not None:
            return decode_float(gauge_data)
        return None

    @parse_float
    async def get_temperature(self, sensor: Sensor | int) -> Optional[str]:
        """Get sensor temperature"""
        _sensor: Sensor = sensor if isinstance(sensor, Sensor) else Sensor.from_int(sensor)
        if _sensor not in (Sensor.PIEZO, Sensor.AMBIENT):
            return None
        return await self.request_gauge(access_code=AccessCode.READ, command=f"T{_sensor.value}")

    async def get_relay(self, rl_n: int) -> Optional[dict[str, Optional[float | str]]]:
        """Retrieve relay settings"""
        rl_data: Optional[str] = await self.request_gauge(
            access_code=AccessCode.READ, command=f"R{rl_n}"
        )
        if rl_data is not None:
            try:
                return decode_relay_data(rl_data)
            except (TypeError, ValueError):
                pass
        return None

    async def set_relay(
        self, rl_n: int, settings: dict[str, Optional[float | str]]
    ) -> Optional[dict[str, Optional[float | str]]]:
        """Set relay settings."""
        data = encode_relay_data(settings)
        await self.request_gauge(access_code=AccessCode.WRITE, command=f"R{rl_n}", data=data)
        return await self.get_relay(rl_n)

    async def reset_relay(self, rl_n: int) -> Optional[dict[str, Optional[float | str]]]:
        """Reset relay to default value."""
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command=f"R{rl_n}")
        return await self.get_relay(rl_n)

    async def get_display_units(self) -> Optional[DisplayUnits]:
        """Get current display units."""
        units: Optional[str] = await self.request_gauge(access_code=AccessCode.READ, command="DU")
        if units:
            try:
                return DisplayUnits.from_str(units)
            except ValueError:
                pass
        return None

    async def set_display_units(self, units: DisplayUnits | str) -> Optional[DisplayUnits]:
        """Set display units."""
        _units: DisplayUnits = (
            units if isinstance(units, DisplayUnits) else DisplayUnits.from_str(units)
        )
        await self.request_gauge(
            access_code=AccessCode.WRITE, command="DU", data=_units.value.encode()
        )
        return await self.get_display_units()

    async def reset_display_units(self) -> Optional[DisplayUnits]:
        """Reset display units to default value."""
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="DU")
        return await self.get_display_units()

    async def get_display_orientation(self) -> Optional[DisplayOrientation]:
        """Get display orientation"""
        response: Optional[str] = await self.request_gauge(
            access_code=AccessCode.READ, command="DO"
        )
        if response is not None:
            try:
                return DisplayOrientation(int(bool(int(response))))
            except (TypeError, ValueError):
                pass
        return None

    async def set_display_orientation(
        self, direction: DisplayOrientation | int
    ) -> Optional[DisplayOrientation]:
        """Set display orientation."""
        _direction: DisplayOrientation = (
            direction
            if isinstance(direction, DisplayOrientation)
            else DisplayOrientation(int(bool(int(direction))))
        )
        data = f"{_direction.value}".encode()
        await self.request_gauge(access_code=AccessCode.WRITE, command="DO", data=data)
        return await self.get_display_orientation()

    async def reset_display_orientation(self) -> Optional[DisplayOrientation]:
        """Reset display orientation to default value."""
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="DO")
        return await self.get_display_orientation()

    async def rotate_display(self) -> Optional[DisplayOrientation]:
        """Change display orientation to opposite."""
        orientation = await self.get_display_orientation()
        if orientation is not None:
            rot = DisplayOrientation(int(not bool(orientation.value)))
            return await self.set_display_orientation(rot)
        return None

    async def get_display_data_source(self) -> Optional[Sensor]:
        """Retrieve display data source."""
        response: Optional[str] = await self.request_gauge(
            access_code=AccessCode.READ, command="DD"
        )
        if response is not None:
            try:
                return Sensor.from_int(int(response))
            except (TypeError, ValueError):
                pass
        return None

    async def set_display_data_source(self, sensor: Sensor | int) -> Optional[Sensor]:
        """Set display data source to value."""
        _sensor: Sensor = sensor if isinstance(sensor, Sensor) else Sensor.from_int(sensor)
        await self.request_gauge(
            access_code=AccessCode.WRITE, command="DD", data=f"{_sensor.value}".encode()
        )
        return await self.get_display_data_source()

    async def reset_display_data_source(self) -> Optional[Sensor]:
        """Reset display data source to default value."""
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="DD")
        return await self.get_display_data_source()

    @check_success
    async def adjust_high(self, pressure: Optional[float] = None) -> Optional[str]:
        """Adjust high pressure level, over-range (e.g. at atmospheric pressure)."""
        data: Optional[bytes] = None
        if pressure is not None:
            try:
                data = encode_float_1(pressure).encode()
            except (TypeError, ValueError):
                return "ERROR"
        return await self.request_gauge(access_code=AccessCode.WRITE, command="AH", data=data)

    @check_success
    async def adjust_low(self, pressure: Optional[float] = None) -> Optional[str]:
        """Adjust sensor to low pressure, e.g. under range."""
        data: Optional[bytes] = None
        if pressure is not None:
            try:
                data = encode_float_1(pressure).encode()
            except (TypeError, ValueError):
                return "Error"
        return await self.request_gauge(access_code=AccessCode.WRITE, command="AL", data=data)

    @parse_bool
    async def get_degas(self) -> Optional[str]:
        """Retrieve degas ON/OFF state."""
        return await self.request_gauge(access_code=AccessCode.READ, command="DG")

    async def set_degas(self, state: bool) -> bool:
        """Turn degas ON/OFF."""
        await self.request_gauge(
            access_code=AccessCode.WRITE, command="DG", data=f"{int(bool(state))}".encode()
        )
        return await self.get_degas()

    @parse_bool
    async def get_digital_logic(self) -> Optional[str]:
        """
        Retrieve Digital/Degas logic state.
        Degas Logic is active low (0/False) (VSH)
        Digital Logic is active low (0/False) (VSI/VSM, VxL)
        """
        return await self.request_gauge(access_code=AccessCode.READ, command="DL")

    async def set_digital_logic(self, state: bool | int) -> bool:
        """
        Set Digital/Degas logic to provided state.
        Degas Logic is active low (0/False, 1/True) (VSH)
        Digital Logic is active low (0/False, 1/True) (VSI/VSM, VxL)
        """
        data = f"{int(bool(state))}".encode()
        await self.request_gauge(access_code=AccessCode.WRITE, command="DL", data=data)
        return await self.get_digital_logic()

    async def reset_digital_logic(self):
        """
        Reset Digital/Degas logic to default state.
        Degas Logic is active low (0/False) (VSH)
        Digital Logic is active high (1/True) (VSI/VSM, VxL)
        """
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="DL")
        return await self.get_digital_logic()

    async def get_sensor_transition(self) -> Optional[dict[str, Optional[int | float]]]:
        """Retrieve sensor transition rule."""
        result: Optional[str] = await self.request_gauge(access_code=AccessCode.READ, command="ST")
        if result is not None:
            return decode_sensor_transition(result)
        return None

    async def set_sensor_transition(
        self, transition_rule: dict[str, Optional[int | float]]
    ) -> Optional[dict[str, Optional[int | float]]]:
        """Set sensor transition rule."""
        data = encode_sensor_transition(transition_rule)
        await self.request_gauge(access_code=AccessCode.WRITE, command="ST", data=data)
        return await self.get_sensor_transition()

    async def reset_sensor_transition(self) -> Optional[dict[str, Optional[int | float]]]:
        """Reset sensor transition to default rule."""
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="ST")
        return await self.get_sensor_transition()

    @parse_bool
    async def get_cathode_status(self) -> Optional[str]:
        """Retrieve cathode ON/OFF status."""
        return await self.request_gauge(access_code=AccessCode.READ, command="CA")

    async def get_cathode_control_mode(self) -> Optional[CathodeControlMode]:
        """Retrieve cathode control mode (MAN/AUTO)."""
        state: Optional[str] = await self.request_gauge(access_code=AccessCode.READ, command="CM")
        if state is not None:
            try:
                return CathodeControlMode(int(state))
            except (TypeError, ValueError):
                pass
        return None

    async def set_cathode_control_mode(
        self, mode: CathodeControlMode | int | bool
    ) -> Optional[CathodeControlMode]:
        """Set cathode control mode (MAN/AUTO)."""
        if isinstance(mode, (bool, int)):
            data = f"{int(bool(mode))}".encode()
        else:
            data = f"{mode.value}".encode()
        await self.request_gauge(access_code=AccessCode.WRITE, command="CM", data=data)
        return await self.get_cathode_control_mode()

    async def reset_cathode_control_mode(self) -> Optional[CathodeControlMode]:
        """Reset cathode control mode (MAN/AUTO) to default value"""
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="CM")
        return await self.get_cathode_control_mode()

    @parse_bool
    async def get_cathode_control(self) -> Optional[str]:
        """Retrieve cathode ON/OFF control state."""
        return await self.request_gauge(access_code=AccessCode.READ, command="CC")

    async def set_cathode_control(self, state: bool) -> bool:
        """Set cathode ON/OFF control state."""
        await self.request_gauge(
            access_code=AccessCode.WRITE, command="CC", data=f"{int(bool(state))}".encode()
        )
        return await self.get_cathode_control()

    async def reset_cathode_control(self) -> bool:
        """Reset cathode control to default value"""
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="CC")
        return await self.get_cathode_control()

    @parse_int
    async def get_filament_control(self) -> Optional[str]:
        """Retrieve filament control mode."""
        return await self.request_gauge(access_code=AccessCode.READ, command="FC")

    async def set_filament_control(self, mode: int) -> Optional[int]:
        """Set filament control to selected mode."""
        await self.request_gauge(
            access_code=AccessCode.WRITE, command="FC", data=f"{mode}".encode()
        )
        return await self.get_filament_control()

    async def reset_filament_control(self) -> Optional[int]:
        """Reset filament control to default mode"""
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="FC")
        return await self.get_filament_control()

    @parse_int
    async def get_filament_number(self) -> Optional[str]:
        """Retrieve filament number"""
        return await self.request_gauge(access_code=AccessCode.READ, command="FN")

    @parse_int
    async def get_filament_status(self) -> Optional[str]:
        """Retrieve current filament status."""
        return await self.request_gauge(access_code=AccessCode.READ, command="FS")

    @parse_float
    async def get_gas_correction(self, sensor: Sensor | int) -> Optional[str]:
        """Retrieve gas correction coefficient for provided sensor."""
        _sensor: Sensor = sensor if isinstance(sensor, Sensor) else Sensor.from_int(sensor)
        return await self.request_gauge(access_code=AccessCode.READ, command=f"C{_sensor.value}")

    async def set_gas_correction(self, sensor: Sensor | int, corr: float) -> Optional[float]:
        """Set gas correction coefficient for provided sensor."""
        _sensor: Sensor = sensor if isinstance(sensor, Sensor) else Sensor.from_int(sensor)
        await self.request_gauge(
            access_code=AccessCode.WRITE,
            command=f"C{_sensor.value}",
            data=f"{encode_float_1(corr)}".encode(),
        )
        return await self.get_gas_correction(sensor)

    async def reset_gas_correction(self, sensor: Sensor | int) -> Optional[float]:
        """Set gas correction coefficient for provided sensor to default value."""
        _sensor: Sensor = sensor if isinstance(sensor, Sensor) else Sensor.from_int(sensor)
        await self.request_gauge(
            access_code=AccessCode.FACTORY_DEFAULT, command=f"C{_sensor.value}"
        )
        return await self.get_gas_correction(sensor)

    async def get_output_characteristic(self) -> Optional[dict[str, Optional[str | int | float]]]:
        """Retrieve output characteristics"""
        oc: Optional[str] = await self.request_gauge(access_code=AccessCode.READ, command="OC")
        if oc is not None:
            try:
                return decode_output_characteristic(oc)
            except (TypeError, ValueError):
                pass
        return None

    async def reset_output_characteristic(
        self,
    ) -> Optional[dict[str, Optional[str | int | float]]]:
        """Reset output characteristics to default value"""
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="OC")
        return await self.get_output_characteristic()

    async def set_tab_output_characteristic(
        self,
        tab: dict[str, Optional[str | int | float]],
        nodes: list[dict[str, Optional[str | int | float]]],
    ) -> tuple[
        Optional[dict[str, Optional[str | int | float]]],
        Optional[list[dict[str, Optional[str | int | float]]]],
    ]:
        """Set output characteristics."""
        tab_data = encode_tab_output_characteristic(tab).encode()
        nodes_set = []
        failed: Optional[str] = await self.request_gauge(
            access_code=AccessCode.WRITE, command="OC", data=tab_data
        )
        if not failed:
            for node in nodes:
                node_set_data = encode_tab_output_characteristic(node).encode()
                failed = await self.request_gauge(
                    access_code=AccessCode.WRITE, command="OC", data=node_set_data
                )
                if not failed:
                    node_data: Optional[str] = await self.request_gauge(
                        access_code=AccessCode.READ, command="OC", data=f"E{node['node']}".encode()
                    )
                    if node_data is not None:
                        node_data_decoded = decode_output_characteristic(node_data)
                        node_data_decoded["node"] = node["node"]
                        nodes_set.append(node_data_decoded)
            oc = await self.get_output_characteristic()
            return oc, nodes_set
        return None, None

    @parse_bool
    async def get_panel_locked(self) -> Optional[str]:
        """Retrieve panel locked state."""
        return await self.request_gauge(access_code=AccessCode.READ, command="PS")

    async def set_panel_locked(self, locked: bool) -> bool:
        """Lock/unlock the panel."""
        await self.request_gauge(
            access_code=AccessCode.WRITE, command="PS", data=f"{int(bool(locked))}".encode()
        )
        return await self.get_panel_locked()

    @parse_bool
    async def get_controller_enabled(self) -> Optional[str]:
        """Retrieve controller enabled/disabled state."""
        return await self.request_gauge(access_code=AccessCode.READ, command="CS")

    async def set_controller_enabled(self, enable: bool) -> bool:
        """Enable/disable controller"""
        await self.request_gauge(
            access_code=AccessCode.WRITE, command="CS", data=f"{int(bool(enable))}".encode()
        )
        return await self.get_controller_enabled()

    @parse_int
    async def get_low_pass_filter(self, sensor: Sensor | int) -> Optional[str]:
        """Retrieve low-pass filter value for sensor."""
        _sensor: Sensor = sensor if isinstance(sensor, Sensor) else Sensor.from_int(sensor)
        return await self.request_gauge(
            access_code=AccessCode.READ, command="LF", data=f"{_sensor.value}".encode()
        )

    async def set_low_pass_filter(self, sensor: Sensor | int, lf: int) -> Optional[int]:
        """Set low-pass filter value for sensor."""
        _sensor: Sensor = sensor if isinstance(sensor, Sensor) else Sensor.from_int(sensor)
        await self.request_gauge(
            access_code=AccessCode.WRITE, command="LF", data=f"D{_sensor.value}F{lf}".encode()
        )
        return await self.get_low_pass_filter(sensor)

    async def reset_low_pass_filter(self, sensor: Optional[Sensor | int] = None) -> Optional[int]:
        """Reset low-pass filter to default value."""
        data: Optional[bytes] = None
        if sensor is not None:
            _sensor: Sensor = sensor if isinstance(sensor, Sensor) else Sensor.from_int(sensor)
            data = f"{_sensor.value}".encode()
        await self.request_gauge(access_code=AccessCode.FACTORY_DEFAULT, command="LF", data=data)
        return await self.get_low_pass_filter(sensor)

    async def read_data(self) -> dict:
        """
        Read and return a dictionary of gauge data.

        Currently, retrieves only the pressure value, but can be extended to include
        additional data.

        Returns
        -------
        dict
            A dictionary with at least the key "pressure" mapping to the current pressure value
            (float or None).
        """
        pressure = await self.measure()
        data = {
            "pressure": pressure,
        }
        return data

    async def set_pressure(self, pressure: float) -> Optional[float]:
        """
        Set and return the pressure value.

        Sends the "mv" command with an encoded pressure value and returns the decoded response.


        Parameters
        ----------
        pressure : float
            The pressure value to set in millibars (mbar).

        Returns
        -------
        Optional[float]
            The set pressure value in millibars (mbar), or None if the request fails.
        """
        gauge_data = await self.request_gauge(
            access_code=AccessCode.WRITE, command="mv", data=encode_float(pressure).encode()
        )
        if gauge_data is not None:
            return decode_float(gauge_data)
        return None
