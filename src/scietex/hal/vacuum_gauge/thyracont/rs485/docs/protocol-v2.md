# Thyracont RS485 Protocol V2 — Reference

Authoritative source: *Thyracont Communication Protocol*, version 2.1.9
(2023-02-22, Stefan Junge / M. Nussbaum), 38 pages. This document is a
condensed reference for the subset of V2 implemented in
`thyracont/rs485/v2/`. Where this file and the PDF disagree, the PDF wins.

V2 is a **command-oriented ASCII protocol**, not a register protocol. A request
carries a two-character command and optional data; the response carries an
ASCII data string. It is unrelated to Modbus on the wire — the gateway
translator (`v2/translator.py`) maps standard Modbus FC03 reads onto V2
commands.

## 1. Frame format

Every frame is ASCII, terminated by a mandatory carriage return (`CR`, `0x0D`).
There is no start byte.

Package **without** data (read request, or a response with no data):

```
byte:  0   1   2   3    4   5   6   7   8   9
       ADR       AC   CMD       LEN   CS  CR
```

Package **with** data:

```
byte:  0   1   2   3    4   5   6   7   8  ...  n   n+1  n+2
       ADR       AC   CMD       LEN      DATA     CS   CR
```

| Part | Bytes (with data) | Bytes (without data) | Description |
| --- | --- | --- | --- |
| Address (ADR) | 0-2 | 0-2 | 3 ASCII digits, zero-padded |
| Access Code (AC) | 3 | 3 | 1 ASCII digit, access type |
| Command (CMD) | 4-5 | 4-5 | 2 case-sensitive ASCII letters |
| Length (LEN) | 6-7 | 6-7 | 2 ASCII digits, byte count of DATA |
| Data (DATA) | 8-n | — | ASCII payload |
| Checksum (CS) | n+1 | 8 | 1 ASCII char, see §3 |
| Carriage Return (CR) | n+2 | 9 | `0x0D`, mandatory |

### 1.1 Address (ADR)

Three ASCII digits. `001` = RS232/USB; `001`-`016` = RS485; `100` = VD12 (USB).

### 1.2 Length (LEN)

Two ASCII digits, zero-padded to the left. `00` when there is no data. The
length counts DATA bytes only, not the whole frame.

## 2. Access codes (AC)

The AC differs between send (master → transmitter) and receive
(transmitter → master). On success the transmitter **increments** the send AC
by one: a read sent with `0` is answered with `1`; a write sent with `2` is
answered with `3`; a factory-default sent with `4` is answered with `5`.

| Type of access | Send (master → transmitter) | Receive (transmitter → master) |
| --- | --- | --- |
| Read | 0 | 1 |
| Write | 2 | 3 |
| Factory Default | 4 | 5 |
| Streaming Mode Response | — | 6 |
| Error | — | 7 |
| Binary | 8 | 9 |

On any error the transmitter answers with AC `7` and an error code as DATA
(see §5). Binary mode is used for firmware update; when using it, LEN is also
binary (2 bytes).

> **Conformance note.** AC `6` is reserved for *streaming-mode* responses
> only. A normal read response must carry AC `1`, and a normal write response
> AC `3`. The `AccessCode` enum in `v2/data.py` defines only the send codes
> (`READ=0`, `WRITE=2`, `FACTORY_DEFAULT=4`, `BINARY=8`) plus the receive codes
> `STREAMING=6` and `ERROR=7`; it omits the receive codes `1`, `3`, `5`, `9`.
> As a result the emulator (`v2/request.py:195`) answers every successful
> command with AC `6`. Verified: a read `MV` returns AC `6`, not `1`. The
> client (`v2/client.py:213`) only special-cases AC `7`, so it tolerates the
> wrong code — the defect only surfaces against real hardware or a strict
> conformance test.

## 3. Checksum (CS)

The formula is unchanged from V1:

```
CS_decimal = (sum of decimal byte values) mod 64 + 64
```

The checksum is computed over bytes `0..7` for a package without data, and
over bytes `0..n` (i.e. including DATA) for a package with data. The resulting
decimal number is converted back to its ASCII character.

Worked example — read Measurement Value (`MV`) at address 1:

```
frame:  0  0  1  0  M  V  0  0  ?  CR
ASCII: 48 48 49 48 77 86 48 48
sum = 48+48+49+48+77+86+48+48 = 452
CS  = (452 mod 64) + 64 = 4 + 64 = 68 -> ASCII "D"
```

Resulting frame: `0010MV00D\r`.

## 4. Data source selector

Some commands accept a data-source selector as DATA. Values:

| Sensor type | Value |
| --- | --- |
| Absolute pressure (combination) | 0 (default) |
| Pirani | 1 |
| Piezo | 2 |
| Hot cathode | 3 |
| Cold cathode | 4 |
| Ambient pressure | 6 |
| Relative pressure | 7 |
| Temperature, piezo sensor | `T2` |

## 5. Error codes

An error response carries AC `7` and one of the following DATA strings:

| Code | Meaning |
| --- | --- |
| `NO_DEF` | Command is not valid (not defined) for the device |
| `_LOGIC` | Access code invalid, or command execution not logical |
| `_RANGE` | Value in the send request is out of range |
| `ERROR1` | Sensor is defective or stacked out |
| `SYNTAX` | Command valid, but data syntax or selected mode invalid |
| `LENGTH` | Command valid, but data length out of expected range |
| `_CD_RE` | Calibration data read error |
| `_EP_RE` | EEPROM read error |
| `_UNSUP` | Unsupported data (not a valid value) |
| `_SEDIS` | Sensor element disabled |

## 6. Commands implemented in this package

The table lists the commands the emulator (`v2/emulation_utils.py`) and the
gateway translator (`v2/translator.py`) support. `AC` is the send access code.

| CMD | AC | Send DATA | Receive DATA | Meaning |
| --- | --- | --- | --- | --- |
| `MV` | 0 | — | float / `OR` / `UR` | Measurement value, pressure [mbar] |
| `M0`-`M4` | 0 | — | float / `OR` / `UR` | Measurement value by sensor (M1 Pirani, M2 Piezo, M3 hot cathode, M4 cold cathode) |
| `OH` | 0 | — | `int` or `intCint` | Operating hours, 15-minute units; `C` separates device and cathode |
| `PM` | 0 | `1` | `W[int]A[int]` | Pirani sensor statistics: wear [%] and time since zero adjustment (15-min units) |
| `TD` | 0 | — | string | Type of device |
| `PN` | 0 | — | string | Product name |
| `SD` | 0 | — | string | Serial number, device |
| `SH` | 0 | — | string | Serial number, sensor head |
| `VD` | 0 | — | string | Version, device |
| `VF` | 0 | — | string | Version, firmware |
| `VB` | 0 | — | string | Version, bootloader |
| `MR` | 0 | — | `H[float]L[float]` | Measurement range: high and low limits [mbar] |

### 6.1 Measurement value (`MV`, `M1`-`M4`)

Read-only. Response DATA is a float in mbar, or the literal `OR` (overrange)
or `UR` (underrange). Example: pressure 973.4 mbar is sent as `9.734e2`.

### 6.2 Operating hours (`OH`)

Read-only. Response is an integer count of 15-minute intervals. Devices with a
cathode append `C` and a second integer: `42C36` means 42/4 = 10.5 h device and
36/4 = 9 h cathode.

### 6.3 Sensor statistics (`PM`)

Read-only. Send DATA selects the sensor: `1` Pirani, `3` hot cathode, `4` cold
cathode. Pirani response is `W[int]A[int]`:

- `W` = estimated wear in percent. Negative = corrosion, positive =
  contamination, `32767` = not calculated yet.
- `A` = time since last zero adjustment, in 15-minute intervals.

Factory-default (`AC` 4) with DATA `1` resets the Pirani wear value to 0.

### 6.4 Measurement range (`MR`)

Read-only. Response is `H[float]L[float]`, e.g. `H1.2e3L1e-4` for a range of
1.2e3 down to 1e-4 mbar.

## 7. Float encoding

V2 transmits measurement values as ASCII floats, not as fixed-point integers.
The helper `encode_float` in `v2/data.py` formats with `f"{value:1.3e}"` and
strips the exponent's leading zeros (e.g. `9.734e2`). `decode_float` maps the
literals `OR` → `999999.0` and `UR` → `0.0`, and otherwise parses the float.

## 8. V1 → V2 command mapping (informative)

Section 8 of the PDF compares the old (V1) and new (V2) command sets. This is
the only V1 reference in the document; the V1 wire format itself is not
specified there.

| Old (V1) | New (V2) | Data compatible | Notes |
| --- | --- | --- | --- |
| Type (`T`) | Type of Device (`TD`) | Yes | |
| Measurement (`M`) | Measurement Value (`MV`) | No | V1: 6-byte fixed, coded; V2: float |
| Setpoint (`S`,`s`), Hysteresis (`H`,`h`), Parameter Set (`P`,`p`) | Relay 1-4 (`R1`-`R4`) | No | Complete overhaul |
| Correction Factor (`C`,`c`) | Gas Correction Factor 1,3,4 (`C1`,`C3`,`C4`) | No | V1: integer ×100; V2: float |
| Adjustment (`j`) | Adjust High/Low (`AH`,`AL`) | No | Complete overhaul |
| Start/Stop Control (`A`,`a`) | Controller Status (`CS`) | Yes | |
| Lock Keyboard (`K`,`k`) | Panel Status (`PS`) | Yes | |
| Degas (`D`,`d`) | Degas (`DG`) | Yes | |
| Filament Number (`F`) | Filament Number (`FN`) | No | V1: 0/1; V2: 1/2 |
| Sensor Transition (`W`,`w`) | Sensor Transition (`ST`) | Partly | Complete overhaul |
| Cold Cathode (`I`,`i`) | Cathode Control (`CC`) | Yes | |
| Display Unit (`U`,`u`) | Display Unit (`DU`) | No | Complete overhaul |

## 9. Streaming mode (informative)

`SM` (write, AC 2) enables automatic transmission. Modes: `1` V1 style, `2` V2
style, `3` V1 frameless, `4` V2 frameless. Streaming responses use AC `6`.
Requires at least 38400 baud. Only one transmitter on a shared bus may stream
at a time. This package does not implement streaming.
