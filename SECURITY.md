# Security policy

## Reporting a vulnerability

Please report security issues through
[GitHub's private vulnerability reporting](https://github.com/The-Smartest-Home/sungrow_sht_sunspec/security/advisories/new)
for this repository. Do not include inverter serial numbers, credentials, or
other private installation details in a public issue.

## Deployment guidance

The add-on uses host networking so it can reach the inverter and accept
dashboard and SunSpec clients on the LAN. Both services are read-only and, by
default, accept clients only from loopback. Configure `allowed_clients` with
the exact client IPs or trusted LAN CIDRs needed; never expose either service
directly to the internet. The dashboard uses plain HTTP. Keep the inverter on
a trusted network and use a firewall to limit access to its Modbus TCP port.

The container runs as a non-root user. Register-map files are restricted to
the bundled `/app/profiles` directory or the add-on's read-only `/config`
mount.
