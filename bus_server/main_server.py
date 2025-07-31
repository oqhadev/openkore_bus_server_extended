"""
Main bus server implementation
Recreates the OpenKore Bus::Server::MainServer functionality in Python
"""

import asyncio
import time
import configparser
import os
import sys
from typing import Dict, Optional, Set

try:
    from discord_webhook import DiscordWebhook
except ImportError:
    DiscordWebhook = None

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
        self.discord_webhook = self._load_discord_webhook()
    
    def _load_discord_webhook(self) -> Optional[str]:
        """Load Discord webhook URL from config.ini"""
        try:
            config = configparser.ConfigParser()
            
            # Try multiple possible config.ini locations
            possible_paths = [
                # Same directory as executable (for PyInstaller)
                os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)), 'config.ini'),
                # Project root (for development)
                os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini'),
                # Current working directory
                'config.ini'
            ]
            
            config_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            
            if not config_path:
                if not self.quiet:
                    print(f"⚠️ config.ini not found in any of these locations: {possible_paths}")
                return None
            
            config.read(config_path)
            webhook_url = config.get('discord', 'discord_webhook', fallback='')
            
            if not self.quiet:
                print(f"📋 Config loaded from: {config_path}")
            
            return webhook_url if webhook_url else None
        except Exception as e:
            if not self.quiet:
                print(f"⚠️ Failed to load Discord webhook config: {e}")
            return None
    
    async def _send_to_discord(self, message: str) -> bool:
        """Send message to Discord webhook"""
        if not self.discord_webhook or not DiscordWebhook:
            return False
        
        try:
            webhook = DiscordWebhook(url=self.discord_webhook, content=message)
            
            # Use asyncio to run the blocking request in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, webhook.execute)
            
            if response.status_code in [200, 204]:  # Discord webhook success
                if not self.quiet:
                    print(f"📨 Message sent to Discord: {message}")
                return True
            else:
                if not self.quiet:
                    print(f"❌ Discord webhook failed with status {response.status_code}")
                return False
                
        except Exception as e:
            if not self.quiet:
                print(f"❌ Failed to send Discord message: {e}")
            return False
    
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
            # Check if this is a Discord message
            player = args.get("player", "").lower()
            if player == "discord":
                # Send to Discord webhook instead of broadcasting
                comm = args.get("comm", "")
                
                success = await self._send_to_discord(comm)
                if not self.quiet:
                    if success:
                        print(f"📨 Discord message sent from {client.name}: {comm}")
                    else:
                        print(f"❌ Failed to send Discord message from {client.name}")
                return
            
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
