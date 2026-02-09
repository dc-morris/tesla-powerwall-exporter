"""Tesla Powerwall Prometheus Exporter.

Polls the Tesla Fleet API for energy site data and exposes it as
Prometheus metrics.
"""

import json
import os
import time
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configuration from environment
CLIENT_ID = os.environ["TESLA_CLIENT_ID"]
CLIENT_SECRET = os.environ["TESLA_CLIENT_SECRET"]
REFRESH_TOKEN_FILE = "/data/refresh_token"
SITE_ID = os.environ["TESLA_SITE_ID"]
API_BASE = os.environ.get("TESLA_API_BASE", "https://fleet-api.prd.eu.vn.cloud.tesla.com")
PORT = int(os.environ.get("PORT", "9998"))

access_token = None
token_expiry = 0


def load_refresh_token():
    with open(REFRESH_TOKEN_FILE, "r") as f:
        return f.read().strip()


def save_refresh_token(token):
    with open(REFRESH_TOKEN_FILE, "w") as f:
        f.write(token)


def refresh_access_token():
    global access_token, token_expiry

    refresh_token = load_refresh_token()
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
    }).encode()

    req = urllib.request.Request("https://auth.tesla.com/oauth2/v3/token", data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    resp = urllib.request.urlopen(req)
    tokens = json.loads(resp.read())

    access_token = tokens["access_token"]
    token_expiry = time.time() + tokens["expires_in"] - 300  # refresh 5 min early

    if "refresh_token" in tokens:
        save_refresh_token(tokens["refresh_token"])

    print(f"Token refreshed, expires in {tokens['expires_in']}s")


def get_token():
    global access_token, token_expiry
    if access_token is None or time.time() >= token_expiry:
        refresh_access_token()
    return access_token


def fetch_live_status():
    token = get_token()
    url = f"{API_BASE}/api/1/energy_sites/{SITE_ID}/live_status"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["response"]


def format_metrics(data):
    lines = []

    def gauge(name, help_text, value):
        if value is not None:
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")

    # Names matching the Grafana dashboard (ID 16053)
    gauge("tesla_solar_instant_power", "Solar power production in watts", data.get("solar_power"))
    gauge("tesla_battery_instant_power", "Battery power in watts (positive=discharging)", data.get("battery_power"))
    gauge("tesla_site_instant_power", "Grid power in watts (positive=importing)", data.get("grid_power"))
    gauge("tesla_load_instant_power", "Home power consumption in watts", data.get("load_power"))
    gauge("tesla_powerwall_state_of_charge_percentage", "Battery charge percentage", data.get("percentage_charged"))
    gauge("tesla_powerwall_generator_power_watts", "Generator power in watts", data.get("generator_power"))

    grid_up = 1 if data.get("grid_status") == "Active" else 0
    gauge("tesla_powerwall_grid_active", "Whether grid is active (1=active, 0=down)", grid_up)

    on_grid = 1 if data.get("island_status") == "on_grid" else 0
    gauge("tesla_powerwall_on_grid", "Whether system is on grid (1=on_grid, 0=islanded)", on_grid)

    storm = 1 if data.get("storm_mode_active") else 0
    gauge("tesla_powerwall_storm_mode_active", "Whether storm mode is active", storm)

    return "\n".join(lines) + "\n"


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            try:
                data = fetch_live_status()
                body = format_metrics(data)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.end_headers()
                self.wfile.write(body.encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {e}\n".encode())
                print(f"Error fetching metrics: {e}")
        elif self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok\n")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress request logs
        pass


if __name__ == "__main__":
    print(f"Starting Tesla Powerwall exporter on port {PORT}")
    print(f"Site ID: {SITE_ID}")
    server = HTTPServer(("0.0.0.0", PORT), MetricsHandler)
    server.serve_forever()
