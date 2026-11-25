# Changelog

## [0.3.14]

- Make forwarded-read requester details configurable with Debug logging.
- Relay upstream Modbus exception responses to clients without warning-log spam.

## [0.3.13]

- Log the requesting client and register range for forwarded Modbus reads.

## [0.3.12]

- Replace the comma-separated model selection with individual model checkboxes.

## [0.3.11]

- Allow selecting which synthesized SunSpec models are exposed.

## [0.3.10]

- Allow selecting which synthesized SunSpec models are exposed.

## [0.3.9]

- Keep the synthesized SunSpec register block local and proxy other read
  requests to the configured inverter.

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
