"""Test Erstevak RS485 V2 communication."""

import serial

from scietex.hal.serial.config import ModbusSerialConnectionConfig as Config

if __name__ == "__main__":
    con_params = Config("/dev/cu.usbserial-142310", baudrate=19200, timeout=0.1)
    con = serial.Serial(
        port=con_params.port,
        baudrate=con_params.baudrate,
        bytesize=con_params.bytesize,
        stopbits=con_params.stopbits,
        parity=con_params.parity,
        timeout=con_params.timeout,
        inter_byte_timeout=0.01,
    )
    con.write(b"0010MV00D\r")
    serial_response = con.readline()
    print(f"RESPONSE: {serial_response}")
