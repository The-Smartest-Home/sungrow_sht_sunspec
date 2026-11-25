"""Home Assistant add-on entry point for the Sungrow SunSpec bridge."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from pathlib import Path
from typing import Any

from modbus import ModbusClient, SunSpecServer, read_mapped_fields
from models import build_registers, load_register_map

OPTIONS_PATH = Path("/data/options.json")
LOGGER = logging.getLogger("sungrow_sunspec")


def read_options(path: Path = OPTIONS_PATH) -> dict[str, Any]:
    try:
        options = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Unable to read add-on options at {path}: {error}") from error

    required = {
        "inverter_host": str,
        "inverter_port": int,
        "unit_id": int,
        "refresh_interval": int,
        "sunspec_port": int,
        "register_map_file": str,
    }
    for key, expected_type in required.items():
        value = options.get(key)
        if not isinstance(value, expected_type) or (
            expected_type is str and not value.strip()
        ):
            raise ValueError(f"Invalid or missing add-on option: {key}")
    return options


async def poll_forever(
    *,
    options: dict[str, Any],
    mappings: dict[str, Any],
    server: SunSpecServer,
) -> None:
    while True:
        try:
            if mappings["fields"]:
                async with ModbusClient(
                    options["inverter_host"],
                    options["inverter_port"],
                    options["unit_id"],
                ) as client:
                    values = await read_mapped_fields(client, mappings["fields"])
            else:
                values = {}
            server.update(build_registers(mappings, values))
            LOGGER.info("Updated %d mapped SunSpec points", len(values))
        except (OSError, asyncio.TimeoutError, ValueError) as error:
            server.update(build_registers(mappings, {}))
            LOGGER.error("Inverter poll failed; mapped points marked unavailable: %s", error)
        await asyncio.sleep(options["refresh_interval"])


async def run() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    options = read_options()
    map_path = Path(options["register_map_file"])
    mappings = load_register_map(map_path)
    if not mappings["fields"]:
        LOGGER.warning(
            "No Sungrow source points are configured in %s; SunSpec points will be "
            "reported as not implemented until a register map is installed.",
            map_path,
        )

    server = SunSpecServer(
        host="0.0.0.0",
        port=options["sunspec_port"],
        register_map=build_registers(mappings, {}),
    )
    await server.start()
    LOGGER.info(
        "SunSpec Modbus TCP server listening on port %d (read-only)",
        options["sunspec_port"],
    )
    await poll_forever(options=options, mappings=mappings, server=server)


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        LOGGER.info("Shutting down")


if __name__ == "__main__":
    main()
