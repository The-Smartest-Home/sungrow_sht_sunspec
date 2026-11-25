"""Minimal asynchronous Modbus TCP client and read-only SunSpec server."""

from __future__ import annotations

import asyncio
import logging
import struct
from collections import defaultdict
from typing import Any

LOGGER = logging.getLogger("sungrow_sunspec.modbus")
MAX_READ_REGISTERS = 120


class ModbusClient:
    def __init__(self, host: str, port: int, unit_id: int, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.transaction_id = 0

    async def __aenter__(self) -> ModbusClient:
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), timeout=self.timeout
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self.writer is not None:
            self.writer.close()
            await self.writer.wait_closed()

    async def read_registers(self, register_type: str, address: int, count: int) -> list[int]:
        if self.reader is None or self.writer is None:
            raise RuntimeError("Modbus client is not connected")
        if register_type not in {"input", "holding"}:
            raise ValueError(f"Unsupported register type: {register_type}")
        if not 1 <= count <= 125 or not 0 <= address <= 65535:
            raise ValueError("Invalid Modbus register range")

        function = 4 if register_type == "input" else 3
        self.transaction_id = (self.transaction_id + 1) & 0xFFFF
        pdu = struct.pack(">BHH", function, address, count)
        self.writer.write(
            struct.pack(">HHHB", self.transaction_id, 0, len(pdu) + 1, self.unit_id) + pdu
        )
        await asyncio.wait_for(self.writer.drain(), timeout=self.timeout)

        header = await asyncio.wait_for(self.reader.readexactly(7), timeout=self.timeout)
        transaction, protocol, length, unit = struct.unpack(">HHHB", header)
        if transaction != self.transaction_id or protocol != 0 or unit != self.unit_id:
            raise ValueError("Invalid Modbus response header")
        if not 2 <= length <= 252:
            raise ValueError("Invalid Modbus response length")
        response = await asyncio.wait_for(
            self.reader.readexactly(length - 1), timeout=self.timeout
        )
        if response[0] == (function | 0x80):
            raise OSError(f"Upstream inverter returned Modbus exception {response[1]}")
        if response[0] != function or response[1] != count * 2 or len(response) != count * 2 + 2:
            raise ValueError("Invalid Modbus register response")
        return list(struct.unpack(f">{count}H", response[2:]))


async def read_mapped_fields(
    client: ModbusClient, fields: dict[str, dict[str, Any]]
) -> dict[str, int | float]:
    grouped: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for name, source in fields.items():
        width = int(source["data_type"][-2:]) // 16
        grouped[source["register_type"]].append((source["address"], width, name))

    values: dict[str, int | float] = {}
    for register_type, entries in grouped.items():
        entries.sort()
        ranges: list[tuple[int, int, list[tuple[int, int, str]]]] = []
        for address, width, name in entries:
            end = address + width
            if ranges and address <= ranges[-1][1] and end - ranges[-1][0] <= MAX_READ_REGISTERS:
                start, previous_end, members = ranges[-1]
                ranges[-1] = (start, max(previous_end, end), [*members, (address, width, name)])
            else:
                ranges.append((address, end, [(address, width, name)]))

        for start, end, members in ranges:
            registers = await client.read_registers(register_type, start, end - start)
            for address, width, name in members:
                source = fields[name]
                offset = address - start
                raw = registers[offset : offset + width]
                if width > 1 and source["word_order"] == "swap":
                    raw.reverse()
                data_type = source["data_type"]
                signed = data_type.startswith("int")
                integer = 0
                for word in raw:
                    integer = (integer << 16) | word
                if signed and integer & (1 << (width * 16 - 1)):
                    integer -= 1 << (width * 16)
                if integer in source.get("invalid_values", []):
                    continue
                values[name] = integer * source["scale"]
    return values


def handle_request(pdu: bytes, registers: dict[int, int]) -> bytes:
    """Handle a Modbus PDU. Writes are rejected to keep inverter controls read-only."""
    if not pdu:
        return b""
    function = pdu[0]
    if function not in (3, 4):
        return bytes((function | 0x80, 1))
    if len(pdu) != 5:
        return bytes((function | 0x80, 3))
    address, count = struct.unpack(">HH", pdu[1:])
    if not 1 <= count <= 125 or address + count > 65536:
        return bytes((function | 0x80, 3))
    try:
        words = [registers[address + offset] for offset in range(count)]
    except KeyError:
        return bytes((function | 0x80, 2))
    return bytes((function, count * 2)) + struct.pack(f">{count}H", *words)


class SunSpecServer:
    def __init__(self, host: str, port: int, register_map: dict[int, int]):
        self.host = host
        self.port = port
        self.register_map = register_map
        self.server: asyncio.AbstractServer | None = None

    def update(self, register_map: dict[int, int]) -> None:
        self.register_map = register_map

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._client_connected, self.host, self.port)

    async def _client_connected(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        try:
            while True:
                header = await reader.readexactly(7)
                transaction, protocol, length, unit = struct.unpack(">HHHB", header)
                if protocol != 0 or not 2 <= length <= 254:
                    LOGGER.warning("Rejected malformed Modbus request from %s", peer)
                    break
                pdu = await reader.readexactly(length - 1)
                response_pdu = handle_request(pdu, self.register_map)
                response_header = struct.pack(
                    ">HHHB", transaction, 0, len(response_pdu) + 1, unit
                )
                writer.write(response_header + response_pdu)
                await writer.drain()
        except asyncio.IncompleteReadError:
            pass
        except (ConnectionError, OSError) as error:
            LOGGER.debug("SunSpec client %s disconnected: %s", peer, error)
        finally:
            writer.close()
            await writer.wait_closed()
