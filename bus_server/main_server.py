"""
Main bus server implementation
Recreates the OpenKore Bus::Server::MainServer functionality in Python
"""

import asyncio
import time
from typing import Dict, Optional, Set

from .base_server import BaseServer, ClientConnection


class MainServer(BaseServer):
    """
    Main bus server implementation.
    Handles client identification, message routing, and broadcasting.
    """
    
    # Client states
    NOT_IDENTIFIED = "NOT_IDENTIFIED"
    IDENTIFIED = "IDENTIFIED"
    
    def __init__(self, port: int = 0, bind: str = 'localhost', quiet: bool = False):
        super().__init__(port, bind, quiet)
        self.last_connection_log = time.time()
    
    async def on_client_new(self, client: ClientConnection) -> None:
        """Handle new client connection - send initial HELLO."""
        client.state = self.NOT_IDENTIFIED
        
        # Send HELLO message to initiate handshake
        success = await client.send("HELLO", {"yourID": client.client_id})
        if not success and not self.quiet:
            print(f"❌ Failed to send HELLO to client {client.client_id}")
    
    async def on_client_exit(self, client: ClientConnection) -> None:
        """Handle client disconnection - notify other clients."""
        if not self.quiet:
            print(f"[{time.strftime('%H:%M:%S')}] Client exited: {client.name} (ID: {client.client_id})")
        
        if client.state == self.IDENTIFIED:
            await self.broadcast("LEAVE", {"clientID": client.client_id}, exclude={client.client_id})
    
    async def on_client_data(self, client: ClientConnection, message_id: str, args: dict) -> None:
        """Handle incoming messages from clients."""
        # Show message_id, client name, and the full message content
        if not self.quiet:
            print(f"📨 {message_id} from {client.name}\n    Content: {args}")
        
        # Handle known message types
        handler_name = f"process_{message_id}"
        
        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            try:
                await handler(client, args)
            except Exception as e:
                if not self.quiet:
                    print(f"⚠️ Handler {handler_name} failed: {e}")
                self.logger.error(f"Handler {handler_name} failed: {e}")
        else:
            # Handle message routing
            await self._route_message(client, message_id, args)
    
    async def _route_message(self, client: ClientConnection, message_id: str, args: dict) -> None:
        """Route messages between clients."""
        # System messages that should not be broadcasted
        system_messages = {'HELLO', 'LIST_CLIENTS', 'JOIN', 'LEAVE', 'DELIVERY_FAILED', 'CLIENT_NOT_FOUND'}
        
        if "TO" in args:
            # Private message - send to specific client
            recipient_id = args["TO"]
            if recipient_id in self.clients:
                recipient = self.clients[recipient_id]
                args["FROM"] = client.client_id
                
                if not self.quiet:
                    print(f"[{time.strftime('%H:%M:%S')}] Routing private message to {recipient.name}")
                
                success = await recipient.send(message_id, args)
                if not success:
                    # Delivery failed
                    if not self.quiet:
                        print(f"[{time.strftime('%H:%M:%S')}] Message delivery failed to {recipient_id}")
                    reply_args = {"clientID": recipient_id}
                    if "SEQ" in args:
                        reply_args["SEQ"] = args["SEQ"]
                    reply_args["IRY"] = 1
                    await client.send("DELIVERY_FAILED", reply_args)
                else:
                    if not self.quiet:
                        print(f"[{time.strftime('%H:%M:%S')}] Message delivered successfully")
            else:
                # Client not found
                if not self.quiet:
                    print(f"[{time.strftime('%H:%M:%S')}] Client {recipient_id} not found")
                reply_args = {"clientID": recipient_id}
                if "SEQ" in args:
                    reply_args["SEQ"] = args["SEQ"]
                reply_args["IRY"] = 1
                await client.send("CLIENT_NOT_FOUND", reply_args)
        else:
            # Broadcast message to all clients (except system messages)
            args["FROM"] = client.client_id
            
            # Count eligible clients for broadcasting
            eligible_clients = [c for c in self.clients.values() 
                              if c.state == self.IDENTIFIED and 
                              not c.private_only and 
                              c.client_id != client.client_id]
            
            if not self.quiet and len(eligible_clients) > 0:
                print(f"📡 Broadcasting {message_id} to {len(eligible_clients)} clients")
                
            await self.broadcast(message_id, args, exclude={client.client_id})
    
    async def process_HELLO(self, client: ClientConnection, args: dict) -> None:
        """Handle client identification."""
        if not isinstance(args, dict):
            if not self.quiet:
                print(f"❌ Client {client.client_id} sent invalid HELLO arguments")
            self.logger.error(f"Client {client.client_id} sent invalid HELLO arguments")
            client.close()
            return
        
        if client.state == self.NOT_IDENTIFIED:
            # New client identification
            client.user_agent = args.get("userAgent", "Unknown")
            client.private_only = args.get("privateOnly", False)
            client.name = f"{client.user_agent}:{client.client_id}"
            client.state = self.IDENTIFIED
            
            if not self.quiet:
                print(f"✅ Client identified: {client.name}")
            
            # Broadcast JOIN message
            join_args = {
                "clientID": client.client_id,
                "name": client.name,
                "userAgent": client.user_agent,
                "host": str(client.address)
            }
            
            await self.broadcast("JOIN", join_args, exclude={client.client_id})
            
            if not self.quiet:
                print(f"📢 Broadcasted JOIN for client {client.client_id}")
                
        else:
            # Client already identified
            if not self.quiet:
                print(f"⚠️ Client {client.client_id} already identified")
            self.logger.error(f"Client {client.client_id} sent duplicate HELLO")
            client.close()
    
    async def process_LIST_CLIENTS(self, client: ClientConnection, args: dict) -> None:
        """Handle client list request."""
        if not isinstance(args, dict):
            self.logger.error(f"Client {client.client_id} sent invalid LIST_CLIENTS arguments")
            client.close()
            return
        
        # Build client list
        reply_args = {}
        client_count = 0
        
        for cid, c in self.clients.items():
            if c.state == self.IDENTIFIED:
                reply_args[f"client{client_count}"] = cid
                reply_args[f"clientUserAgent{client_count}"] = c.user_agent
                client_count += 1
        
        reply_args["count"] = client_count
        if "SEQ" in args:
            reply_args["SEQ"] = args["SEQ"]
        reply_args["IRY"] = 1
        
        await client.send("LIST_CLIENTS", reply_args)
    
    async def broadcast(self, message_id: str, args: Optional[dict] = None, exclude: Optional[Set[str]] = None) -> None:
        """
        Broadcast a message to all identified clients.
        Excludes clients that are not identified or have privateOnly set.
        """
        if exclude is None:
            exclude = set()
        
        eligible_clients = []
        for client_id, client in self.clients.items():
            if (client_id not in exclude and 
                client.state == self.IDENTIFIED and 
                not client.private_only):
                eligible_clients.append(client)
        
        for client in eligible_clients:
            await client.send(message_id, args)
    
    async def log_connections_periodically(self) -> None:
        """Periodically log active connection count."""
        while self.running:
            await asyncio.sleep(30)  # Log every 30 seconds
            if not self.quiet and time.time() - self.last_connection_log > 30:
                total_clients = len(self.clients)
                identified_clients = len([c for c in self.clients.values() if c.state == self.IDENTIFIED])
                
                if total_clients > 0:
                    print(f"🔗 {identified_clients}/{total_clients} clients connected")
                
                self.last_connection_log = time.time()
    
    async def run_forever(self) -> None:
        """Run the server with periodic connection logging."""
        # Start the connection logging task
        log_task = asyncio.create_task(self.log_connections_periodically())
        
        try:
            # Run the main server
            await super().run_forever()
        finally:
            log_task.cancel()
            try:
                await log_task
            except asyncio.CancelledError:
                pass
    
    async def send_to_client(self, client_id: str, message_id: str, args: Optional[dict] = None) -> bool:
        """Send a message to a specific client by ID."""
        if client_id in self.clients:
            client = self.clients[client_id]
            if client.state == self.IDENTIFIED:
                return await client.send(message_id, args)
        return False
