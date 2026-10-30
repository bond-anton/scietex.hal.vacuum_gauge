"""
Modbus gateway driver descriptors for vacuum gauges.

These advertise the RS485 protocol bundles to the Modbus gateway through the
``scietex.modbus.drivers`` entry point group. Erstevak gauges share the
Thyracont bundles: the wire protocol is identical, only the vendor differs.

V1 and V2 are separate bundles, not versions of one: V2 is a command-oriented
ASCII protocol with a different frame layout, so it needs its own framer,
decoder, PDU and translator. The V2 translator is read-only — it maps FC03
reads onto vendor commands and exposes no writes.
"""

from scietex.hal.serial.gateway.drivers import ModbusDriver

_FRAMER = "scietex.hal.vacuum_gauge.thyracont.rs485.v1.framer.ThyracontASCIIFramer"
_DECODER = "scietex.hal.vacuum_gauge.thyracont.rs485.v1.decoder.ThyracontDecodePDU"
_PDUS = ["scietex.hal.vacuum_gauge.thyracont.rs485.v1.request.ThyracontRequest"]
_TRANSLATOR = "scietex.hal.vacuum_gauge.thyracont.rs485.v1.translator.ThyracontV1Translator"

_V2_FRAMER = "scietex.hal.vacuum_gauge.thyracont.rs485.v2.framer.ThyracontASCIIFramer"
_V2_DECODER = "scietex.hal.vacuum_gauge.thyracont.rs485.v2.decoder.ThyracontDecodePDU"
_V2_PDUS = ["scietex.hal.vacuum_gauge.thyracont.rs485.v2.request.ThyracontRequest"]
_V2_TRANSLATOR = "scietex.hal.vacuum_gauge.thyracont.rs485.v2.translator.ThyracontV2Translator"

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

thyracont_rs485_v2 = ModbusDriver(
    name="thyracont_rs485_v2",
    label="Thyracont RS485 V2",
    description="Thyracont RS485 version 2 vacuum gauge behind the Modbus gateway (read-only).",
    device_type="Vacuum Gauge",
    framer=_V2_FRAMER,
    decoder=_V2_DECODER,
    pdus=list(_V2_PDUS),
    translator=_V2_TRANSLATOR,
)

erstevak_rs485_v2 = ModbusDriver(
    name="erstevak_rs485_v2",
    label="Erstevak RS485 V2",
    description="Erstevak RS485 version 2 vacuum gauge; shares the Thyracont V2 bundle.",
    device_type="Vacuum Gauge",
    framer=_V2_FRAMER,
    decoder=_V2_DECODER,
    pdus=list(_V2_PDUS),
    translator=_V2_TRANSLATOR,
)
