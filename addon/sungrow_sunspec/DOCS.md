# Sungrow SHx SunSpec bridge

## Setup

Configure the inverter host, Modbus TCP port, unit ID, SunSpec port, allowed
SunSpec client addresses, and register-map file before starting. The bundled
SH25T/SHB profile is community-derived; validate it against your inverter and
firmware before relying on its values.

The add-on exposes:

- The read-only SunSpec Modbus TCP service on port `5020` by default, starting
  at register `40000`.
- The read-only web dashboard through the add-on's **Open Web UI** button.
  Home Assistant ingress handles authentication. It refreshes every five
  seconds and shows inverter power, battery charge, grid flow, model points,
  unavailable values, and the last successful inverter update. Lifetime PV
  generation is shown in kWh; the SunSpec model exposes it in Wh.

To listen on the standard Modbus TCP port `502`, set `sunspec_port` to `502`.
The add-on has only the `NET_BIND_SERVICE` capability needed for its
non-root server process to bind ports below `1024`. If port `502` is already
in use on the Home Assistant host, choose another available port.

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
