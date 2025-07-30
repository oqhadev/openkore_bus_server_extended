"""
Base server implementation for the OpenKore Bus API
Handles TCP connections and client management using asyncio
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from abc import ABC, abstractmethod

from .messages import MessageParser, serialize


class ClientConnection:
    """Represents a client connection to the bus server."""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, client_id: str):
        self.reader = reader
        self.writer = writer
        self.client_id = client_id
        self.parser = MessageParser()
        self.address = writer.get_extra_info('peername', 'unknown')
        self.user_agent = "Unknown"
        self.private_only = False
        self.state = "NOT_IDENTIFIED"
        self.name = f"Unknown:{client_id}"
    
    async def send(self, message_id: str, args: Optional[dict] = None) -> bool:
        """Send a message to this client."""
        try:
            data = serialize(message_id, args)
            
            # Check if writer is still connected
            if self.writer.is_closing():
                return False
            
            self.writer.write(data)
            await self.writer.drain()
            return True
        except ConnectionResetError:
            print(f"[CONNECTION RESET] Failed to send to client {self.client_id} - connection reset")
            return False
        except BrokenPipeError:
            print(f"[BROKEN PIPE] Failed to send to client {self.client_id} - broken pipe")
            return False
        except Exception as e:
            print(f"[SEND ERROR] Failed to send message to client {self.client_id}: {e}")
            logging.error(f"Failed to send message to client {self.client_id}: {e}")
            return False
    
    def close(self):
        """Close the client connection."""
        try:
            self.writer.close()
        except Exception:
            pass
    
    async def wait_closed(self):
        """Wait for the connection to be closed."""
        try:
            await self.writer.wait_closed()
        except Exception:
            pass


class BaseServer(ABC):
    """
    Base server implementation for handling TCP connections.
    Similar to OpenKore's Base::Server but using asyncio.
    """
    
    def __init__(self, port: int = 0, bind: str = 'localhost', quiet: bool = False):
        self.port = port
        self.bind = bind
        self.quiet = quiet
        self.host = bind
        self.server: Optional[asyncio.Server] = None
        self.clients: Dict[str, ClientConnection] = {}
        self.max_client_id = 0
        self.running = False
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the server."""
        logger = logging.getLogger(f"{self.__class__.__name__}")
        if not self.quiet:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.ERROR)
        return logger
    
    async def start(self) -> None:
        """Start the server."""
        self.server = await asyncio.start_server(
            self._handle_client,
            self.bind,
            self.port
        )
        
        # Get the actual port if auto-assigned
        addr = self.server.sockets[0].getsockname()
        self.host = addr[0]
        self.port = addr[1]
        self.running = True
        
        self.logger.info(f"🌐 Server started on {self.host}:{self.port}")
        print(f"🚀 Bus server started at {self.host}:{self.port}")
    
    async def shutdown(self) -> None:
        """Shutdown the server and close all connections."""
        self.running = False
        
        # Close all client connections
        for client in list(self.clients.values()):
            await self._disconnect_client(client.client_id)
        
        # Close the server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        self.logger.info(f"❌ Server shutdown complete")
    
    async def run_forever(self) -> None:
        """Keep the server running forever."""
        if self.server:
            async with self.server:
                await self.server.serve_forever()
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle a new client connection."""
        client_id = str(self.max_client_id)
        self.max_client_id += 1
        
        client = ClientConnection(reader, writer, client_id)
        self.clients[client_id] = client
        
        self.logger.info(f"👋 New client connected: {client.address} (ID: {client_id})")
        
        try:
            await self.on_client_new(client)
            await self._client_message_loop(client)
        except Exception as e:
            self.logger.error(f"Error handling client {client_id}: {e}")
        finally:
            await self._disconnect_client(client_id)
    
    async def _client_message_loop(self, client: ClientConnection) -> None:
        """Main message handling loop for a client."""
        while self.running and client.client_id in self.clients:
            try:
                # Read data from client with timeout
                try:
                    data = await asyncio.wait_for(client.reader.read(32768), timeout=60.0)
                except asyncio.TimeoutError:
                    # Client idle for too long, keep connection alive
                    continue
                
                if not data:
                    break
                
                # Add to parser and process messages
                client.parser.add(data)
                
                while True:
                    result = client.parser.read_next()
                    if result is None:
                        break
                    
                    message_id, args = result
                    await self.on_client_data(client, message_id, args)
                    
            except asyncio.CancelledError:
                if not self.quiet:
                    print(f"[CANCELLED] Client {client.client_id} task cancelled")
                break
            except ConnectionResetError:
                if not self.quiet:
                    print(f"[CONNECTION RESET] Client {client.client_id} connection reset by peer")
                break
            except Exception as e:
                if not self.quiet:
                    print(f"[ERROR] Client {client.client_id} message loop error: {e}")
                self.logger.error(f"Error in message loop for client {client.client_id}: {e}")
                break
    
    async def _disconnect_client(self, client_id: str) -> None:
        """Disconnect a client and clean up."""
        if client_id in self.clients:
            client = self.clients[client_id]
            self.logger.info(f"👋 Client disconnected: {client.address} (ID: {client_id})")
            
            try:
                await self.on_client_exit(client)
            except Exception as e:
                self.logger.error(f"Error in on_client_exit for {client_id}: {e}")
            
            client.close()
            await client.wait_closed()
            del self.clients[client_id]
    
    async def send_to_client(self, client_id: str, message_id: str, args: Optional[dict] = None) -> bool:
        """Send a message to a specific client."""
        if client_id in self.clients:
            return await self.clients[client_id].send(message_id, args)
        return False
    
    async def broadcast(self, message_id: str, args: Optional[dict] = None, exclude: Optional[Set[str]] = None) -> None:
        """Broadcast a message to all connected clients."""
        if exclude is None:
            exclude = set()
        
        for client_id, client in self.clients.items():
            if client_id not in exclude:
                await client.send(message_id, args)
    
    def get_client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self.clients)
    
    def get_client_list(self) -> List[str]:
        """Get a list of all client IDs."""
        return list(self.clients.keys())
    
    # Abstract methods that subclasses must implement
    @abstractmethod
    async def on_client_new(self, client: ClientConnection) -> None:
        """Called when a new client connects."""
        pass
    
    @abstractmethod
    async def on_client_exit(self, client: ClientConnection) -> None:
        """Called when a client disconnects."""
        pass
    
    @abstractmethod
    async def on_client_data(self, client: ClientConnection, message_id: str, args: dict) -> None:
        """Called when a client sends a message."""
        pass
