import asyncio
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "addon" / "sungrow_sunspec" / "app"))

from web import DashboardServer, DashboardState


class DashboardServerTests(unittest.TestCase):
    def test_serves_dashboard_and_live_json_to_allowed_client(self):
        async def run_test():
            state = DashboardState(
                {
                    "common": {
                        "manufacturer": "Sungrow",
                        "model": "SH25T",
                        "options": "SHB",
                        "version": "",
                        "serial_number": "",
                        "device_address": 1,
                    },
                    "fields": {"MTR_W": {}},
                    "scale_factors": {},
                }
            )
            state.update({"MTR_W": -425})
            server = DashboardServer(
                "127.0.0.1", 0, "127.0.0.1/32", state.snapshot
            )
            await server.start()
            port = server.server.sockets[0].getsockname()[1]
            try:
                page = await self.get_response(port, "/")
                self.assertIn(b"Live inverter, battery and grid measurements", page)

                response = await self.get_response(port, "/api/values")
                body = response.split(b"\r\n\r\n", 1)[1]
                data = json.loads(body)
                self.assertEqual(data["status"], "online")
                meter = next(model for model in data["models"] if model["id"] == 203)
                grid_power = next(
                    point for point in meter["points"] if point["name"] == "MTR_W"
                )
                self.assertEqual(grid_power["value"], -425)
            finally:
                server.server.close()
                await server.server.wait_closed()

        asyncio.run(run_test())

    def test_rejects_clients_outside_allowlist(self):
        async def run_test():
            server = DashboardServer("127.0.0.1", 0, "192.168.2.3/32", dict)
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

    @staticmethod
    async def get_response(port, path):
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(
            f"GET {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n".encode()
        )
        await writer.drain()
        response = await reader.read()
        writer.close()
        await writer.wait_closed()
        return response


if __name__ == "__main__":
    unittest.main()
