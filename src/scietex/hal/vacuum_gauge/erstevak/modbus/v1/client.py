"""
Erstevak Modbus/TCP Version 1 Client Module.

Erstevak gauges speak the Thyracont RS485 V1 protocol, so the client is a thin
subclass of `ThyracontModbusV1Gauge` that only changes the default label.

Classes:
    ErstevakModbusV1Gauge: A Modbus/TCP client for Erstevak V1 gauges.
"""

from ....thyracont.modbus.v1.client import ThyracontModbusV1Gauge


class ErstevakModbusV1Gauge(ThyracontModbusV1Gauge):
    """
    Modbus/TCP client for an Erstevak V1 vacuum gauge behind the gateway.

    Attributes:
        label (str): Human-readable gauge label.
    """

    display_name = "Erstevak Modbus V1"

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
