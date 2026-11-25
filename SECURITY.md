# Security policy

## Reporting a vulnerability

Please report security issues through
[GitHub's private vulnerability reporting](https://github.com/The-Smartest-Home/sungrow_sht_sunspec/security/advisories/new)
for this repository. Do not include inverter serial numbers, credentials, or
other private installation details in a public issue.

## Deployment guidance

The add-on uses host networking to reach the inverter and expose SunSpec on the
LAN. The dashboard is served through authenticated Home Assistant ingress and
accepts requests only from the Supervisor proxy. SunSpec is read-only and, by
default, accepts clients only from loopback. Configure `allowed_clients` with
the exact client IPs or trusted LAN CIDRs that need access; never expose the
SunSpec port directly to the internet. Keep the inverter on a trusted network
and use a firewall to limit access to its Modbus TCP port.

The startup wrapper copies the Supervisor options file into `/run`, then
drops privileges before launching the app as a non-root user. Register-map
files are restricted to the bundled `/app/profiles` directory or the add-on's
read-only `/config` mount.
