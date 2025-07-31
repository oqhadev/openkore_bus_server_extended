"""
API extensions for the OpenKore Bus server
Demonstrates how to add REST API functionality
"""

import asyncio
import json
from typing import Dict, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from urllib.parse import urlparse, parse_qs

from .main_server import MainServer


class BusAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for bus server endpoints."""
    
    def __init__(self, bus_server: MainServer, *args, **kwargs):
        self.bus_server = bus_server
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        if path == '/api/status':
            self._handle_status()
        elif path == '/bc':
            self._handle_broadcast_get(query_params)
        else:
            self._send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/broadcast':
            self._handle_broadcast()
        elif path == '/api/message':
            self._handle_message()
        else:
            self._send_error(404, "Not Found")
    
    def _handle_status(self):
        """Return server status."""
        status = {
            "running": self.bus_server.running,
            "host": self.bus_server.host,
            "port": self.bus_server.port,
            "client_count": len(self.bus_server.clients)
        }
        self._send_json_response(status)
    
    def _handle_broadcast_get(self, query_params: Dict):
        """Handle broadcast message via GET request with query parameters."""
        try:
            # Extract parameters from query
            player = query_params.get('player', [''])[0]
            comm = query_params.get('comm', [''])[0]
            
            if not player or not comm:
                self._send_error(400, "Missing required parameters: player and comm")
                return
            
            # Build message arguments - keep OpenKore format
            args = {
                'player': player,
                'comm': comm
            }
            
            # Add any additional query parameters
            for key, values in query_params.items():
                if key not in ['player', 'comm'] and values:
                    args[key] = values[0]
            
            message_id = 'busComm'  # Use OpenKore standard message ID
            
            # Log the API call
            if not self.bus_server.quiet:
                print(f"🌐 API Broadcast: player={player}, comm={comm}")
            
            # Schedule the broadcast in the event loop
            try:
                # Get the event loop from the main thread
                if hasattr(self.bus_server, '_event_loop') and self.bus_server._event_loop:
                    loop = self.bus_server._event_loop
                else:
                    # Fallback: try to get the running loop
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        # Create a new event loop if none exists
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                
                future = asyncio.run_coroutine_threadsafe(
                    self.bus_server.broadcast(message_id, args),
                    loop
                )
                future.result(timeout=2.0)  # Wait up to 2 seconds
                
                client_count = len([c for c in self.bus_server.clients.values() 
                                  if c.state == self.bus_server.IDENTIFIED])
                
                response = {
                    "status": "success",
                    "message": "Broadcast sent successfully",
                    "message_id": message_id,
                    "args": args,
                    "client_count": client_count
                }
                
                if not self.bus_server.quiet:
                    print(f"📡 API broadcast sent to {client_count} clients")
                
                self._send_json_response(response)
                
            except asyncio.TimeoutError:
                self._send_error(500, "Broadcast timeout")
            except Exception as e:
                self._send_error(500, f"Broadcast failed: {str(e)}")
                
        except Exception as e:
            self._send_error(400, f"Bad Request: {str(e)}")
    
    
    def _handle_broadcast(self):
        """Handle broadcast message via API."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            message_id = data.get('message_id', 'API_BROADCAST')
            args = data.get('args', {})
            
            # Schedule the broadcast in the event loop
            asyncio.run_coroutine_threadsafe(
                self.bus_server.broadcast(message_id, args),
                asyncio.get_event_loop()
            )
            
            self._send_json_response({"status": "sent", "message_id": message_id})
            
        except Exception as e:
            self._send_error(400, f"Bad Request: {str(e)}")
    
    def _handle_message(self):
        """Handle private message via API."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            client_id = data.get('client_id')
            message_id = data.get('message_id', 'API_MESSAGE')
            args = data.get('args', {})
            
            if not client_id:
                self._send_error(400, "client_id required")
                return
            
            # Schedule the message send in the event loop
            future = asyncio.run_coroutine_threadsafe(
                self.bus_server.send_to_client(client_id, message_id, args),
                self.bus_server._event_loop if hasattr(self.bus_server, '_event_loop') else asyncio.get_event_loop()
            )
            
            success = future.result(timeout=1.0)
            
            if success:
                self._send_json_response({"status": "sent", "client_id": client_id})
            else:
                self._send_error(404, "Client not found")
                
        except Exception as e:
            self._send_error(400, f"Bad Request: {str(e)}")
    
    def _send_json_response(self, data: Dict):
        """Send JSON response."""
        response = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response)
    
    def _send_error(self, code: int, message: str):
        """Send error response."""
        error_response = {"error": message, "code": code}
        response = json.dumps(error_response).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response)


class BusServerWithAPI(MainServer):
    """Extended bus server with REST API functionality."""
    
    def __init__(self, port: int = 0, bind: str = 'localhost', quiet: bool = False, 
                 api_port: Optional[int] = None):
        super().__init__(port, bind, quiet)
        self.api_port = api_port or (port + 1000) if port > 0 else 9080
        self.api_server: Optional[HTTPServer] = None
        self.api_thread: Optional[threading.Thread] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def start(self) -> None:
        """Start the bus server and API server."""
        # Store the event loop reference for API handler
        self._event_loop = asyncio.get_running_loop()
        await super().start()
        self._start_api_server()
    
    async def shutdown(self) -> None:
        """Shutdown both servers."""
        self._stop_api_server()
        await super().shutdown()
    
    def _start_api_server(self) -> None:
        """Start the REST API server in a separate thread."""
        if not self.quiet:
            print(f"🌐 Starting API server on {self.host}:{self.api_port}")
        
        def handler_factory(*args, **kwargs):
            return BusAPIHandler(self, *args, **kwargs)
        
        # Use the same host as the main server
        self.api_server = HTTPServer((self.host, self.api_port), handler_factory)
        self.api_thread = threading.Thread(target=self.api_server.serve_forever)
        self.api_thread.daemon = True
        self.api_thread.start()
    
    def _stop_api_server(self) -> None:
        """Stop the REST API server."""
        if self.api_server:
            self.api_server.shutdown()
            self.api_server.server_close()
        
        if self.api_thread and self.api_thread.is_alive():
            self.api_thread.join(timeout=5.0)
