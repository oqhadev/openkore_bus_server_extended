<div align="center">

# 🚀 OpenKore Bus Server Extended

</div>

<div align="center">

**A modern Python recreation of the OpenKore bus server with HTTP API for busCommand plugin integration**

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Asyncio](https://img.shields.io/badge/Async-IO-green.svg)](https://docs.python.org/3/library/asyncio.html)
[![OpenKore](https://img.shields.io/badge/Compatible-OpenKore-orange.svg)](https://github.com/OpenKore/openkore)

_Built with asyncio for high-performance asynchronous operations and HTTP API integration_

</div>

## ✨ Features

- 🌐 **HTTP API** - RESTful endpoints for external integrations
- 🎮 **busCommand Plugin Integration** - Direct integration with OpenKore's busCommand plugin
- 📨 **Discord Webhook Integration** - Send messages directly to Discord channels

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure Discord webhook (optional)
cp config.ini.example config.ini
# Edit config.ini with your Discord webhook URL

# Install and activate plugin busCommand
# https://github.com/marcelothebuilder/openkore-busCommands
# In OpenKore config.txt:
busServer_host 10.244.244.99
busServer_port 8082
busAuto 1

# Start server
python main.py
```

## 🌐 HTTP API Integration

### Broadcast Command Endpoint

Send commands to all connected OpenKore clients via HTTP:

```bash
# Broadcast "where" command to all players
curl "http://localhost:9082/bc?player=all&comm=where"

# Send status command
curl "http://localhost:9082/bc?player=all&comm=s"

# Send inventory command
curl "http://localhost:9082/bc?player=all&comm=i"
```

## 📨 Discord Webhook Integration

Send messages directly to Discord channels when using `player=discord`:

### Setup Discord Webhook

1. **Create webhook configuration:**
```bash
# Copy example config
cp config.ini.example config.ini

# Edit config.ini and add your Discord webhook URL
[discord]
discord_webhook=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

### Send to Discord

```bash
# OpenKore command format
bus discord Hello Discord!
```

## ⚙️ Configuration

| Option       | Description     | Default         |
| ------------ | --------------- | --------------- |
| `--port`     | Bus server port | `8082`          |
| `--bind`     | Bind address    | `10.244.244.99` |
| `--api-port` | HTTP API port   | `port + 1000`   |
| `--quiet`    | Suppress output | `false`         |

## 📋 Usage Examples

```bash
# 🏠 Default configuration (Bus: 8082, API: 9082)
python main.py

# 🌍 Custom ports
python main.py --port 8083 --api-port 8084

# 🔗 Bind to all interfaces
python main.py --bind 0.0.0.0 --port 8082

# 🤫 Silent mode
python main.py --quiet
```

````

## � API Endpoints

### `/bc` - Broadcast Command
Primary endpoint for busCommand plugin integration. Sends commands to all connected OpenKore clients.

**Parameters:**
- `player` (required): Target player identifier (e.g., "all", "player1")
- `comm` (required): Command to broadcast (e.g., "where", "s", "i")

**Examples:**
```bash
# Get player locations
curl "http://localhost:9082/bc?player=all&comm=where"

# Check player status
curl "http://localhost:9082/bc?player=all&comm=s"

# View inventory
curl "http://localhost:9082/bc?player=all&comm=i"
````

### `/api/status` - Server Status

Returns current server status and connection information.

```bash
curl "http://localhost:9082/api/status"
```

**Response:**

```json
{
  "running": true,
  "host": "10.244.244.99",
  "port": 8082,
  "client_count": 2
}
```

## 🎮 busCommand Plugin Integration

The `/bc` endpoint is specifically designed for OpenKore's busCommand plugin integration:

1. **HTTP Request** → `/bc?player=all&comm=where`
2. **Bus Message** → `busComm {player: "all", comm: "where"}`
3. **OpenKore Client** → Executes "where" command

### Message Flow

```
External App → HTTP API → Bus Server → OpenKore Clients → OpenKore Commands
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   External      │    │   Bus Server     │    │   OpenKore      │
│   Applications  │────│   Extended       │────│   Clients       │
│                 │    │                  │    │                 │
│ • Web Apps      │    │ • TCP Server     │    │ • Player 1      │
│ • Scripts       │    │ • HTTP API       │    │ • Player 2      │
│ • Monitoring    │    │ • Message Router │    │ • Player N      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Requirements

- **Python 3.x**

---

<div align="center">
<strong>Made with ❤️ by OqhaDev © 2025</strong>
</div>
