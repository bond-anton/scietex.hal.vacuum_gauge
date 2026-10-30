"""
Erstevak RS485 Version 2 Client Module.
"""

from ....base.capabilities import (
    CalibrationCapabilities,
    DisplayCapabilities,
    GaugeCapabilities,
    PenningCapabilities,
    RelayCapabilities,
)
from ....thyracont.rs485.v2.client import ThyracontRS485V2Gauge


# pylint: disable=too-many-public-methods
class ErstevakRS485V2Gauge(ThyracontRS485V2Gauge):
    """
    Erstevak vacuum gauge RS485 V2 client.

    Erstevak gauges speak the Thyracont V2 wire protocol unchanged, so the
    command surface is inherited. The capability claim is not: the Thyracont
    claim describes a full-featured gauge with a cold cathode, a hot-cathode
    filament and a degas cycle, and the Erstevak gauges this driver serves are
    single-sensor Pirani instruments.

    The claim below is the MTP4D surface. It is deliberately narrower than the
    inherited one: a caller that gates on ``capabilities`` must not be told the
    gauge can degas or drive a filament it does not have.

    Attributes:
        capabilities (GaugeCapabilities): The MTP4D control surface.
    """

    capabilities = GaugeCapabilities(
        # A Pirani gauge has no cold cathode, so neither the Penning state nor
        # its sync flag is writable.
        penning=PenningCapabilities(state=False, sync=False),
        relay=RelayCapabilities(
            count=2,
            modes=("pressure", "T0", "T1", "E", "U", "O", "C", "W"),
            hysteresis=True,
        ),
        calibration=CalibrationCapabilities(high=True, low=True),
        display=DisplayCapabilities(units=True, orientation=True, data_source=True),
        # No hot cathode: no degas cycle and no filament control.
        degas=False,
        gas_correction=True,
        panel_lock=True,
        controller=True,
        filter=True,
        digital_logic=True,
        reset=True,
    )

    display_name = "Erstevak RS485 V2"
