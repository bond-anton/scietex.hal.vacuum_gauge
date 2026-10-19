"""
Erstevak Modbus/TCP Subpackage.

Erstevak gauges speak the Thyracont RS485 protocol, so the Modbus/TCP clients
are thin subclasses of the Thyracont ones.

Modules:
    v1: Client for the Erstevak RS485 V1 register map (read/write).
    v2: Client for the Erstevak RS485 V2 register map (read-only).
"""
