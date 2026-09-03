#!/usr/bin/env python3
"""
MCP Server for Admin Dashboard (Production Version - HTTP)
Listens on port 8080

For local testing:
  python3 mcp_server_prod.py
  http://localhost:8080

On production server:
  python3 mcp_server_prod.py --host 0.0.0.0 --port 8080

Or via systemd:
  systemctl start mcp-server-prod
"""

import json
import os
import sys
import requests
import argparse
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()

ADMIN_URL = os.getenv("ADMIN_URL", "http://adminka.loc")
MCP_PORT = int(os.getenv("MCP_PORT", 8080))
MCP_HOST = os.getenv("MCP_HOST", "localhost")

app = Flask(__name__)

class MCPServer:
    def __init__(self):
        self.admin_url = ADMIN_URL
        self.allowed_models = [
            'Aggregator', 'Geo', 'Operator', 'BusinessNumber',
            'Service', 'Offer', 'Partner', 'Affiliate', 'Unsubscription'
        ]

    def call_admin(self, endpoint: str, params: dict, token: str) -> dict:
        """Makes a request to the admin dashboard"""
        try:
            url = f"{self.admin_url}/api/mcp/{endpoint}"
            params['token'] = token
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 401:
                return {"error": "Invalid or inactive token"}

            if response.status_code != 200:
                return {"error": f"Admin API returned status {response.status_code}: {response.text}"}

            return response.json()
        except requests.exceptions.ConnectionError:
            return {"error": f"Cannot connect to admin at {self.admin_url}"}
        except requests.RequestException as e:
            return {"error": f"Failed to connect to admin: {str(e)}"}

    def query_data(self, model: str, select: str = "*", where: str = "",
                  join: str = "", limit: int = 50, offset: int = 0, token: str = "") -> dict:
        """Universal data query endpoint"""
        if not token:
            return {"error": "Token is required"}

        if model not in self.allowed_models:
            return {"error": f"Model '{model}' not allowed. Allowed: {', '.join(self.allowed_models)}"}

        params = {
            'model': model,
            'select': select,
            'limit': limit,
            'offset': offset,
        }
        if where:
            params['where'] = where
        if join:
            params['join'] = join

        return self.call_admin('query', params, token)

    def build_tools_list(self) -> list:
        """Builds a list of available tools"""
        return [
            {
                "name": "query_data",
                "description": "Universal data query from admin dashboard. Allows querying any model with filters.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "MCP user token (obtain in admin dashboard)"
                        },
                        "model": {
                            "type": "string",
                            "enum": self.allowed_models,
                            "description": "Data model"
                        },
                        "select": {
                            "type": "string",
                            "description": "Fields to select (all available by default). Example: 'id,name,rate'"
                        },
                        "where": {
                            "type": "string",
                            "description": "Filter conditions. Example: 'id_geo:33,status:active'"
                        },
                        "join": {
                            "type": "string",
                            "description": "Join another table. Example: 'operator_names,operators.id_operator_name,operator_names.id'"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default: 50)"
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Offset (for pagination)"
                        },
                    },
                    "required": ["token", "model"],
                }
            }
        ]

mcp = MCPServer()

# ==================== MCP HTTP Endpoints ====================

@app.route('/mcp/initialize', methods=['POST'])
def mcp_initialize():
    """MCP initialization endpoint"""
    data = request.json or {}
    return jsonify({
        "protocolVersion": data.get("protocolVersion", "2024-11-05"),
        "capabilities": {"tools": {}},
        "serverInfo": {
            "name": "admin-mcp",
            "version": "1.0.0",
        },
    })

@app.route('/mcp/tools/list', methods=['GET', 'POST'])
def mcp_tools_list():
    """List of available tools"""
    return jsonify({
        "tools": mcp.build_tools_list()
    })

@app.route('/mcp/tools/call', methods=['POST'])
def mcp_tools_call():
    """Call a tool"""
    data = request.json or {}
    tool_name = data.get("name")
    tool_args = data.get("arguments") or {}

    if tool_name == "query_data":
        token = tool_args.get("token")
        model = tool_args.get("model")
        select = tool_args.get("select", "*")
        where = tool_args.get("where", "")
        join = tool_args.get("join", "")
        limit = tool_args.get("limit", 50)
        offset = tool_args.get("offset", 0)

        result = mcp.query_data(
            model=model,
            select=select,
            where=where,
            join=join,
            limit=limit,
            offset=offset,
            token=token
        )
        is_error = isinstance(result, dict) and "error" in result

        return jsonify({
            "content": [{
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2),
            }],
            "isError": is_error,
        })
    else:
        return jsonify({"error": f"Unknown tool: {tool_name}"}), 400

# ==================== Info Endpoints ====================

@app.route('/health', methods=['GET'])
def health():
    """Server health check endpoint"""
    try:
        # Check admin dashboard availability
        response = requests.get(f"{mcp.admin_url}/api/mcp/query?model=Geo&limit=1&token=test", timeout=5)
        admin_status = "connected" if response.status_code in [400, 401] else "disconnected"
    except:
        admin_status = "disconnected"

    return jsonify({
        "status": "ok",
        "admin_url": mcp.admin_url,
        "admin_status": admin_status,
        "version": "1.0.0"
    })

@app.route('/', methods=['GET'])
def index():
    """Information page"""
    return jsonify({
        "name": "Admin MCP Server (Production)",
        "version": "1.0.0",
        "admin_url": mcp.admin_url,
        "endpoints": {
            "initialize": "POST /mcp/initialize",
            "tools_list": "GET /mcp/tools/list",
            "tools_call": "POST /mcp/tools/call",
            "health": "GET /health"
        },
        "docs": "https://github.com/anthropics/model-context-protocol"
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MCP Server for Admin')
    parser.add_argument('--host', default=MCP_HOST, help=f'Host (default: {MCP_HOST})')
    parser.add_argument('--port', type=int, default=MCP_PORT, help=f'Port (default: {MCP_PORT})')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    print(f"Starting Admin MCP Server")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Admin URL: {mcp.admin_url}")
    print(f"  Health check: http://{args.host}:{args.port}/health")
    print(f"  API docs: http://{args.host}:{args.port}/")
    print("")

    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\nServer stopped")
        sys.exit(0)
