# Thyracont RS485 Protocol V1 — Reference

> **Provenance warning.** Unlike V2, the V1 wire format is **not documented in
> any available Thyracont PDF**. The device manuals (`man_vsp_*.pdf`,
> `man_vsm_*.pdf`, `man_vsi_*.pdf`, `man_vsl_*.pdf`, `vsh87d.pdf`) only state
> that V1 is still supported and point to the V2 protocol document. The V2
> document itself contains only a command-comparison table (§8), not the V1
> wire format.
>
> This reference is therefore **reconstructed from the existing implementation**
> in `thyracont/rs485/v1/` and `thyracont/rs485/` (framer, decoder, checksum,
> emulation_utils, data, translator). Treat it as a description of what the
> code does, not as an authoritative vendor specification. Any claim here that
> cannot be traced to a source file is marked *(unverified)*.

V1 is a **command-oriented ASCII protocol**. A request is a single-character
command plus up to six bytes of data; a response is a six-digit decimal string
(the vendor stores every value as a raw integer and formats it with
`f"{value:06d}"`). It is unrelated to Modbus on the wire — the gateway
translator (`v1/translator.py`) maps standard Modbus requests onto V1 commands.

## 1. Frame format

Frames are ASCII, terminated by a carriage return (`CR`, `0x0D`). There is no
start byte. The frame is:

```
<3-digit device id><message><1-byte checksum>CR
```

| Part | Bytes | Description |
| --- | --- | --- |
| Device ID | 0-2 | 3 ASCII digits, zero-padded (`f"{device_id:03d}"`) |
| Message | 3..n | Command + data (see §2) |
| Checksum | n+1 | 1 ASCII char, see §3 |
| CR | n+2 | `0x0D`, mandatory |

Source: `rs485/framer.py` (`ThyracontRS485ASCIIFramer.encode`/`decode`).

The framer's `MIN_SIZE` is 6 bytes for V1 (`v1/framer.py` inherits the base
value; the base class docstring says 4 but the constant is 6). The V2 framer
overrides it to 10.

### 1.1 Message layout

The message (after the 3-digit device ID, before the checksum) is:

```
<command:1 char><data:0..6 bytes>
```

- **Command** — a single case-sensitive ASCII letter. The command's first byte
  becomes the PDU `function_code` (`v1/request.py:102`).
- **Data** — up to 6 bytes, decoded as an ASCII string and truncated to 6
  characters (`v1/request.py:106`, `data` setter at `:115`).

Source: `v1/request.py`, `rs485/decoder.py`.

## 2. Commands

The emulator (`v1/emulation_utils.py:parse_command`) implements the following
commands. `data` is the ASCII payload; the response is the DATA portion of the
reply frame.

| CMD | Direction | Data | Response | Meaning |
| --- | --- | --- | --- | --- |
| `T` | read | — | `MTM09D` | Gauge type |
| `M` | read | — | 6-digit | Current pressure (REG_P) |
| `m` | write | 6-digit | echo | Write pressure (REG_P) |
| `S` | read | `1` or `2` | 6-digit | Read setpoint 1 or 2 |
| `s` | select/write | `1`/`2` then 6-digit | echo | Select setpoint, then write value |
| `C` | read | `1` or `2` | 6-digit | Read calibration 1 or 2 |
| `c` | select/write | `1`/`2` then 6-digit | echo | Select calibration, then write value |
| `I` | read | — | 6-digit | Penning gauge state |
| `i` | write | int | echo | Write Penning gauge state |
| `W` | read | — | 6-digit | Penning synchronization value |
| `w` | write | int | echo | Write Penning synchronization value |
| `j` | adjust | `1`/`0`/6-digit | echo or empty | Atmosphere/zero adjustment |

Source: `v1/emulation_utils.py:147-270`.

### 2.1 Setpoint and calibration: two-step select-then-write

`S`/`s` and `C`/`c` are **stateful across requests**. The select step
(`s`+`1`/`2`, `c`+`1`/`2`) stores a selection flag; the next value write goes
to the selected target and clears the flag. Writing a value without a prior
select writes to whatever was last selected, or silently does nothing if
nothing has been selected since power-on.

The gateway is strictly one-request/one-response, so the translator exposes the
two steps as **two separate registers** (10/11 for setpoints, 12/13 for
calibration); the client issues two consecutive writes. See
`v1/translator.py:57-63`.

### 2.2 Adjustment (`j`)

- `j` + `1` → select atmosphere adjustment (`REG_ATM_SEL = 1`, `REG_ZERO_SEL = 0`).
- `j` + `0` → select zero adjustment (`REG_ZERO_SEL = 1`, `REG_ATM_SEL = 0`).
- `j` + data → apply the selected adjustment. Atmosphere accepts only
  `100023`; zero accepts only `000000` or `000020`. Any other value returns an
  empty response and writes nothing.

Source: `v1/emulation_utils.py:250-269`.

## 3. Checksum

Identical to V2:

```
CS_decimal = (sum of decimal byte values) mod 64 + 64
```

Computed over the device ID **and** the message (excluding the checksum byte
itself). Source: `rs485/checksum.py:calc_checksum`. The V2 document (§2.6)
confirms the formula "has not changed with respect to old protocol".

## 4. Value encoding

### 4.1 Pressure — 6-digit mantissa/exponent

Pressure is encoded as a 6-digit string: 4-digit mantissa + 2-digit exponent
with an offset of **+20**.

```
encode: base = round(mantissa * 1000)   # 4 digits
        exp  = round(exponent + 20)     # 2 digits
        f"{base:04d}{exp:02d}"
```

The mantissa is the value normalized to `[1, 10)` (or 0). Example: 1.23e-3 mbar
→ mantissa 1.23, exponent -3 → `1230` + `17` = `123017`.

The encode offset is **+20** (`v1/data.py:100`) while the decode subtracts
**23** (`v1/data.py:133`). The asymmetry is intentional and compensated by the
mantissa scaling: encode multiplies the normalized mantissa by 1000 (4 digits),
decode multiplies the 4-digit base by `10^exp`. Verified round-trip:

```
1.23e-3 -> 123017 -> 0.00123
973.4   -> 973422 -> 973.4
1.0     -> 100020 -> 1.0
1.2e3   -> 120023 -> 1200.0
```

Source: `v1/data.py:74-136`.

### 4.2 Calibration — scaled integer

Calibration values are scaled by 100 and rounded to an integer:
`_calibration_encode(1.23)` → `"123"`, `_calibration_decode("123")` → `1.23`.
Source: `v1/data.py:139-187`.

### 4.3 Raw register values

The emulator stores values as raw 16-bit registers. A 32-bit value spans two
consecutive registers combined/split by `combine_32bit`/`split_32bit`
(`v1/emulation_utils.py:57-99`). The translator passes register values through
as raw integers and round-trips them through the 6-digit decimal string
(`v1/translator.py:250-265`).

## 5. Register map (emulator internal)

The emulator's register store (`v1/emulation_utils.py:44-54`):

| Register | Name | Width | Purpose |
| --- | --- | --- | --- |
| 0-1 | `REG_P` | 32-bit | Pressure |
| 2-3 | `REG_SP1` | 32-bit | Setpoint 1 |
| 4-5 | `REG_SP2` | 32-bit | Setpoint 2 |
| 6 | `REG_CAL1` | 16-bit | Calibration 1 |
| 7 | `REG_CAL2` | 16-bit | Calibration 2 |
| 8 | `REG_PENNING_STATE` | 16-bit | Penning gauge state |
| 9 | `REG_PENNING_SYNC` | 16-bit | Penning synchronization |
| 10 | `REG_SP_SEL` | 16-bit | Setpoint selection flag |
| 11 | `REG_CAL_SEL` | 16-bit | Calibration selection flag |
| 12 | `REG_ATM_SEL` | 16-bit | Atmosphere adjustment flag |
| 13 | `REG_ZERO_SEL` | 16-bit | Zero adjustment flag |

> **Calibration write bug.** `REG_CAL1` and `REG_CAL2` are declared 16-bit
> (single registers), but the `c` command writes them with `write_two_regs`
> (`v1/emulation_utils.py:235,238`), which writes **two** consecutive
> registers. Writing CAL1 therefore also overwrites CAL2, and writing CAL2
> overwrites `REG_PENNING_STATE`. The read path (`C` command) reads a single
> register, so the corruption is silent. This is a real defect; see the
> repository issue tracker.

## 6. Gateway register map (translator)

The translator (`v1/translator.py:19-46`) exposes the vendor commands as
standard Modbus registers (0-based PDU addresses):

| Address | Read (FC03) | Write (FC06/FC16) |
| --- | --- | --- |
| 0-1 | Pressure ← `M` | Pressure ← `m` + 6-digit (32-bit) |
| 2-3 | SP1 ← `S`+`1` | (read-only) |
| 4-5 | SP2 ← `S`+`2` | (read-only) |
| 6 | CAL1 ← `C`+`1` | (read-only) |
| 7 | CAL2 ← `C`+`2` | (read-only) |
| 8 | Penning ← `I` | Penning state ← `i` + data |
| 9 | Penning ← `W` | Penning sync ← `w` + data |
| 10 | (write-only) | SP select: write 1 or 2 → `s`+`1`/`2` |
| 11 | (write-only) | SP value: write 32-bit → `s` + 6-digit |
| 12 | (write-only) | CAL select: write 1 or 2 → `c`+`1`/`2` |
| 13 | (write-only) | CAL value: write 32-bit → `c` + 6-digit |

The model string (`T` command) is not register-mappable and is out of scope.

## 7. V1 → V2 command mapping

From §8 of the V2 protocol document (the only V1 reference in the PDF):

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

Note the collision: V1 `W`/`w` is *Sensor Transition*, but the emulator uses
`W`/`w` for *Penning synchronization* (`v1/emulation_utils.py:245-249`). The
emulator's `W`/`w` semantics are therefore **not** the V1 sensor-transition
command from the comparison table — they are a package-specific extension
*(unverified against any vendor source)*.

## 8. Known defects in the V1 implementation

1. **Calibration write clobbers adjacent registers** — `c` writes CAL1/CAL2
   with `write_two_regs` although they are 16-bit (§5). Verified: writing CAL1
   sets CAL2 to 0.
2. **`W`/`w` semantics** — emulator uses them for Penning sync, but the V2
   comparison table assigns `W`/`w` to Sensor Transition (§7).
