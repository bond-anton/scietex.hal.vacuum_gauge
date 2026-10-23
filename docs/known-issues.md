# Known Issues

## 1. `modbus-service.service` holds the serial port exclusively

**Status:** open — to be fixed later.

**Symptom.** With the user systemd quadlet `modbus-service.service` running, the
`pymodbus` backend cannot open the serial port:

```
Failed to connect [Errno 11] Could not exclusively lock port /dev/ttyUSB0:
[Errno 11] Resource temporarily unavailable
```

Every request then returns `None`. The `pyserial` backend is unaffected because
it does not request an exclusive lock.

**Cause.** `modbus-service.service` (a user systemd container running
`/opt/venv/bin/start-modbus-service`) opens `/dev/ttyUSB0` and holds it. The
`pymodbus` backend requests an exclusive lock on the port and fails while the
service owns it.

**Workaround.** Stop the service before talking to the gauge directly:

```bash
systemctl --user stop modbus-service.service
```

Note the service is not disabled: it restarts on next login/boot or when the
USB-serial hotplug path (`modbus-serial-hotplug.path`) fires. To keep it off:

```bash
systemctl --user disable --now modbus-service.service
```

**Fix direction.** Either coordinate port ownership (the service and direct
clients must not both open the port), or make the `pymodbus` backend tolerate a
shared port. Not yet decided.
