# Sungrow SH25T SunSpec bridge: requirements and validation

## Purpose and scope

The add-on reads measurements from a Sungrow SH25T hybrid inverter with an SHB
battery over Modbus TCP and serves them as SunSpec Modbus TCP. Its current
profile is community-derived and is a starting point for field validation,
not a claim of official Sungrow certification. No control writes to the
inverter are in scope.

## Sources and evidence

The initial register profile is derived from
[Sungrow-SHx-Inverter-Modbus-Home-Assistant](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant),
by mkaiser, MIT-licensed. Exact provenance and the required MIT notice are in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md); the JSON profile contains
the upstream revision and source file. That project recognizes SH25T (device
type code `0x0E28`) and documents three MPPTs for SH*T models. Its shared
register map is community-maintained and measurements may depend on inverter
and firmware revision.

No registers are inferred from register-number adjacency. The initial mapping
below transcribes explicit source definitions in upstream `modbus_sungrow.yaml`
at revision `071f8c8c5f784198928f80de23ae168eed1acd1d`.

## Functional requirements

1. Connect as a Modbus TCP client using the configured inverter host, port, and
   unit ID. Poll only configured source registers, at the configured interval.
2. Read input registers with function 4 and holding registers with function 3;
   decode signed/unsigned 16/32-bit values and configurable 32-bit word order.
3. Apply source engineering-unit scale before encoding each SunSpec point.
   Apply each SunSpec scale factor exactly once: published engineering value
   equals encoded point multiplied by `10 ** scale_factor`.
4. Serve SunSpec signature `SunS`, Common model 1, three-phase inverter model
   103, storage model 124, three-phase wye meter model 203, then the end marker
   `0xFFFF`, starting at holding register 40000. Keep model IDs, field order,
   field widths and N/I sentinels consistent with SunSpec definitions.
5. In model 203, preserve signed net grid power: positive means importing from
   grid, negative means exporting. Consumers may compute surplus as
   `max(0, -W)`; do not reverse the value or conflate it with inverter PV
   generation. A missing/unavailable Sungrow meter value must be N/I.
6. Serve both holding- and input-register reads from the same SunSpec address
   map. Reject every Modbus write request. Report absent/unavailable points as
   the correct type-specific SunSpec not-implemented value, not as zero.
7. On inverter read/connect/timeout failure, log the failure and replace
   telemetry points with not-implemented sentinels. Do not retain stale values
   as if they were fresh.
8. Keep profiles configurable and preserve source attribution. Never represent
   the community profile as official or proven on a specific installation.
9. Provide a read-only HTTP dashboard for the same live values served over
   SunSpec. Present inverter power, battery charge, signed grid power, model
   points, availability, and last successful poll without retaining stale
   values after a failed poll.
10. Restrict HTTP and SunSpec clients using the same configurable IP/CIDR
    policy. The dashboard must use Home Assistant ingress and accept requests
    only from the Supervisor proxy; SunSpec defaults to loopback and uses the
    configurable IP/CIDR allowlist. Both listeners must bound idle request
    time.

## Initial point mapping

Source addresses below are zero-based Modbus PDU input-register addresses.
`swap` means the low 16-bit word precedes the high word, as configured by the
upstream profile's `swap: word`. Source scale converts raw register values to
the target SunSpec engineering unit.

| SunSpec model/point | Community source point | Address | Source type/order | Source scale | SunSpec SF |
|---|---|---:|---|---:|---:|
| 103 `AphA` | Phase A current | 13030 | int16 | 0.1 A | -1 |
| 103 `AphB` | Phase B current | 13031 | int16 | 0.1 A | -1 |
| 103 `AphC` | Phase C current | 13032 | int16 | 0.1 A | -1 |
| 103 `PhVphA` | Phase A voltage | 5018 | uint16 | 0.1 V | -1 |
| 103 `PhVphB` | Phase B voltage | 5019 | uint16 | 0.1 V | -1 |
| 103 `PhVphC` | Phase C voltage | 5020 | uint16 | 0.1 V | -1 |
| 103 `W` | Total active power | 13033 | int32, swap | 1 W | 0 |
| 103 `Hz` | Grid frequency | 5241 | uint16 | 0.01 Hz | -2 |
| 103 `VAr` | Reactive power | 5032 | int32, swap | 1 (provisional var) | 0 |
| 103 `PF` | Power factor (ratio) | 5034 | int16 | 0.1 (ratio to %) | -2 |
| 103 `WH` | Total PV generation | 13002 | uint32, swap | 100 Wh/raw | 0 |
| 103 `DCW` | Total DC power | 5016 | uint32, swap | 1 W | 0 |
| 103 `TmpSnk` | Inverter temperature | 5007 | int16 | 0.1 °C | -1 |
| 103 `StVnd` | Running state raw | 12999 | uint16 | 1 | N/A |
| 124 `ChaState` | Battery level | 13022 | uint16 | 0.1% | -1 |
| 124 `InBatV` | Battery voltage | 13019 | uint16 | 0.1 V | -1 |
| 203 `W` | Meter active power (net grid flow) | 5600 | int32, swap | 1 W | 0 |
| 203 `WphA` | Meter phase A active power | 5602 | int32, swap | 1 W | 0 |
| 203 `WphB` | Meter phase B active power | 5604 | int32, swap | 1 W | 0 |
| 203 `WphC` | Meter phase C active power | 5606 | int32, swap | 1 W | 0 |
| 203 `TotWhImp` | Total grid import energy | 13036 | uint32, swap | 100 Wh/raw | 0 |
| 203 `TotWhExp` | Total grid export energy | 13045 | uint32, swap | 100 Wh/raw | 0 |

The `WH` source is the upstream lifetime PV generation counter; it is not
asserted to be an exact inverter AC output-energy counter. `TmpSnk` is a proxy
for the community “Inverter temperature” reading. `PF` is transformed from a
ratio into SunSpec percent. The upstream profile names register 5033 “Reactive
power” but declares its unit as W; the SunSpec VAr mapping is provisional and
must be checked against Sungrow documentation and hardware. These semantic
mappings require validation before being treated as interoperable measurements.
The upstream community map documents meter active power as valid only when the
inverter is directly connected to its energy meter, with positive values for
grid import and negative values for grid export. It marks raw `0x7FFFFFFF` as
unavailable; this profile maps that value to SunSpec N/I. If the meter is not
connected or values remain unavailable, model 203 still exists but its `W`
point is N/I, so a client must not interpret it as zero export.

Other fields remain SunSpec not-implemented until a documented source and
meaning are validated. In particular, do not synthesize AC total current,
DC aggregate voltage/current, standard inverter state, battery charge status,
or writable storage controls from unrelated values.

## Safety and failure requirements

- The SunSpec endpoint is read-only, even for model 124 points defined as
  writable by SunSpec.
- The dashboard is read-only, authenticated through Home Assistant ingress,
  and only accepts connections from the Supervisor proxy. It uses relative
  resource URLs and respects the forwarded ingress path.
- Do not write to inverter registers; do not enable public exposure of the
  dashboard or SunSpec endpoint. Restrict network reachability to trusted LAN
  clients. Home Assistant ingress handles dashboard authentication; the
  SunSpec endpoint is limited by the configured client allowlist.
- A source field can be absent, unsupported, or invalid. Keep it not
  implemented and log actionable upstream errors; never substitute zero.
- Verify address, register type, signedness, word order, scale, unit, sentinel
  and model semantic independently. A syntactically valid profile is not proof
  that a given inverter returns the expected value.

## Validation plan / acceptance criteria

### Automated offline checks

- Verify profile JSON provenance fields, allowed point names, address ranges,
  source width, source type, word order and finite scales.
- Use synthetic Modbus responses to assert 16/32-bit signed and unsigned
  decoding, swapped word decoding, contiguous read grouping, Modbus exception
  handling and timeout behavior.
- Assert SunSpec signature, common model length and identity strings, model
  IDs, exact model lengths/offsets, correct N/I sentinels, high/low word order,
  scale-factor application, end marker, and read-only exception responses.
- Use known vectors for each profile mapping, including negative active/reactive
  power, phase measurements, frequency, PF, cumulative energy, battery SOC,
  battery voltage, and temperature.
- Run `python -m unittest discover -s tests -v`, compile all Python modules,
  validate add-on metadata and build the container image.

### Hardware verification before relying on readings

1. Record SH25T model identity, SHB model/firmware, inverter firmware, datalogger
   type/firmware, unit ID and the community profile revision used. Do not
   publish serial numbers or site-specific network details.
2. Confirm Modbus read-only access and each raw register directly against the
   inverter using the correct function code and documented address base.
3. Compare raw values to the Home Assistant/community sensor and an independent
   display/meter under stable conditions. Check sign conventions during both
   charge and discharge, and test low/near-zero as well as non-zero values.
4. Check 32-bit word order with a non-zero measurement and confirm scaling and
   units across at least two operating states.
5. Connect an independent SunSpec client. Confirm model discovery, point
   values, N/I behavior, scale factors and read-only behavior.
6. Exercise inverter disconnect/reconnect, malformed upstream response,
   missing-point profile, and server client disconnect; confirm no stale
   telemetry is presented as current.
7. Record results and any firmware-specific deviations in profile metadata,
   tests and documentation. Promote mappings to verified only with reproducible
   evidence and review.

## Extension requirements

New points or device profiles must include: source project/document and exact
revision, model/firmware applicability, source PDU address and function,
register width/type/signedness/word order, units and transformation, target
SunSpec point/model and scale factor, expected N/I behavior, a test vector,
and provenance attribution. Prefer a new named profile over silently changing
the meaning of the default profile. Official/vendor-derived tables must only
be redistributed when their license permits it.
