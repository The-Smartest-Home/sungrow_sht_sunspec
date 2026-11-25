"""Small, read-only HTTP dashboard for the live SunSpec data."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from modbus import CLIENT_REQUEST_TIMEOUT, client_is_allowed, parse_allowed_clients
from models import build_dashboard_data

LOGGER = logging.getLogger("sungrow_sunspec.web")
SUPERVISOR_CLIENTS = parse_allowed_clients("172.30.32.2/32")

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#102b3f">
  <title>Sungrow SunSpec</title>
  <link rel="stylesheet" href="style.css">
  <script defer src="app.js"></script>
</head>
<body>
  <header class="topbar">
    <div class="brand-mark" aria-hidden="true"><span>☼</span></div>
    <div>
      <p class="eyebrow">ENERGY OVERVIEW</p>
      <h1>Sungrow <span>SunSpec</span></h1>
      <p class="subtitle">Live inverter, battery and grid measurements</p>
    </div>
    <div id="connection" class="connection waiting"><span></span>Connecting</div>
  </header>
  <main>
    <section id="summary" class="summary" aria-label="Key measurements"></section>
    <div class="section-heading">
      <div>
        <p class="eyebrow">SUNSPEC DATA</p>
        <h2>Measurements</h2>
      </div>
      <label class="toggle"><input id="show-unavailable" type="checkbox">
        <span>Show unavailable points</span></label>
    </div>
    <div id="models" class="models" aria-live="polite"></div>
    <footer><span id="updated">Waiting for the first inverter update</span>
      <span>Refreshes every 5 seconds</span></footer>
  </main>
</body>
</html>
"""

STYLE = """
:root{color-scheme:light;--ink:#193548;--muted:#718592;--line:#e4ebee;--teal:#138f89;--navy:#102b3f}
*{box-sizing:border-box}body{margin:0;background:#f3f7f7;color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.topbar{min-height:190px;padding:35px max(6vw,24px);display:flex;align-items:center;gap:22px;background:linear-gradient(115deg,#102b3f,#174e5b);color:white}
.brand-mark{width:64px;height:64px;flex:none;border-radius:20px;display:grid;place-items:center;background:#f5b942;color:#102b3f;font-size:44px}
.eyebrow{margin:0 0 5px;color:#75d0c6;font-size:11px;font-weight:800;letter-spacing:1.6px}
h1,h2,p{margin-top:0}h1{margin-bottom:3px;font-size:clamp(25px,4vw,36px);letter-spacing:-.7px}h1 span{color:#8edbd2;font-weight:500}.subtitle{margin:0;color:#d0dfe3}
.connection{margin-left:auto;display:flex;align-items:center;gap:9px;padding:8px 13px;border:1px solid #ffffff3b;border-radius:30px;font-size:13px;white-space:nowrap}.connection span{width:9px;height:9px;border-radius:50%;background:#f5b942}
.connection.online span{background:#68d5a5}.connection.unavailable span{background:#ff8585}.connection.waiting span{background:#f5b942}
main{width:min(1180px,90vw);margin:38px auto}.summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:-72px}
.metric,.model-card{background:white;border:1px solid var(--line);border-radius:16px;box-shadow:0 8px 24px #18394a0a}
.metric{min-width:0;min-height:148px;padding:22px}.metric-label{color:var(--muted);font-size:13px;font-weight:650}.metric-value{margin:13px 0 0;font-size:clamp(27px,4vw,38px);font-weight:750;letter-spacing:-1px;overflow-wrap:anywhere}.metric-unit{margin-left:7px;color:var(--muted);font-size:15px;font-weight:500;letter-spacing:0;white-space:nowrap}.metric-hint{margin:3px 0 0;color:var(--muted);font-size:12px}
.section-heading{display:flex;align-items:end;justify-content:space-between;margin:43px 0 16px}.section-heading h2{margin:0;font-size:23px;letter-spacing:-.4px}.section-heading .eyebrow{color:var(--teal)}
.toggle{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:13px;cursor:pointer}.toggle input{accent-color:var(--teal)}
.models{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.model-card{padding:21px;overflow:hidden}.model-title{display:flex;justify-content:space-between;align-items:center;padding-bottom:15px;border-bottom:1px solid var(--line)}.model-title h3{margin:0;font-size:17px}.model-id{color:var(--muted);font-size:12px}
.point-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px 18px;min-width:0}.point{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:start;gap:4px 8px;min-width:0;padding:11px 0;border-bottom:1px solid #edf1f2}.point-label{min-width:0;color:#526a77;font-size:13px;overflow-wrap:anywhere}.point-value{min-width:0;font-size:13px;font-weight:700;text-align:right;white-space:normal;overflow-wrap:anywhere}.point.unavailable .point-value{color:#a6b0b5;font-weight:500}
footer{display:flex;justify-content:space-between;gap:12px;margin:22px 2px;color:var(--muted);font-size:12px}
@media(max-width:720px){.topbar{align-items:flex-start;padding:27px 5vw;gap:14px}.brand-mark{width:48px;height:48px;border-radius:15px;font-size:34px}.connection{position:absolute;right:5vw;top:24px;padding:6px 9px;font-size:11px}.topbar>div:nth-child(2){padding-top:48px}.summary{grid-template-columns:1fr;margin-top:-48px;gap:10px}.metric{min-height:auto;padding:17px}.metric-value{margin-top:5px}.models{grid-template-columns:1fr}.section-heading{align-items:flex-start;gap:12px;flex-direction:column}main{margin-top:24px}}
"""

SCRIPT = """
const numberFormat = new Intl.NumberFormat(undefined, {maximumFractionDigits: 2});

function formatValue(point) {
  if (!point.available || point.value === null) return "N/I";
  if (typeof point.value === "number") return numberFormat.format(point.value);
  return String(point.value);
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function render(data) {
  const connection = document.querySelector("#connection");
  connection.className = `connection ${data.status}`;
  connection.lastChild.textContent = data.status === "online" ? "Live" :
    data.status === "unavailable" ? "Inverter unavailable" : "Waiting for data";

  const summaries = data.summary.map(item => {
    const model = data.models.find(candidate => candidate.id === item.model);
    const point = model?.points.find(candidate => candidate.name === item.point);
    const card = makeElement("article", "metric");
    card.append(makeElement("div", "metric-label", item.label));
    const value = makeElement("p", "metric-value");
    value.append(document.createTextNode(point ? formatValue(point) : "N/I"));
    if (point?.available && point.unit) value.append(makeElement("span", "metric-unit", point.unit));
    card.append(value);
    let hint = "";
    if (item.point === "MTR_W" && point?.available && typeof point.value === "number")
      hint = point.value < 0 ? "Exporting to grid" : point.value > 0 ? "Importing from grid" : "Near-zero grid flow";
    if (!point?.available) hint = "Point not available in the active profile";
    card.append(makeElement("p", "metric-hint", hint));
    return card;
  });
  document.querySelector("#summary").replaceChildren(...summaries);

  const showUnavailable = document.querySelector("#show-unavailable").checked;
  const cards = data.models.map(model => {
    const card = makeElement("article", "model-card");
    const title = makeElement("div", "model-title");
    title.append(makeElement("h3", "", model.name));
    title.append(makeElement("span", "model-id", `Model ${model.id}`));
    card.append(title);
    const list = makeElement("div", "point-list");
    const points = model.points.filter(point => showUnavailable || point.available);
    for (const point of points) {
      const row = makeElement("div", `point${point.available ? "" : " unavailable"}`);
      row.append(makeElement("span", "point-label", point.label));
      const value = makeElement("span", "point-value",
        `${formatValue(point)}${point.available && point.unit ? ` ${point.unit}` : ""}`);
      row.append(value);
      list.append(row);
    }
    if (!points.length) list.append(makeElement("p", "metric-hint", "No mapped values available yet."));
    card.append(list);
    return card;
  });
  document.querySelector("#models").replaceChildren(...cards);
  const updated = data.updated_at ? new Date(data.updated_at).toLocaleString() : null;
  document.querySelector("#updated").textContent = updated
    ? `Last successful inverter update: ${updated}` : "Waiting for the first inverter update";
}

async function refresh() {
  try {
    const response = await fetch("api/values", {cache: "no-store"});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());
  } catch {
    const connection = document.querySelector("#connection");
    connection.className = "connection unavailable";
    connection.lastChild.textContent = "Dashboard unavailable";
  }
}

document.querySelector("#show-unavailable").addEventListener("change", refresh);
refresh();
window.setInterval(refresh, 5000);
"""


class DashboardState:
    def __init__(self, mappings: dict[str, Any]):
        self.mappings = mappings
        self.source_values: dict[str, int | float] = {}
        self.updated_at: str | None = None
        self.error = False

    def update(self, values: dict[str, int | float], *, error: bool = False) -> None:
        self.source_values = {} if error else values
        self.error = error
        if not error:
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> dict[str, Any]:
        return build_dashboard_data(
            self.mappings,
            self.source_values,
            updated_at=self.updated_at,
            error=self.error,
        )


class DashboardServer:
    def __init__(
        self,
        host: str,
        port: int,
        snapshot: Callable[[], dict[str, Any]],
    ):
        self.host = host
        self.port = port
        self.snapshot = snapshot
        self.server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        self.server = await asyncio.start_server(
            self._client_connected, self.host, self.port, limit=4096
        )

    async def _client_connected(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        try:
            if not client_is_allowed(peer, SUPERVISOR_CLIENTS):
                LOGGER.warning("Rejected non-Supervisor dashboard request from %s", peer)
                return
            request = await asyncio.wait_for(
                reader.readuntil(b"\r\n\r\n"), timeout=CLIENT_REQUEST_TIMEOUT
            )
            lines = request.split(b"\r\n")
            request_line = lines[0].decode("ascii")
            method, path, version = request_line.split(" ", 2)
            headers: dict[str, str] = {}
            for line in lines[1:]:
                if not line:
                    break
                key, value = line.decode("latin-1").split(":", 1)
                headers[key.strip().lower()] = value.strip()
            ingress_path = headers.get("x-ingress-path", "")
            if ingress_path and path.startswith(ingress_path):
                path = path[len(ingress_path) :]
            path = path.split("?", 1)[0]
            if not path.startswith("/"):
                path = f"/{path}"
            if version not in {"HTTP/1.0", "HTTP/1.1"}:
                await self._respond(writer, "400 Bad Request", b"Bad request", "text/plain")
            elif method != "GET":
                await self._respond(writer, "405 Method Not Allowed", b"Method not allowed", "text/plain")
            elif path == "/":
                await self._respond(writer, "200 OK", PAGE.encode(), "text/html; charset=utf-8")
            elif path == "/style.css":
                await self._respond(writer, "200 OK", STYLE.encode(), "text/css; charset=utf-8")
            elif path == "/app.js":
                await self._respond(writer, "200 OK", SCRIPT.encode(), "text/javascript; charset=utf-8")
            elif path == "/api/values":
                payload = json.dumps(self.snapshot(), allow_nan=False).encode()
                await self._respond(writer, "200 OK", payload, "application/json; charset=utf-8")
            else:
                await self._respond(writer, "404 Not Found", b"Not found", "text/plain")
        except (
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
            asyncio.TimeoutError,
            UnicodeDecodeError,
            ValueError,
        ):
            LOGGER.debug("Malformed or idle dashboard request from %s", peer)
        except (ConnectionError, OSError) as error:
            LOGGER.debug("Dashboard client %s disconnected: %s", peer, error)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass

    @staticmethod
    async def _respond(
        writer: asyncio.StreamWriter, status: str, body: bytes, content_type: str
    ) -> None:
        headers = (
            f"HTTP/1.1 {status}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Cache-Control: no-store\r\n"
            "X-Content-Type-Options: nosniff\r\n"
            "Referrer-Policy: no-referrer\r\n"
            "Content-Security-Policy: default-src 'self'; style-src 'self'; "
            "script-src 'self'; frame-ancestors 'self'\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        writer.write(headers + body)
        await writer.drain()
