#!/usr/bin/env python3
"""
OpenKore Bus Server Extended
Recreated in Python with asyncio

This project recreates the OpenKore bus server functionality in Python,
providing a communication channel for multiple clients to exchange messages.
"""

from bus_server.api_extensions import BusServerWithAPI
import asyncio
import argparse
import sys


async def main():
    """Main entry point for the bus server."""
    parser = argparse.ArgumentParser(description='OpenKore Bus Server Extended')
    parser.add_argument('--port', type=int, default=8082, 
                       help='Port to bind server (default: 8082)')
    parser.add_argument('--bind', type=str, default='10.244.244.99',
                       help='IP address to bind server (default: 10.244.244.99)')
    parser.add_argument('--api-port', type=int, default=None,
                       help='Port for API server (default: main port + 1000)')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress status messages')
    
    args = parser.parse_args()
    
    # Show startup banner (unless quiet mode)
    if not args.quiet:
        print()
        print("=" * 60)
        print("    🚀 OpenKore Bus Server Extended")
        print("         by OqhaDev © 2025")
        print("=" * 60)
        print(f"🌐 Server: {args.bind}:{args.port}")
        if args.api_port:
            print(f"🌐 API Server: {args.bind}:{args.api_port}")
        else:
            print(f"🌐 API Server: {args.bind}:{args.port + 1000}")
        print("⚡ Press Ctrl+C to stop")
        print("=" * 60)
        print()
    
    # Create and start the server with API
    server = BusServerWithAPI(
        port=args.port, 
        bind=args.bind, 
        quiet=args.quiet,
        api_port=args.api_port
    )
    
    try:
        await server.start()
        
        # Keep the server running
        await server.run_forever()
        
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n👋 Shutting down gracefully...")
        await server.shutdown()
    except Exception as e:
        print(f"❌ Server error: {e}", file=sys.stderr)
        await server.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
