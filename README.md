# 🚀 OpenKore Bus Server Extended

<div align="center">

**A modern Python recreation of the OpenKore bus server**

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Asyncio](https://img.shields.io/badge/Async-IO-green.svg)](https://docs.python.org/3/library/asyncio.html)
[![OpenKore](https://img.shields.io/badge/Compatible-OpenKore-orange.svg)](https://github.com/OpenKore/openkore)

_Built with asyncio for high-performance asynchronous operations_

</div>

## ✨ Features

- 🔥 **High Performance** - Built with asyncio for concurrent connections
- 🌐 **Multi-Client Support** - Handle multiple OpenKore clients simultaneously
- 📡 **Message Broadcasting** - Real-time message exchange between clients
- 🛡️ **Robust Connection Handling** - Automatic client identification and cleanup
- 🎯 **OpenKore Compatible** - Full compatibility with existing OpenKore architecture

## 🚀 Quick Start

```bash
python main.py
```

## ⚙️ Configuration

| Option    | Description     | Default         |
| --------- | --------------- | --------------- |
| `--port`  | Server port     | `8082`          |
| `--bind`  | Bind address    | `10.244.244.99` |
| `--quiet` | Suppress output | `false`         |

## 📋 Usage Examples

```bash
# 🏠 Default configuration
python main.py

# 🌍 Custom port
python main.py --port 9000

# 🔗 Bind to all interfaces
python main.py --bind 0.0.0.0 --port 8082

# 🤫 Silent mode
python main.py --quiet
```

## 📝 Development Roadmap

- [x] ~~simplify console messsage, only show when client join/exit and when client send broadcast, and total client connected, also the error/warning things~~

  - [x] ~~just say "client connected (id)" when get identified~~
  - [x] ~~client (id) broadcast message (arg)~~
  - [x] ~~remove hello things~~

- [ ] implement full api server
- [ ] add api endpoint to broadcast message to all client

## 🔧 Requirements

- **Python 3.7+**
- **No external dependencies** - Pure Python implementation

---

<div align="center">
<strong>Made with ❤️ by OqhaDev © 2025</strong>
</div>
