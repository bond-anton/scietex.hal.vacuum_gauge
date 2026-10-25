"""
Modbus gateway driver descriptors for vacuum gauges.

These advertise the RS485 V1 protocol bundle to the Modbus gateway through the
``scietex.modbus.drivers`` entry point group. Erstevak gauges share the
Thyracont V1 bundle: the wire protocol is identical, only the vendor differs.
"""

from scietex.hal.serial.gateway.drivers import ModbusDriver

_FRAMER = "scietex.hal.vacuum_gauge.thyracont.rs485.v1.framer.ThyracontASCIIFramer"
_DECODER = "scietex.hal.vacuum_gauge.thyracont.rs485.v1.decoder.ThyracontDecodePDU"
_PDUS = ["scietex.hal.vacuum_gauge.thyracont.rs485.v1.request.ThyracontRequest"]
_TRANSLATOR = "scietex.hal.vacuum_gauge.thyracont.rs485.v1.translator.ThyracontV1Translator"

thyracont_rs485_v1 = ModbusDriver(
    name="thyracont_rs485_v1",
    label="Thyracont RS485 V1",
    description="Thyracont RS485 version 1 vacuum gauge behind the Modbus gateway.",
    device_type="Vacuum Gauge",
    framer=_FRAMER,
    decoder=_DECODER,
    pdus=list(_PDUS),
    translator=_TRANSLATOR,
)

erstevak_rs485_v1 = ModbusDriver(
    name="erstevak_rs485_v1",
    label="Erstevak RS485 V1",
    description="Erstevak RS485 version 1 vacuum gauge; shares the Thyracont V1 bundle.",
    device_type="Vacuum Gauge",
    framer=_FRAMER,
    decoder=_DECODER,
    pdus=list(_PDUS),
    translator=_TRANSLATOR,
)
