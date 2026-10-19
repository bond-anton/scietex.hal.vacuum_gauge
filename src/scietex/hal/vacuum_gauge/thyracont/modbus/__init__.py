"""
Thyracont Modbus/TCP Subpackage.

This subpackage provides Modbus/TCP clients for Thyracont vacuum gauges reached
through the Scietex Modbus gateway. The gateway performs the vendor protocol
translation, so these clients speak plain Modbus/TCP.

Modules:
    v1: Client for the Thyracont RS485 V1 register map (read/write).
    v2: Client for the Thyracont RS485 V2 register map (read-only).
"""
