# Tesla Powerwall Prometheus Exporter

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet?logo=anthropic)](https://claude.ai/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A lightweight Prometheus exporter for Tesla Powerwall systems that uses the **Tesla Fleet API** (cloud API) instead of the local Gateway API.

Most existing Powerwall exporters require direct LAN access to the Powerwall Gateway. This exporter uses Tesla's official Fleet API, so it works from anywhere — no local network access required.

## Quick Start

1. Clone and configure:
   ```bash
   git clone https://github.com/dc-morris/tesla-powerwall-exporter.git
   cd tesla-powerwall-exporter
   cp .env.example .env
   # Edit .env with your Tesla API credentials
   ```

2. Seed your refresh token:
   ```bash
   mkdir -p data
   echo 'YOUR_REFRESH_TOKEN' > data/refresh_token
   ```

3. Start the exporter:
   ```bash
   docker compose up -d
   ```

4. Verify it's working:
   ```bash
   curl http://localhost:9998/metrics
   ```

## Metrics

Metric names are compatible with the [Grafana Tesla Powerwall dashboard (ID 16053)](https://grafana.com/grafana/dashboards/16053).

| Metric | Description |
|--------|-------------|
| `tesla_solar_instant_power` | Solar production (watts) |
| `tesla_battery_instant_power` | Battery power (watts, positive=discharging) |
| `tesla_site_instant_power` | Grid power (watts, positive=importing) |
| `tesla_load_instant_power` | Home consumption (watts) |
| `tesla_powerwall_state_of_charge_percentage` | Battery charge (%) |
| `tesla_powerwall_generator_power_watts` | Generator power (watts) |
| `tesla_powerwall_grid_active` | Grid status (1=active, 0=down) |
| `tesla_powerwall_on_grid` | Grid connection (1=on_grid, 0=islanded) |
| `tesla_powerwall_storm_mode_active` | Storm mode (1=active, 0=inactive) |

## Prometheus Configuration

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: tesla_powerwall
    scrape_interval: 30s
    static_configs:
      - targets: ["tesla-exporter:9998"]
```

An example `prometheus.yml` is included in this repo.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TESLA_CLIENT_ID` | Yes | — | Tesla developer app client ID |
| `TESLA_CLIENT_SECRET` | Yes | — | Tesla developer app client secret |
| `TESLA_SITE_ID` | Yes | — | Energy site ID (see Fleet API setup) |
| `TESLA_API_BASE` | No | `https://fleet-api.prd.eu.vn.cloud.tesla.com` | Fleet API base URL |
| `PORT` | No | `9998` | Metrics server port |

### Fleet API regions

| Region | URL |
|--------|-----|
| North America, Asia-Pacific | `https://fleet-api.prd.na.vn.cloud.tesla.com` |
| Europe, Middle East, Africa | `https://fleet-api.prd.eu.vn.cloud.tesla.com` |
| China | `https://fleet-api.prd.cn.vn.cloud.tesla.com` |

## Tesla Fleet API Setup

This is a one-time process to get the credentials needed to run the exporter.

### 1. Create a developer app

Go to https://developer.tesla.com and create an app with:

- **Redirect URI**: a URL you control (e.g. `https://yourdomain.com/callback`)
- **Scopes**: `energy_device_data`
- **Origin**: your domain

### 2. Host your public key

Tesla requires your app's public key to be hosted at:
```
https://yourdomain.com/.well-known/appspecific/com.tesla.3p.public-key.pem
```

### 3. Register the app with Tesla

```bash
# Get a partner token first
curl -X POST https://auth.tesla.com/oauth2/v3/token \
  -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&scope=openid energy_device_data&audience=https://fleet-api.prd.na.vn.cloud.tesla.com"

# Register with each region you need
curl -X POST https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/partner_accounts \
  -H "Authorization: Bearer PARTNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domain": "yourdomain.com"}'
```

### 4. Authorize and get tokens

Open this URL in your browser (substitute your values):
```
https://auth.tesla.com/oauth2/v3/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https://yourdomain.com/callback&scope=energy_device_data%20offline_access&state=setup
```

After authorizing, you'll be redirected with a `code` parameter. Exchange it for tokens:

```bash
curl -X POST https://auth.tesla.com/oauth2/v3/token \
  -d "grant_type=authorization_code&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&code=AUTH_CODE&redirect_uri=https://yourdomain.com/callback"
```

Save the `refresh_token` from the response.

### 5. Find your energy site ID

```bash
curl https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/products \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

Look for `energy_site_id` in the response.

### 6. Configure and run

Add your credentials to `.env` and seed the refresh token:

```bash
mkdir -p data
echo 'REFRESH_TOKEN_FROM_STEP_4' > data/refresh_token
docker compose up -d
```

The exporter rotates refresh tokens automatically after the initial seed.

## Endpoints

| Path | Description |
|------|-------------|
| `/metrics` | Prometheus metrics |
| `/health` | Health check (returns `ok`) |

## License

MIT
