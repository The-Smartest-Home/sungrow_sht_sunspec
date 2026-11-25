# Changelog

Notable changes to this project are documented here.

## [0.3.5]

- Read available inverter-provided SunSpec Common model values, using register
  map values only as fallbacks.

## [0.3.4]

- Display SunSpec scale factors as readable multipliers with descriptive labels.

## [0.3.3]

- Refresh the add-on icon and logo with a cleaner, consistent visual design.
- Ignore JetBrains `.idea/` project files.
- Map cumulative grid import and export energy into SunSpec model 203.

## [0.3.2]

- Display lifetime PV generation in kWh on the dashboard while retaining Wh in
  SunSpec model 103.

## [0.3.1]

- Prevent long dashboard point labels and values from overlapping.

## [0.3.0]

- Serve the dashboard through authenticated Home Assistant ingress.
- Read add-on options safely before dropping privileges to the non-root app user.
