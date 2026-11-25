import asyncio
import ipaddress
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "addon" / "sungrow_sunspec" / "app"))

from modbus import (
    ModbusClient,
    SunSpecServer,
    handle_request,
    parse_allowed_clients,
    read_mapped_fields,
)


class FakeClient:
    def __init__(self):
        self.calls = []
        self.registers = {10: 0xFFFF, 11: 20, 12: 0}

    async def read_registers(self, register_type, address, count):
        self.calls.append((register_type, address, count))
        return [self.registers[index] for index in range(address, address + count)]


class ModbusRequestTests(unittest.TestCase):
    def test_allowed_clients_parse_addresses_and_cidrs(self):
        networks = parse_allowed_clients("192.168.2.3,192.168.2.0/24")
        self.assertEqual(len(networks), 2)
        self.assertIn(ipaddress.ip_address("192.168.2.3"), networks[0])
        self.assertIn(ipaddress.ip_address("192.168.2.200"), networks[1])

    def test_allowed_clients_support_ipv4_mapped_ipv6_peers(self):
        networks = parse_allowed_clients("192.168.2.3/32")
        address = ipaddress.ip_address("::ffff:192.168.2.3")
        self.assertIn(address.ipv4_mapped, networks[0])

    def test_allowed_clients_reject_empty_or_invalid_values(self):
        for value in ("", " , ", "not-an-address"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_allowed_clients(value)

    def test_read_holding_registers(self):
        response = handle_request(struct.pack(">BHH", 3, 40000, 2), {40000: 0x5375, 40001: 0x6E53})
        self.assertEqual(response, b"\x03\x04\x53\x75\x6e\x53")

    def test_read_input_registers_and_missing_address(self):
        response = handle_request(struct.pack(">BHH", 4, 40010, 1), {40010: 12})
        self.assertEqual(response, b"\x04\x02\x00\x0c")
        missing = handle_request(struct.pack(">BHH", 3, 40010, 2), {40010: 12})
        self.assertEqual(missing, b"\x83\x02")

    def test_writes_are_rejected(self):
        response = handle_request(b"\x06\x00\x01\x00\x02", {})
        self.assertEqual(response, b"\x86\x01")

    def test_adjacent_sources_are_grouped_and_signed_values_decoded(self):
        async def run_test():
            client = FakeClient()
            fields = {
                "W": {
                    "register_type": "input",
                    "address": 10,
                    "data_type": "int16",
                    "scale": 0.1,
                },
                "WH": {
                    "register_type": "input",
                    "address": 11,
                    "data_type": "uint32",
                    "scale": 1,
                    "word_order": "swap",
                },
            }
            values = await read_mapped_fields(client, fields)
            self.assertEqual(values, {"W": -0.1, "WH": 20})
            self.assertEqual(client.calls, [("input", 10, 3)])

        asyncio.run(run_test())

    def test_configured_invalid_upstream_value_is_not_returned_as_measurement(self):
        async def run_test():
            client = FakeClient()
            client.registers = {10: 0xFFFF, 11: 0x7FFF}
            values = await read_mapped_fields(
                client,
                {
                    "MTR_W": {
                        "register_type": "input",
                        "address": 10,
                        "data_type": "int32",
                        "scale": 1,
                        "word_order": "swap",
                        "invalid_values": [2147483647],
                    }
                },
            )
            self.assertNotIn("MTR_W", values)

        asyncio.run(run_test())

    def test_modbus_tcp_server_and_client_interoperate(self):
        async def run_test():
            server = SunSpecServer(
                "127.0.0.1",
                0,
                {40000: 0x5375, 40001: 0x6E53},
                "127.0.0.1/32",
            )
            await server.start()
            port = server.server.sockets[0].getsockname()[1]
            try:
                async with ModbusClient("127.0.0.1", port, 1) as client:
                    words = await client.read_registers("holding", 40000, 2)
                self.assertEqual(words, [0x5375, 0x6E53])
            finally:
                server.server.close()
                await server.server.wait_closed()

        asyncio.run(run_test())

    def test_sunspec_server_rejects_clients_outside_allowlist(self):
        async def run_test():
            server = SunSpecServer("127.0.0.1", 0, {}, "192.168.2.3/32")
            await server.start()
            port = server.server.sockets[0].getsockname()[1]
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                try:
                    with self.assertRaises(asyncio.IncompleteReadError):
                        await asyncio.wait_for(reader.readexactly(1), timeout=1)
                finally:
                    writer.close()
                    await writer.wait_closed()
            finally:
                server.server.close()
                await server.server.wait_closed()

        asyncio.run(run_test())

    def test_upstream_response_timeout_is_not_silently_accepted(self):
        async def run_test():
            async def accept_and_stall(reader, writer):
                await reader.read(12)
                await asyncio.sleep(0.1)
                writer.close()

            server = await asyncio.start_server(accept_and_stall, "127.0.0.1", 0)
            port = server.sockets[0].getsockname()[1]
            try:
                async with ModbusClient("127.0.0.1", port, 1, timeout=0.01) as client:
                    with self.assertRaises(asyncio.TimeoutError):
                        await client.read_registers("input", 1, 1)
            finally:
                server.close()
                await server.wait_closed()

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
