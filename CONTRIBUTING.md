# Contributing

Keep changes small and safe for a real inverter installation. Register-map
changes must cite the Sungrow communication-map document/version and identify
the inverter family and firmware for which they were verified. Do not add
unverified addresses or installation-specific secrets.

Before opening a pull request:

1. Add or update tests for behavior and SunSpec register layout.
2. Run `python -m unittest discover -s tests -v`.
3. Check Home Assistant add-on metadata and ensure documentation reflects any
   option or behavior changes.
4. Review the diff for secrets, unrelated edits, and unsafe Modbus writes.

The bridge is read-only by design. Changes that send writes to the inverter
need explicit product approval and documented safeguards; do not introduce
them as part of a refactor.
