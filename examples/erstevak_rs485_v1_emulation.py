"""Emulation of Erstevak vacuum gauge over serial communication."""

# pylint: disable=duplicate-code
from typing import Optional
import asyncio
import time
import logging

from scietex.hal.serial import VirtualSerialPair
from scietex.hal.serial.config import ModbusSerialConnectionConfig as Config

from scietex.hal.vacuum_gauge.erstevak.rs485.v1 import ErstevakVacuumGauge
from scietex.hal.vacuum_gauge.erstevak.rs485.v1 import ErstevakEmulator


# pylint: disable=too-many-statements
async def main(
    address: int,
    client_con: Config,
    server_con: Config,
    logger: Optional[logging.Logger] = None,
):
    """Main coroutine."""
    emulator = ErstevakEmulator(server_con, logger=logger, address=address)
    await emulator.start()

    gauge = ErstevakVacuumGauge(
        client_con,
        address=address,
        label="Erstevak Emulation",
        logger=logger,
        timeout=2.0,
        backend="pymodbus",
    )

    t1 = time.time()
    model = await gauge.get_model()
    t2 = time.time()
    print(f"GAUGE MODEL: {model}, dt = {(t2 - t1) * 1000} ms")

    t1 = time.time()
    pressure = await gauge.measure()
    t2 = time.time()
    print(f"PRESSURE: {pressure} mbar, dt = {(t2 - t1) * 1000} ms")

    t1 = time.time()
    pressure = await gauge.set_pressure(3.3e-3)
    t2 = time.time()
    print(f"PRESSURE SET: {pressure} mbar, dt = {(t2 - t1) * 1000} ms")

    t1 = time.time()
    pressure = await gauge.measure()
    t2 = time.time()
    print(f"PRESSURE: {pressure} mbar, dt = {(t2 - t1) * 1000} ms")

    t1 = time.time()
    pressure = await gauge.get_setpoint(1)
    t2 = time.time()
    print(f"SP 1: {pressure} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    pressure = await gauge.set_setpoint(1, 5e-2)
    t2 = time.time()
    print(f"SP 1 SET: {pressure} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    pressure = await gauge.get_setpoint(1)
    t2 = time.time()
    print(f"SP 1: {pressure} mbar, dt = {(t2 - t1) * 1000} ms")

    t1 = time.time()
    pressure = await gauge.get_setpoint(2)
    t2 = time.time()
    print(f"SP 2: {pressure} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    pressure = await gauge.set_setpoint(2, 3e-5)
    t2 = time.time()
    print(f"SP 2 SET: {pressure} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    pressure = await gauge.get_setpoint(2)
    t2 = time.time()
    print(f"SP 2: {pressure} mbar, dt = {(t2 - t1) * 1000} ms")

    t1 = time.time()
    cal1 = await gauge.get_calibration(1)
    t2 = time.time()
    print(f"CAL 1: {cal1}, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    cal1 = await gauge.set_calibration(1, 2.3)
    t2 = time.time()
    print(f"CAL 1 SET: {cal1}, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    cal1 = await gauge.get_calibration(1)
    t2 = time.time()
    print(f"CAL 1: {cal1}, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    cal2 = await gauge.get_calibration(2)
    t2 = time.time()
    print(f"CAL 2: {cal2}, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    cal2 = await gauge.set_calibration(2, 0.7)
    t2 = time.time()
    print(f"CAL 2 SET: {cal2}, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    cal2 = await gauge.get_calibration(2)
    t2 = time.time()
    print(f"CAL 2: {cal2}, dt = {(t2 - t1) * 1000} ms")

    t1 = time.time()
    status = await gauge.get_penning_state()
    t2 = time.time()
    print(f"PENNING ON: {status} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    status = await gauge.set_penning_state(True)
    t2 = time.time()
    print(f"PENNING SET: {status} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    status = await gauge.get_penning_state()
    t2 = time.time()
    print(f"PENNING ON: {status} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    status = await gauge.set_penning_state(False)
    t2 = time.time()
    print(f"PENNING SET: {status} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    status = await gauge.get_penning_state()
    t2 = time.time()
    print(f"PENNING ON: {status} mbar, dt = {(t2 - t1) * 1000} ms")

    t1 = time.time()
    status = await gauge.get_penning_sync()
    t2 = time.time()
    print(f"PENNING SYNC: {status} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    status = await gauge.set_penning_sync(False)
    t2 = time.time()
    print(f"PENNING SYNC SET: {status} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    status = await gauge.get_penning_sync()
    t2 = time.time()
    print(f"PENNING SYNC: {status} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    status = await gauge.set_penning_sync(True)
    t2 = time.time()
    print(f"PENNING SYNC SET: {status} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    status = await gauge.get_penning_sync()
    t2 = time.time()
    print(f"PENNING SYNC: {status} mbar, dt = {(t2 - t1) * 1000} ms")

    t1 = time.time()
    pressure = await gauge.set_atmosphere()
    t2 = time.time()
    print(f"SET ATM: {pressure} mbar, dt = {(t2 - t1) * 1000} ms")
    t1 = time.time()
    pressure = await gauge.set_zero()
    t2 = time.time()
    print(f"SET ZERO: {pressure} mbar, dt = {(t2 - t1) * 1000} ms")

    await emulator.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger_console = logging.getLogger()

    vsp = VirtualSerialPair(logger_console)
    vsp.start()

    BAUDRATE = 19200
    TIMEOUT = 0.1
    GAUGE_ADDRESS = 1
    client_config = Config(vsp.serial_ports[0], baudrate=BAUDRATE, timeout=TIMEOUT)
    server_config = Config(vsp.serial_ports[1], baudrate=BAUDRATE, timeout=TIMEOUT)
    asyncio.run(
        main(
            address=GAUGE_ADDRESS,
            client_con=client_config,
            server_con=server_config,
            logger=logger_console,
        )
    )

    vsp.stop()
