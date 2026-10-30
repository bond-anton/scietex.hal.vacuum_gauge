"""
Erstevak RS485 Version 1 Client Module.
"""

from ....thyracont.rs485.v1.client import ThyracontRS485V1Gauge


# pylint: disable=too-many-public-methods
class ErstevakRS485V1Gauge(ThyracontRS485V1Gauge):
    """
    Erstevak vacuum gauge RS485 V1 client.

    Erstevak gauges speak the Thyracont V1 wire protocol unchanged, so this
    subclass only renames the driver. The capability claim is inherited as-is:
    V1 has no per-model capability negotiation, and the Erstevak gauges this
    protocol serves (MTP4D, MTM9D) both expose the same V1 command set.
    """

    display_name = "Erstevak RS485 V1"
