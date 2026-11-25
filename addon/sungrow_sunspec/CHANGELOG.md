# Changelog

## [0.3.8]

- Publish container port 5020 on host port 502 through Home Assistant port
  forwarding, without requiring an unsupported Linux capability.

## [0.3.7]

- Remove an unsupported capability declaration so Home Assistant can install
  the add-on; document that the non-root service requires an unprivileged port.

## [0.3.6]

- Allow the non-root SunSpec server to bind the standard Modbus port 502.

## [0.3.5]

- Read available inverter-provided SunSpec Common model values, using register
  map values only as fallbacks.
