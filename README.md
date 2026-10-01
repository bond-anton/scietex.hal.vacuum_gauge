# scietex.hal.vacuum_gauge

`scietex.hal.vacuum_gauge` is a Python library for interfacing with and emulating vacuum gauges
from various manufacturers, including Edwards, Leybold, and Erstevak. It provides a modular
framework for converting analog voltage outputs to pressure readings and communicating with gauges
over RS485 protocols. The library is designed for use in scientific and industrial applications,
offering both client-side interaction with physical hardware and server-side emulation for testing
and development.

## Features
- **Analog Gauge Support**: Convert voltage outputs to pressure readings (in millibars)
  for Edwards (APG-M, APG-L), Leybold (TTR 101 N), and Erstevak (MTP4D, MTM9D) gauges using 
  interpolation or exponential formulas.
- **RS485 Communication**: Full support for the Thyracont/Erstevak RS485 protocol
  (versions 1 and 2), including client-side control and server-side emulation.
- **Gateway Translators**: `ThyracontV1Translator` and `ThyracontV2Translator` expose
  Thyracont gauges behind `scietex.hal.serial` v2.0.0’s `ModbusGateway`, letting a
  standard Modbus/TCP client talk to a gauge over the vendor RS485 protocol.
- **Modular Design**: Organized into subpackages (`base`, `edwards`, `leybold`,
  `erstevak`, `thyracont`) for easy extension to additional manufacturers or models.
- **Atmospheric Adjustments**: Apply gas-specific correction factors to pressure calculations.
- **Emulation**: Simulate Erstevak gauge behavior for testing without physical hardware.
- **Backends**: Supports `pymodbus` and `pyserial` for flexible RS485 communication.

### Gateway Translators

Both translators are `GatewayTranslator` plugins for `scietex.hal.serial` v2.0.0’s
`ModbusGateway`, so a standard Modbus/TCP client can read and write a Thyracont gauge
through the gateway. The register maps are documented in each module docstring.

- `ThyracontV1Translator` — maps standard Modbus FC03/FC06/FC16 requests to the
  Thyracont RS485 V1 vendor protocol (pressure, setpoints, calibration, Penning state).
  Values are raw integers; 32-bit values span two registers.
- `ThyracontV2Translator` — read-only FC03 mapping to the Thyracont RS485 V2 vendor
  protocol (pressure, operating hours, wear) as IEEE-754 float32 register pairs.
  Every supported read spans exactly two registers.

### Gateway usage

Wire the Thyracont plugin artifacts into a `GatewayConfig` by their installed
dotted paths (`serial_config` is a `scietex.hal.serial` serial connection config):

```python
from scietex.hal.serial.gateway.config import GatewayConfig, GatewayDeviceConfig

config = GatewayConfig(
    serial=serial_config,
    host="127.0.0.1",
    port=5020,
    devices={
        1: GatewayDeviceConfig(
            device_id=1,
            framer="scietex.hal.vacuum_gauge.thyracont.rs485.v1.framer.ThyracontASCIIFramer",
            decoder="scietex.hal.vacuum_gauge.thyracont.rs485.v1.decoder.ThyracontDecodePDU",
            pdus=["scietex.hal.vacuum_gauge.thyracont.rs485.v1.request.ThyracontRequest"],
            translator="scietex.hal.vacuum_gauge.thyracont.rs485.v1.translator.ThyracontV1Translator",
        )
    },
)
```

For a V2 gauge, use the matching `...rs485.v2...` framer, decoder, request, and
`ThyracontV2Translator` paths instead.

## System Requirements

- **Python**: 3.10 or higher.
- **Operating Systems**: Compatible with **Linux** and **macOS**.

## Installation

To install the package, execute the following command in your terminal:

```bash
pip install scietex.hal.vacuum_gauge
```

## Contribution
We welcome contributions to the project! Whether it's bug fixes, feature enhancements,
or documentation improvements, your input is valuable. Please feel free to submit
pull requests or open issues to discuss potential changes.

## License

This project is licensed under the MIT License. For more details, please refer
to the `LICENSE` file included in the repository.
