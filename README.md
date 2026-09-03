# MCP Server for Admin Dashboard

An MCP server that provides access to admin dashboard data through the Claude MCP protocol.

## Local Development

### Requirements
- Python 3.8+
- pip

### Installation

```bash
cd /Users/svitlanataran/mcp_server
pip install -r requirements.txt
```

### Running

**Terminal 1: Run Admin Dashboard**
```bash
cd /Users/svitlanataran/PhpstormProjects/admin_upformobile
php artisan serve
# or use another startup method
# http://adminka.loc should be accessible
```

**Terminal 2: Run MCP Server**
```bash
cd /Users/svitlanataran/mcp_server
python3 mcp_server.py
```

### Testing

1. Make sure the admin dashboard is available at `http://adminka.loc/`
2. Create an MCP token in the admin dashboard (interface will be added later)
3. Connect the MCP server in Claude:
   - Type: stdio
   - Command: `python3`
   - Arguments: `/Users/svitlanataran/mcp_server/mcp_server.py`

## Production Deployment

### Server Structure

```
/home/deploy/
├─ admin_upformobile/ (Laravel admin dashboard)
└─ mcp_server/ (this project)
   ├─ mcp_server.py
   ├─ requirements.txt
   └─ .env (modified for production)
```

### Setup

1. Copy the `mcp_server` folder to the remote server

2. Install dependencies:
```bash
cd /home/deploy/mcp_server
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and edit it:
```
# If admin dashboard is on the same server
ADMIN_URL=http://localhost:8000
# or
ADMIN_URL=http://127.0.0.1:8000

# If admin dashboard is on a different server
ADMIN_URL=http://admin.example.com
```

### Running with Systemd (Recommended)

Create the file `/etc/systemd/system/mcp-server.service`:

```ini
[Unit]
Description=Admin MCP Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/deploy/mcp_server
ExecStart=/usr/bin/python3 /home/deploy/mcp_server/mcp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then run:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-server
sudo systemctl start mcp-server
sudo systemctl status mcp-server
```

### Running with Supervisor (Alternative)

Create the file `/etc/supervisor/conf.d/mcp-server.conf`:

```ini
[program:mcp-server]
command=/usr/bin/python3 /home/deploy/mcp_server/mcp_server.py
directory=/home/deploy/mcp_server
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/mcp-server.log
```

Then run:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start mcp-server
```

### Viewing Logs

```bash
# Systemd
sudo journalctl -u mcp-server -f

# Supervisor
tail -f /var/log/mcp-server.log
```

## How It Works

1. Claude connects to the MCP server (via stdio or another protocol)
2. The MCP server receives a request (e.g., "get the list of geos")
3. The MCP server sends an HTTP request to the admin dashboard: `GET http://adminka.loc/api/mcp/geos?token=...`
4. The admin dashboard verifies the token and responds with JSON
5. The MCP server parses the JSON and sends the response to Claude
6. Claude formats and displays the response to the user

## Tokens

Tokens are created in the admin dashboard and used to authenticate MCP requests.

Each token:
- Is tied to a specific user
- Has a unique string value
- Can be activated/deactivated
- Provides access only to data available to that user in the admin dashboard

## Project Links

- **Upwork Project**: [MCP Integrations — Connecting Internal Systems to LLMs](https://www.upwork.com)
