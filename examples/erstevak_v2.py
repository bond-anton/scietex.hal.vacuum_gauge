"""Test Erstevak RS485 V2 communication."""

try:
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v2.request import ErstevakRequest, AccessCode
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v2.decoder import ErstevakDecodePDU
    from src.scietex.hal.vacuum_gauge.erstevak.rs485.v2.framer import ErstevakASCIIFramer
except ModuleNotFoundError:
    from scietex.hal.vacuum_gauge.erstevak.rs485.v2.request import ErstevakRequest, AccessCode
    from scietex.hal.vacuum_gauge.erstevak.rs485.v2.decoder import ErstevakDecodePDU
    from scietex.hal.vacuum_gauge.erstevak.rs485.v2.framer import ErstevakASCIIFramer


if __name__ == "__main__":
    # b"0010MV00D\r"
    DATA = None
    # DATA = b"1.2e-3"
    req = ErstevakRequest(AccessCode.READ, command="MV", data=DATA)
    encoded = req.encode()
    print(f"REQUEST: {req.encode(), req.function_code, req.rtu_frame_size}")
    req.decode(encoded)
    print(req.data, req.function_code, req.command, req.rtu_frame_size)

    framer = ErstevakASCIIFramer(ErstevakDecodePDU(is_server=False))
    frame_encoded = framer.encode(data=req.encode(), device_id=req.dev_id, _tid=0)
    print(frame_encoded)
    print(framer.decode(frame_encoded))
