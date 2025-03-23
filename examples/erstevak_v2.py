"""Test Erstevak RS485 V2 communication."""

# pylint: disable=duplicate-code

from typing import Optional
import asyncio
import logging

from scietex.hal.serial.config import ModbusSerialConnectionConfig as Config

# from scietex.hal.vacuum_gauge.erstevak.rs485.v2.request import ErstevakRequest, AccessCode
# from scietex.hal.vacuum_gauge.erstevak.rs485.v2.decoder import ErstevakDecodePDU
# from scietex.hal.vacuum_gauge.erstevak.rs485.v2.framer import ErstevakASCIIFramer
from scietex.hal.vacuum_gauge.erstevak.rs485.v2 import (
    ErstevakVacuumGauge,
    Sensor,
    DisplayUnits,
)


# pylint: disable=too-many-locals,too-many-statements
async def main(address: int, client_con: Config, logger: Optional[logging.Logger] = None):
    """Main function."""
    gauge = ErstevakVacuumGauge(
        address=address,
        connection_config=client_con,
        logger=logger,
        # backend="pyserial",
        backend="pymodbus",
    )
    # Gauge information
    # print("=" * 20 + "\nGAUGE INFO\n" + "=" * 20)
    # dt = await gauge.get_model()
    # print(f"Model: {dt}")
    # pn = await gauge.get_product_name()
    # print(f"Product Name: {pn}")
    # sd = await gauge.get_device_sn()
    # print(f"Serial Number [DEVICE]: {sd}")
    # sh = await gauge.get_head_sn()
    # print(f"Serial Number [HEAD]: {sh}")
    # print("=" * 20 + "\n")

    # print("=" * 20 + "\nPRESSURE MEASUREMENT\n" + "=" * 20)
    # mr = await gauge.get_measurement_range()
    # print(f"Measurement range: {mr} mbar")
    # lf = await gauge.get_low_pass_filter(Sensor.PIRANI)
    # print(f"Low pass filter: {lf}%")
    # p = await gauge.measure(sensor=Sensor.AUTO)
    # print(f"Pressure: {p} mbar.")
    # lf = await gauge.set_low_pass_filter(Sensor.PIRANI, 100)
    # print(f"Low pass filter: {lf}%")
    # p = await gauge.measure(sensor=Sensor.AUTO)
    # print(f"Pressure: {p} mbar.")
    # lf = await gauge.reset_low_pass_filter(Sensor.PIRANI)
    # print(f"Low pass filter: {lf}%")
    # print("=" * 20 + "\n")

    # Temperature measurement is available for some gauges
    # print("=" * 20 + "\nTEMPERATURE MEASUREMENT\n" + "=" * 20)
    # t = await gauge.get_temperature(Sensor.PIEZO)
    # print(f"T: {t}")
    # print("=" * 20 + "\n")

    # print("=" * 20 + "\nRELAY OPERATION\n" + "=" * 20)
    # rl_n = 1
    # rl1 = await gauge.get_relay(rl_n)
    # rl1["on"] = 0.06
    # print(f"RL {rl_n}: {rl1}")
    # rl1 = await gauge.set_relay(rl_n, rl1)
    # print(f"RL {rl_n}: {rl1}")
    # rl1 = await gauge.reset_relay(rl_n)
    # print(f"RL {rl_n}: {rl1}")
    # print("=" * 20 + "\n")

    # Display functions
    print("=" * 20 + "\nDISPLAY OPERATION\n" + "=" * 20)
    du = await gauge.get_display_units()
    print(f"Display units: {du}")
    await gauge.set_display_units(DisplayUnits.HPA)
    await gauge.reset_display_units()
    do = await gauge.get_display_orientation()
    print(f"Display orientation: {do}")
    do = await gauge.rotate_display()
    print(f"Display orientation: {do}")
    do = await gauge.reset_display_orientation()
    print(f"Display orientation: {do}")

    dd = await gauge.get_display_data_source()
    print(f"Display data source: {dd}")
    print("=" * 20 + "\n")

    # Gauge Calibration Be careful
    # print("=" * 20 + "\nGAUGE CALIBRATION\n" + "=" * 20)
    # await gauge.adjust_high()
    # await gauge.adjust_low()
    # print("=" * 20 + "\n")

    # Gauge output characteristics
    # print("=" * 20 + "\nGAUGE OUTPUT\n" + "=" * 20)
    # oc = await gauge.get_output_characteristic()
    # print(f"Gauge output characteristics: {oc}")
    #
    # print("Setting Interpolation Table for Gauge output.")
    # oc = {"mode": "Tab", "size": 2, "under_range": 0.0, "over_range": 10.5, "fault": 0.4}
    # nodes = [
    #     {"mode": "Tab", "node": 1, "pressure": 1.0, "voltage": 1.0},
    #     {"mode": "Tab", "node": 2, "pressure": 5.0, "voltage": 5.0},
    # ]
    # oc, nodes = await gauge.set_tab_output_characteristic(oc, nodes)
    #
    # print(f"Gauge output characteristics: {oc}")
    # print(nodes)
    #
    # oc = await gauge.reset_output_characteristic()
    # print(f"Gauge output characteristics: {oc}")
    # print("=" * 20 + "\n")

    # Gauge restart
    print("=" * 20 + "\nGAUGE RESTART\n" + "=" * 20)
    result = await gauge.restart_gauge()
    print(f"RESTART SUCCESS: {result}")
    print("=" * 20 + "\n")

    # Gauge statistics
    print("=" * 20 + "\nGAUGE STATISTICS\n" + "=" * 20)
    oh = await gauge.get_operating_hours()
    print(f"Gauge operation statistics: {oh}")
    for i in (0, 1, 2, 3, 4, 6, 7):
        pm = await gauge.get_sensor_statistics(i)
        # pm = await gauge.get_sensor_statistics(Sensor.COLD_CATHODE)
        print(f"{Sensor(i)} Gauge wear statistics: {pm}")
    print("=" * 20 + "\n")

    # Communication parameters
    print("=" * 20 + "\nGAUGE COMMUNICATION\n" + "=" * 20)
    rd = await gauge.get_response_delay()
    print(f"RESPONSE DELAY: {rd} us")
    print("=" * 20 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger_console = logging.getLogger()

    # # b"0010MV00D\r"
    # DATA = None
    # # DATA = b"1.2e-3"
    # req = ErstevakRequest(AccessCode.READ, command="MV", data=DATA, slave=2)
    # encoded = req.encode()
    # print(f"REQUEST: {req.encode(), req.function_code, req.rtu_frame_size}")
    # req.decode(encoded)
    # print(req.data, req.function_code, req.command, req.rtu_frame_size)
    #
    # framer = ErstevakASCIIFramer(ErstevakDecodePDU(is_server=False))
    # frame_encoded = framer.encode(data=req.encode(), device_id=req.dev_id, _tid=0)
    # print(f"Encoded frame: {frame_encoded}")
    # print(f"Encoded frame: {framer.buildFrame(req)}")
    # print(f"Decoded frame: {framer.decode(frame_encoded)}")
    #
    # print("=====================")

    client_config = Config("/dev/cu.usbserial-142330", baudrate=115200, timeout=0.1)
    asyncio.run(main(address=2, client_con=client_config, logger=logger_console))
