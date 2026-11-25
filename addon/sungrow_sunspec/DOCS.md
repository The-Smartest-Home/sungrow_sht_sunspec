# Sungrow SHx SunSpec bridge

## Setup

Configure the inverter host, Modbus TCP port, unit ID, allowed SunSpec client
addresses, and register-map file before starting. The SunSpec service is
exposed on host port `502` by default; change the host port in the add-on's
**Network** settings if desired. The bundled SH25T/SHB profile is
community-derived; validate it against your inverter and firmware before
relying on its values.

The add-on exposes:

- A read-only Modbus TCP proxy on host port `502` by default. The synthesized
  SunSpec block starting at register `40000` is served locally; reads outside
  that block are forwarded to the inverter. For example, Sungrow input register
  `13007` (load power in the cited community map) can be read directly through
  this endpoint. It remains a raw vendor register, not a SunSpec point.
  Change the exposed host port in the add-on's **Network** settings to use a
  different port.
- The read-only web dashboard through the add-on's **Open Web UI** button.
  Home Assistant ingress handles authentication. It refreshes every five
  seconds and shows inverter power, battery charge, grid flow, model points,
  unavailable values, and the last successful inverter update. Lifetime PV
  generation is shown in kWh; the SunSpec model exposes it in Wh.

Configure Modbus clients to connect to the Home Assistant host using the
selected proxy host port and the inverter's configured unit ID. The local
SunSpec register block takes precedence if a request overlaps its addresses;
other addresses are read from the inverter. Modbus write requests remain
rejected.

The `exposed_models` option controls which synthesized SunSpec models are
included in the local register chain. Set it to a comma-separated selection of
`103` (inverter), `124` (storage), and `203` (meter); for example, `103,203`
exposes the inverter and meter models. Common model 1 is always included.
Leave the option empty to expose only Common model 1. The default,
`103,124,203`, preserves the complete model chain.

## Network security

Home Assistant ingress authenticates dashboard requests. The dashboard web
server accepts connections only from the Supervisor proxy at `172.30.32.2`.
The `allowed_clients` option applies only to the SunSpec Modbus endpoint and
defaults to `127.0.0.1/32,::1/128`; remote SunSpec clients are denied until
you configure access. Enter a comma-separated list of trusted IP addresses
or CIDRs, for example `192.168.2.42/32,192.168.2.43/32`. Prefer exact client
addresses and do not expose the SunSpec port to the internet.

The inverter connection is read-only. The add-on does not write to inverter
registers or SunSpec control points.

## Register map

The default profile is `/app/profiles/sh25t_shb.community.json`. To use a
custom profile, place a JSON file in the add-on's configuration directory
(mounted read-only at `/config`) and set `register_map_file` to a path such as
`/config/register_map.json`. Only profile files under `/app/profiles` and
`/config` are accepted.

See the repository's [`SPECIFICATION.md`](../../SPECIFICATION.md) for the
mapping, assumptions, and hardware validation requirements. Source attribution
and third-party license information are recorded in
[`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md).

## Troubleshooting

- Confirm the inverter's Modbus TCP service is enabled and reachable from the
  Home Assistant host.
- If SunSpec clients cannot connect, check `allowed_clients`, the selected
  port, and firewall rules on the Home Assistant host and LAN.
- If values show as unavailable, inspect the add-on log and verify that the
  configured profile matches the inverter and meter installation.

## License

This add-on is distributed under the repository license. The bundled
community-derived profile and other third-party material are subject to the
notices in `THIRD_PARTY_NOTICES.md`.
