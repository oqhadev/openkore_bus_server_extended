# API Documentation

## Overview

The OpenKore Bus Server Extended provides HTTP API endpoints for external integration with OpenKore clients. The primary use case is integration with the busCommand plugin for remote command execution.

## Base URL

```
http://{host}:{api_port}
```

Default: `http://localhost:9082`

## Authentication

Currently, no authentication is required. Consider implementing authentication for production deployments.

## Endpoints

### POST /bc - Broadcast Command

**Description:** Broadcasts commands to all connected OpenKore clients via the busCommand plugin.

**Method:** `GET`

**URL:** `/bc`

**Query Parameters:**

| Parameter | Type   | Required | Description              | Example           |
| --------- | ------ | -------- | ------------------------ | ----------------- |
| `player`  | string | Yes      | Target player identifier | `all`, `player1`  |
| `comm`    | string | Yes      | Command to execute       | `where`, `s`, `i` |

**Example Request:**

```bash
GET /bc?player=all&comm=where
```

**Success Response:**

```json
{
  "status": "success",
  "message": "Broadcast sent successfully",
  "message_id": "busComm",
  "args": {
    "player": "all",
    "comm": "where"
  },
  "client_count": 2
}
```

**Error Response:**

```json
{
  "error": "Missing required parameters: player and comm",
  "code": 400
}
```

**Status Codes:**

- `200` - Success
- `400` - Bad Request (missing parameters)
- `500` - Server Error (broadcast failed)

### GET /api/status - Server Status

**Description:** Returns current server status and connection information.

**Method:** `GET`

**URL:** `/api/status`

**Parameters:** None

**Example Request:**

```bash
GET /api/status
```

**Success Response:**

```json
{
  "running": true,
  "host": "10.244.244.99",
  "port": 8082,
  "client_count": 2
}
```

**Response Fields:**

| Field          | Type    | Description                 |
| -------------- | ------- | --------------------------- |
| `running`      | boolean | Server running status       |
| `host`         | string  | Server bind address         |
| `port`         | integer | Main bus server port        |
| `client_count` | integer | Number of connected clients |

## busCommand Plugin Integration

### Setup

1. **Configure OpenKore client:**

```perl
# config.txt
busServer_host 10.244.244.99
busServer_port 8082
busAuto 1

# Load busCommand plugin
plugin busCommand.pl
```

2. **Test connection:**

```bash
curl "http://localhost:9082/api/status"
```

### Common Commands

| Command  | Description         | Example                      |
| -------- | ------------------- | ---------------------------- |
| `where`  | Get player location | `/bc?player=all&comm=where`  |
| `s`      | Show status         | `/bc?player=all&comm=s`      |
| `i`      | Show inventory      | `/bc?player=all&comm=i`      |
| `skills` | Show skills         | `/bc?player=all&comm=skills` |
| `stat`   | Show stats          | `/bc?player=all&comm=stat`   |

### Message Flow

```
1. HTTP Request  → /bc?player=all&comm=where
2. API Handler   → Validates parameters
3. Bus Server    → Formats busComm message
4. Broadcast     → Sends to all connected clients
5. OpenKore      → Receives busComm message
6. busCommand    → Executes "where" command
7. Game Client   → Shows location in game
```

## Error Handling

### HTTP Status Codes

| Code | Description           | Common Causes                   |
| ---- | --------------------- | ------------------------------- |
| 200  | OK                    | Request successful              |
| 400  | Bad Request           | Missing or invalid parameters   |
| 404  | Not Found             | Invalid endpoint                |
| 500  | Internal Server Error | Broadcast timeout, server error |

### Error Response Format

All errors return JSON with the following structure:

```json
{
  "error": "Error description",
  "code": 400
}
```

### Common Errors

**Missing Parameters:**

```json
{
  "error": "Missing required parameters: player and comm",
  "code": 400
}
```

**Broadcast Timeout:**

```json
{
  "error": "Broadcast timeout",
  "code": 500
}
```

## Rate Limiting

Currently, no rate limiting is implemented. For production use, consider:

- Implementing request rate limiting
- Adding authentication/authorization
- Monitoring API usage

## CORS Support

CORS headers are enabled for cross-origin requests:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

## Examples

### cURL Examples

```bash
# Basic broadcast
curl "http://localhost:9082/bc?player=all&comm=where"

# Check server status
curl "http://localhost:9082/api/status"

# With error handling
curl -f "http://localhost:9082/bc?player=all&comm=invalid" || echo "Request failed"
```

### Python Examples

```python
import requests

# Broadcast command
response = requests.get("http://localhost:9082/bc", params={
    "player": "all",
    "comm": "where"
})

if response.status_code == 200:
    data = response.json()
    print(f"Broadcast sent to {data['client_count']} clients")
else:
    print(f"Error: {response.json()['error']}")

# Check status
status = requests.get("http://localhost:9082/api/status").json()
print(f"Server running: {status['running']}, Clients: {status['client_count']}")
```

### JavaScript Examples

```javascript
// Broadcast command
async function broadcastCommand(player, command) {
  try {
    const response = await fetch(
      `http://localhost:9082/bc?player=${player}&comm=${command}`
    );
    const data = await response.json();

    if (response.ok) {
      console.log(`Broadcast sent to ${data.client_count} clients`);
    } else {
      console.error(`Error: ${data.error}`);
    }
  } catch (error) {
    console.error("Request failed:", error);
  }
}

// Usage
broadcastCommand("all", "where");
```

## Security Considerations

### Production Deployment

1. **Bind to specific interface:**

```bash
python main.py --bind 127.0.0.1  # Local only
python main.py --bind 10.0.0.1   # Internal network only
```

2. **Use reverse proxy with authentication:**

```nginx
location /api/ {
    auth_basic "OpenKore API";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:9082;
}
```

3. **Firewall rules:**

```bash
# Allow only specific IPs
iptables -A INPUT -p tcp --dport 9082 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 9082 -j DROP
```

### Monitoring

Monitor API usage and server health:

```bash
# Check server logs
tail -f /var/log/openkore-bus-server.log

# Monitor API responses
curl -s "http://localhost:9082/api/status" | jq '.client_count'
```

---

For more information, see the main [README.md](README.md) file.
