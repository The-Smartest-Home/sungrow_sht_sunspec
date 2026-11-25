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
from web import DashboardServer, DashboardState

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
        "web_port": int,
        "allowed_clients": str,
        "register_map_file": str,
    }
    for key, expected_type in required.items():
        value = options.get(key)
        if not isinstance(value, expected_type) or (
            expected_type is int and isinstance(value, bool)
        ) or (
            expected_type is str and not value.strip()
        ):
            raise ValueError(f"Invalid or missing add-on option: {key}")
    if options["sunspec_port"] == options["web_port"]:
        raise ValueError("sunspec_port and web_port must be different")
    return options


def resolve_register_map_path(
    value: str,
    profile_directory: Path = Path("/app/profiles"),
    config_directory: Path = Path("/config"),
) -> Path:
    path = Path(value).resolve()
    allowed_roots = (profile_directory.resolve(), config_directory.resolve())
    if not any(path.is_relative_to(root) for root in allowed_roots):
        raise ValueError("register_map_file must be inside /app/profiles or /config")
    if not path.is_file():
        raise ValueError(f"Register map does not exist or is not a file: {path}")
    return path


async def poll_forever(
    *,
    options: dict[str, Any],
    mappings: dict[str, Any],
    server: SunSpecServer,
    dashboard_state: DashboardState,
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
            dashboard_state.update(values)
            LOGGER.info("Updated %d mapped SunSpec points", len(values))
        except (OSError, asyncio.TimeoutError, ValueError) as error:
            server.update(build_registers(mappings, {}))
            dashboard_state.update({}, error=True)
            LOGGER.error("Inverter poll failed; mapped points marked unavailable: %s", error)
        await asyncio.sleep(options["refresh_interval"])


async def run() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    options = read_options()
    map_path = resolve_register_map_path(options["register_map_file"])
    mappings = load_register_map(map_path)
    if not mappings["fields"]:
        LOGGER.warning(
            "No Sungrow source points are configured in %s; SunSpec points will be "
            "reported as not implemented until a register map is installed.",
            map_path,
        )

    dashboard_state = DashboardState(mappings)
    server = SunSpecServer(
        host="0.0.0.0",
        port=options["sunspec_port"],
        register_map=build_registers(mappings, {}),
        allowed_clients=options["allowed_clients"],
    )
    await server.start()
    LOGGER.info(
        "SunSpec Modbus TCP server listening on port %d (read-only)",
        options["sunspec_port"],
    )
    dashboard = DashboardServer(
        host="0.0.0.0",
        port=options["web_port"],
        allowed_clients=options["allowed_clients"],
        snapshot=dashboard_state.snapshot,
    )
    await dashboard.start()
    LOGGER.info("Read-only dashboard listening on port %d", options["web_port"])
    await poll_forever(
        options=options,
        mappings=mappings,
        server=server,
        dashboard_state=dashboard_state,
    )


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        LOGGER.info("Shutting down")


if __name__ == "__main__":
    main()
