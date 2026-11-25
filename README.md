# Sungrow SHx SunSpec Home Assistant add-on

[![Add repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FThe-Smartest-Home%2Fsungrow_sht_sunspec)

This repository contains a Home Assistant add-on that reads configured points
from a Sungrow SH-series inverter over Modbus TCP, serves SunSpec Modbus TCP
models, and provides a live web dashboard. The initial target is an SH25T with
SHB storage.

The add-on provides SunSpec Common (model 1), three-phase inverter (model 103),
storage (model 124), and three-phase meter (model 203) blocks. The meter's
signed real-power point is the grid-flow signal for PV-surplus consumers:
positive means importing from the grid and negative means exporting. A
consumer can treat negative `W` as surplus (`surplus_watts = max(0, -W)`).
This is measured net grid flow, not an estimate of all PV generation; the
Sungrow meter must be connected and its reading available. The SunSpec endpoint
is read-only. The bundled
SH25T profile is derived from the community-maintained
[Sungrow-SHx-Inverter-Modbus-Home-Assistant](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant)
project, not an official Sungrow map, and has not been verified against your
firmware or installation. Its source revision and MIT license are recorded in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). Unmapped SunSpec points
return the SunSpec not-implemented value. See
[`SPECIFICATION.md`](SPECIFICATION.md) for the point-by-point source map,
assumptions, implementation requirements, and validation plan.

## Install in Home Assistant

1. In **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, add this
   repository URL:
   `https://github.com/The-Smartest-Home/sungrow_sht_sunspec`
2. Install **Sungrow SHx SunSpec bridge**.
3. Configure the inverter IP, Modbus TCP port/unit ID, SunSpec port
   (default `5020`), and allowed client IPs/CIDRs, then start the add-on.
4. By default, the bundled community profile is used. To override it, create
   `register_map.json` in the add-on's configuration directory using the schema
   below, then set `register_map_file` to `/config/register_map.json`.
   Compare the profile with the register map applicable to your firmware and
   verify readings before relying on them.
5. Select **Open Web UI** in Home Assistant for the authenticated dashboard.
   Point your SunSpec client at the Home Assistant host on TCP port `5020`,
   starting at holding/input register `40000`.

The dashboard uses Home Assistant ingress for authentication and is reachable
only through the Home Assistant UI. The default `allowed_clients` value permits
only loopback connections to the SunSpec endpoint; set it to the specific
client addresses or trusted CIDRs that need access, for example
`192.168.2.42/32,192.168.2.43/32`. Do not expose the SunSpec endpoint to the
internet. The inverter's Modbus TCP service must be enabled and reachable from
the Home Assistant host.
To use the standard Modbus TCP port, set `sunspec_port` to `502`. The add-on
has only the Linux `NET_BIND_SERVICE` capability needed to bind ports below
`1024`; the default remains `5020`.

The dashboard displays lifetime PV energy in kWh for readability. SunSpec
model 103 exposes the same accumulated energy in Wh, as defined by the model.
For Common model 1, the bridge also tries to read the inverter's SunSpec block
from holding registers starting at 40000 on each poll. Any readable fields
replace the configured Common values; missing fields or an unavailable block
continue to use the register-map values as fallbacks.

## Register-map format

Addresses are zero-based Modbus PDU addresses, not human-formatted
`3xxxx`/`4xxxx` references. Use `register_type: "input"` for function 4 or
`"holding"` for function 3. Multi-register integers use standard big-endian
word order. `scale` converts the raw Sungrow value to engineering units; the
SunSpec scale-factor exponent determines the published value (`engineering
value = SunSpec register value × 10^scale_factor`).

```json
{
  "version": 1,
  "manufacturer": "Sungrow",
  "model": "SH25T",
  "options": "SHB",
  "version_string": "",
  "serial_number": "",
  "device_address": 1,
  "scale_factors": {
    "A_SF": -1,
    "V_SF": -1,
    "W_SF": 0,
    "Hz_SF": -2,
    "WH_SF": 0,
    "Tmp_SF": -1,
    "ChaState_SF": 0
  },
  "fields": {
    "W": {
      "register_type": "input",
      "address": 0,
      "data_type": "int16",
      "scale": 1
    },
    "ChaState": {
      "register_type": "input",
      "address": 0,
      "data_type": "uint16",
      "scale": 1
    }
  }
}
```

The addresses above are placeholders only; replace them with verified addresses
for your device. Supported source types are `uint16`, `int16`, `uint32`, and `int32`.
32-bit source fields may set `"word_order": "swap"` when the low word comes
first; the default is `"big"`.
`scale_factors` may configure the SunSpec
scale-factor points present in models 103 and 124; unspecified factors default
to zero. Any field omitted from `fields` is exposed as not implemented.

Supported mapped SunSpec points:

- **Model 103:** AC and phase currents/voltages, AC power/frequency/apparent
  and reactive power/power factor/energy, DC current/voltage/power,
  temperatures, operating states and event bitfields.
- **Model 124:** storage charge/discharge limits and rates, control mode,
  state of charge, available storage, battery voltage and charge state.

Battery point values are only as complete and accurate as the register profile
provided for the installed inverter. This bridge does not write SunSpec control
points to the inverter.

## Development

Install the pinned Python version and create the local virtual environment:

```sh
uv python install
uv sync
```

Run the unit tests inside the environment with:

```sh
uv run python -m unittest discover -s tests -v
```

See [AGENTS.md](AGENTS.md) for AI-assisted development guidance and
[CONTRIBUTING.md](CONTRIBUTING.md) for contribution checks.
