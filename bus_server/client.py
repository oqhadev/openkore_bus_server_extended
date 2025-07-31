"""
Simple client implementation for connecting to the OpenKore Bus Server Extended
Compatible with the original OpenKore bus protocol
"""

import asyncio
import json
import socket
from typing import Any, Dict, Optional, Callable

from .messages import MessageParser, serialize


class SimpleClient:
    """
    Simple client for connecting to the bus server.
    Similar to OpenKore's Bus::SimpleClient but using asyncio.
    """
    
    def __init__(self, host: str = '10.244.244.99', port: int = 8082):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.parser = MessageParser()
        self.connected = False
        self.client_id: Optional[str] = None
        self.message_callbacks: Dict[str, Callable] = {}
    
    async def connect(self) -> bool:
        """Connect to the bus server."""
        try:
            print(f"🔌 Connecting to {self.host}:{self.port}...")
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.connected = True
            print(f"✅ Connected to bus server")
            
            # Set socket options to prevent disconnection
            sock = self.writer.get_extra_info('socket')
            if sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the bus server."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.connected = False
        self.client_id = None
        print("👋 Disconnected from bus server")
    
    async def send(self, message_id: str, args: Optional[Dict[str, Any]] = None) -> bool:
        """Send a message to the bus server."""
        if not self.connected or not self.writer:
            return False
        
        try:
            data = serialize(message_id, args)
            
            # Check if writer is still valid
            if self.writer.is_closing():
                return False
            
            self.writer.write(data)
            await self.writer.drain()
            return True
        except (ConnectionResetError, BrokenPipeError):
            await self.disconnect()
            return False
        except Exception as e:
            print(f"❌ Send failed: {e}")
            await self.disconnect()
            return False

    async def read_next(self) -> Optional[tuple[str, Dict[str, Any]]]:
        """Read the next message from the server."""
        if not self.connected or not self.reader:
            return None
        
        try:
            # Check if we have a complete message in buffer
            result = self.parser.read_next()
            if result:
                return result
            
            # Read more data with timeout
            try:
                data = await asyncio.wait_for(self.reader.read(32768), timeout=30.0)
            except asyncio.TimeoutError:
                return None
                
            if not data:
                await self.disconnect()
                return None
            
            self.parser.add(data)
            return self.parser.read_next()
            
        except ConnectionResetError:
            await self.disconnect()
            return None
        except Exception as e:
            print(f"❌ Read failed: {e}")
            await self.disconnect()
            return None
    
    async def identify(self, user_agent: str = "PythonClient", private_only: bool = False) -> bool:
        """Identify with the bus server."""
        if not self.connected:
            return False
        
        # Wait for initial HELLO from server
        result = await self.read_next()
        if result and result[0] == "HELLO":
            server_hello_args = result[1]
            self.client_id = server_hello_args.get("yourID")
            
            print(f"🆔 Server assigned ID: {self.client_id}")
            
            # Send our HELLO response
            hello_args = {
                "userAgent": user_agent,
                "privateOnly": private_only
            }
            
            success = await self.send("HELLO", hello_args)
            if success:
                print(f"✅ Identified as {user_agent}")
                return True
            else:
                print(f"❌ Failed to identify")
                return False
        else:
            print(f"❌ Expected HELLO from server, got: {result}")
            return False
    
    async def list_clients(self) -> Optional[Dict[str, Any]]:
        """Request a list of connected clients."""
        if not await self.send("LIST_CLIENTS", {}):
            return None
        
        # Wait for response
        result = await self.read_next()
        if result and result[0] == "LIST_CLIENTS":
            return result[1]
        
        return None
    
    async def message_loop(self) -> None:
        """Main message handling loop."""
        while self.connected:
            result = await self.read_next()
            if result:
                message_id, args = result
                await self._handle_message(message_id, args)
            else:
                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
    
    async def _handle_message(self, message_id: str, args: Dict[str, Any]) -> None:
        """Handle incoming messages."""
        # Check if this is a broadcast message from another client
        if "FROM" in args and args["FROM"] != self.client_id:
            print(f"📢 Broadcast from client {args['FROM']}: {message_id}")
        else:
            print(f"📨 Received message: {message_id}")
            
        if isinstance(args, dict):
            for key, value in args.items():
                print(f"  {key}: {value}")
        print("-" * 30)
        
        # Call registered callback if exists
        if message_id in self.message_callbacks:
            await self.message_callbacks[message_id](args)
    
    def register_callback(self, message_id: str, callback: Callable) -> None:
        """Register a callback for a specific message type."""
        self.message_callbacks[message_id] = callback
