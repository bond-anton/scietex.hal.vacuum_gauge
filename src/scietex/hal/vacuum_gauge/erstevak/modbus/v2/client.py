"""
Erstevak Modbus/TCP Version 2 Client Module.

Erstevak gauges speak the Thyracont RS485 V2 protocol, so the client is a thin
subclass of `ThyracontModbusV2Gauge` that only changes the default label.

Classes:
    ErstevakModbusV2Gauge: A Modbus/TCP client for Erstevak V2 gauges.
"""

from ....thyracont.modbus.v2.client import ThyracontModbusV2Gauge


class ErstevakModbusV2Gauge(ThyracontModbusV2Gauge):
    """
    Modbus/TCP client for an Erstevak V2 vacuum gauge behind the gateway.

    Attributes:
        label (str): Human-readable gauge label.
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 1,
        label: str = "Erstevak Gauge",
        timeout: float = 1.0,
        logger=None,
    ) -> None:
        """
        Initialize the client.

        Args:
            host: Gateway host name or address.
            port: Gateway TCP port.
            unit_id: Modbus unit id the gateway routes to the gauge.
            label: Human-readable gauge label.
            timeout: Per-request timeout in seconds.
            logger: Optional logger for diagnostics.
        """
        super().__init__(
            host=host,
            port=port,
            unit_id=unit_id,
            label=label,
            timeout=timeout,
            logger=logger,
        )
