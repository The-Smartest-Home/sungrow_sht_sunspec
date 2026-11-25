"""Home Assistant add-on entry point for the Sungrow SunSpec bridge."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from modbus import (
    ModbusClient,
    SunSpecServer,
    read_mapped_fields,
    read_sunspec_common,
)
from models import build_registers, load_register_map
from web import DashboardServer, DashboardState

OPTIONS_PATH = Path(os.environ.get("OPTIONS_PATH", "/data/options.json"))
LOGGER = logging.getLogger("sungrow_sunspec")
SUPERVISOR_URL = "http://supervisor/addons/self/info"


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


def get_ingress_port(
    token: str | None = None,
    *,
    url: str = SUPERVISOR_URL,
) -> int:
    supervisor_token = token or os.environ.get("SUPERVISOR_TOKEN")
    if not supervisor_token:
        raise RuntimeError("SUPERVISOR_TOKEN is required to resolve the ingress port")
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Unable to resolve Home Assistant ingress port: {error}") from error
    try:
        port = payload["data"]["ingress_port"]
    except (KeyError, TypeError) as error:
        raise RuntimeError("Supervisor response does not contain an ingress port") from error
    if type(port) is not int or not 1 <= port <= 65535:
        raise RuntimeError(f"Supervisor returned an invalid ingress port: {port!r}")
    return port


async def poll_forever(
    *,
    options: dict[str, Any],
    mappings: dict[str, Any],
    server: SunSpecServer,
    dashboard_state: DashboardState,
) -> None:
    while True:
        try:
            async with ModbusClient(
                options["inverter_host"],
                options["inverter_port"],
                options["unit_id"],
            ) as client:
                values = (
                    await read_mapped_fields(client, mappings["fields"])
                    if mappings["fields"]
                    else {}
                )
                try:
                    common_values = await read_sunspec_common(client)
                except (OSError, asyncio.TimeoutError, ValueError) as error:
                    common_values = {}
                    LOGGER.debug(
                        "Inverter SunSpec Common model unavailable; using profile defaults: %s",
                        error,
                    )
                else:
                    if not common_values:
                        LOGGER.debug(
                            "Inverter SunSpec Common model not found; using profile defaults"
                        )
            server.update(build_registers(mappings, values, common_values=common_values))
            dashboard_state.update(values, common_values=common_values)
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

    ingress_port = get_ingress_port()
    if ingress_port == options["sunspec_port"]:
        raise RuntimeError("The allocated ingress port conflicts with sunspec_port")

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
        port=ingress_port,
        snapshot=dashboard_state.snapshot,
    )
    await dashboard.start()
    LOGGER.info("Authenticated dashboard ingress listening on port %d", dashboard.port)
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
