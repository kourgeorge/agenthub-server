"""
CLI commands for AgentHub server management
"""

import click
import asyncio
import json
import yaml
import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path

from .server import create_hub_server, serve_hub, start_development_hub
from .database import init_database, DatabaseManager
from .models import AgentMetadata, AgentRegistration


@click.group()
@click.version_option(version="1.0.0")
def hub_cli():
    """AgentHub Server CLI - Manage AgentHub marketplace server"""
    pass


@hub_cli.command("serve")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8080, help="Port to bind to")
@click.option("--database-url", default="sqlite:///agenthub.db", help="Database URL")
@click.option("--require-auth/--no-auth", default=True, help="Require API key authentication")
@click.option("--cors/--no-cors", default=True, help="Enable CORS")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--workers", default=1, help="Number of worker processes")
@click.option("--log-level", default="info", help="Log level")
def serve_command(host, port, database_url, require_auth, cors, reload, workers, log_level):
    """Start the AgentHub marketplace server"""
    click.echo(f"🚀 Starting AgentHub server on {host}:{port}")
    click.echo(f"📊 Database: {database_url}")
    click.echo(f"🔐 Authentication: {'enabled' if require_auth else 'disabled'}")
    
    try:
        server = create_hub_server(
            database_url=database_url,
            enable_cors=cors,
            require_auth=require_auth
        )
        
        serve_hub(
            server=server,
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            workers=workers
        )
    except KeyboardInterrupt:
        click.echo("\n👋 Shutting down server...")
    except Exception as e:
        click.echo(f"❌ Failed to start server: {e}", err=True)
        sys.exit(1)


@hub_cli.command("dev")
@click.option("--port", default=8080, help="Port to bind to")
@click.option("--database-url", default="sqlite:///agenthub_dev.db", help="Database URL")
def dev_command(port, database_url):
    """Start development server with auto-reload and debug logging"""
    click.echo(f"🔧 Starting AgentHub development server on localhost:{port}")
    click.echo("⚡ Auto-reload enabled")
    click.echo("🐛 Debug logging enabled")
    click.echo("🔓 Authentication disabled")
    
    try:
        start_development_hub(database_url=database_url, port=port)
    except KeyboardInterrupt:
        click.echo("\n👋 Shutting down development server...")
    except Exception as e:
        click.echo(f"❌ Failed to start server: {e}", err=True)
        sys.exit(1)


@hub_cli.command("init-db")
@click.option("--database-url", default="sqlite:///agenthub.db", help="Database URL")
@click.option("--force", is_flag=True, help="Force recreate database")
def init_db_command(database_url, force):
    """Initialize the AgentHub database"""
    click.echo(f"🗄️  Initializing database: {database_url}")
    
    try:
        if force and database_url.startswith("sqlite"):
            # Remove SQLite file if it exists
            db_path = database_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                os.remove(db_path)
                click.echo(f"🗑️  Removed existing database: {db_path}")
        
        db = init_database(database_url)
        click.echo("✅ Database initialized successfully")
        
        # Show database info
        if database_url.startswith("sqlite"):
            db_path = database_url.replace("sqlite:///", "")
            click.echo(f"📁 Database file: {os.path.abspath(db_path)}")
        
    except Exception as e:
        click.echo(f"❌ Failed to initialize database: {e}", err=True)
        sys.exit(1)


@hub_cli.command("register-agent")
@click.option("--config", required=True, help="Agent configuration file (YAML or JSON)")
@click.option("--database-url", default="sqlite:///agenthub.db", help="Database URL")
@click.option("--endpoint-url", help="Agent endpoint URL")
def register_agent_command(config, database_url, endpoint_url):
    """Register an agent from configuration file"""
    click.echo(f"📝 Registering agent from: {config}")
    
    try:
        # Load configuration
        config_path = Path(config)
        if not config_path.exists():
            raise click.ClickException(f"Configuration file not found: {config}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)
        
        # Create metadata
        metadata = AgentMetadata(**config_data)
        
        # Initialize database and register
        db = init_database(database_url)
        agent_id = db.register_agent(metadata, endpoint_url)
        
        click.echo(f"✅ Agent registered successfully!")
        click.echo(f"🆔 Agent ID: {agent_id}")
        click.echo(f"📛 Name: {metadata.name}")
        click.echo(f"📂 Category: {metadata.category}")
        
    except Exception as e:
        click.echo(f"❌ Failed to register agent: {e}", err=True)
        sys.exit(1)


@hub_cli.command("list-agents")
@click.option("--database-url", default="sqlite:///agenthub.db", help="Database URL")
@click.option("--category", help="Filter by category")
@click.option("--limit", default=20, help="Maximum number of agents to show")
def list_agents_command(database_url, category, limit):
    """List registered agents"""
    try:
        db = init_database(database_url)
        agents = db.search_agents(category=category, limit=limit)
        
        if not agents:
            click.echo("📭 No agents found")
            return
        
        click.echo(f"📋 Found {len(agents)} agent(s):")
        click.echo()
        
        for agent in agents:
            click.echo(f"🤖 {agent['name']}")
            click.echo(f"   ID: {agent['id']}")
            click.echo(f"   Category: {agent['category']}")
            click.echo(f"   Version: {agent['version']}")
            click.echo(f"   Status: {agent['status']}")
            click.echo(f"   Tasks: {agent['total_tasks']} (success rate: {agent['success_rate']:.1%})")
            if agent['endpoint_url']:
                click.echo(f"   Endpoint: {agent['endpoint_url']}")
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ Failed to list agents: {e}", err=True)
        sys.exit(1)


@hub_cli.command("agent-info")
@click.argument("agent_id")
@click.option("--database-url", default="sqlite:///agenthub.db", help="Database URL")
def agent_info_command(agent_id, database_url):
    """Get detailed information about an agent"""
    try:
        db = init_database(database_url)
        agent = db.get_agent(agent_id)
        
        if not agent:
            click.echo(f"❌ Agent not found: {agent_id}")
            sys.exit(1)
        
        click.echo(f"🤖 Agent Information")
        click.echo(f"{'='*50}")
        click.echo(f"ID: {agent['id']}")
        click.echo(f"Name: {agent['name']}")
        click.echo(f"Description: {agent['description']}")
        click.echo(f"Category: {agent['category']}")
        click.echo(f"Version: {agent['version']}")
        click.echo(f"Author: {agent['author']}")
        click.echo(f"Status: {agent['status']}")
        click.echo(f"Endpoint URL: {agent['endpoint_url']}")
        click.echo(f"Created: {agent['created_at']}")
        click.echo(f"Last Seen: {agent['last_seen']}")
        click.echo()
        click.echo(f"📊 Statistics:")
        click.echo(f"   Total Tasks: {agent['total_tasks']}")
        click.echo(f"   Success Rate: {agent['success_rate']:.1%}")
        click.echo(f"   Avg Response Time: {agent['average_response_time']:.2f}s")
        click.echo(f"   Reliability Score: {agent['reliability_score']:.1f}/100")
        
        # Show metadata if available
        if agent.get('metadata'):
            click.echo()
            click.echo("📋 Metadata:")
            metadata = agent['metadata']
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            click.echo(json.dumps(metadata, indent=2))
        
    except Exception as e:
        click.echo(f"❌ Failed to get agent info: {e}", err=True)
        sys.exit(1)


@hub_cli.command("create-user")
@click.option("--api-key", required=True, help="API key for the user")
@click.option("--email", help="User email")
@click.option("--name", help="User name")
@click.option("--credits", default=100.0, help="Initial credits")
@click.option("--database-url", default="sqlite:///agenthub.db", help="Database URL")
def create_user_command(api_key, email, name, credits, database_url):
    """Create a new user account"""
    try:
        db = init_database(database_url)
        
        # Check if user already exists
        existing = db.get_user_by_api_key(api_key)
        if existing:
            click.echo(f"❌ User with API key already exists")
            sys.exit(1)
        
        user_id = db.create_user(api_key, email, name)
        
        click.echo(f"✅ User created successfully!")
        click.echo(f"🆔 User ID: {user_id}")
        click.echo(f"🔑 API Key: {api_key}")
        if email:
            click.echo(f"📧 Email: {email}")
        if name:
            click.echo(f"👤 Name: {name}")
        click.echo(f"💰 Credits: {credits}")
        
    except Exception as e:
        click.echo(f"❌ Failed to create user: {e}", err=True)
        sys.exit(1)


@hub_cli.command("test-connection")
@click.option("--url", default="http://localhost:8080", help="Server URL")
@click.option("--api-key", help="API key for authenticated requests")
def test_connection_command(url, api_key):
    """Test connection to AgentHub server"""
    click.echo(f"🔍 Testing connection to: {url}")
    
    try:
        import httpx
        
        # Test health endpoint
        response = httpx.get(f"{url}/health", timeout=10.0)
        response.raise_for_status()
        health_data = response.json()
        
        click.echo("✅ Server is healthy!")
        click.echo(f"📊 Status: {health_data.get('status')}")
        click.echo(f"🤖 Agents: {health_data.get('agents_count', 0)}")
        click.echo(f"⏰ Timestamp: {health_data.get('timestamp')}")
        
        # Test authenticated endpoint if API key provided
        if api_key:
            click.echo()
            click.echo("🔐 Testing authenticated endpoints...")
            
            headers = {"Authorization": f"Bearer {api_key}"}
            response = httpx.get(f"{url}/account/balance", headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                balance_data = response.json()
                click.echo("✅ Authentication successful!")
                click.echo(f"👤 User: {balance_data.get('name', 'Unknown')}")
                click.echo(f"💰 Credits: {balance_data.get('credits', 0)}")
            else:
                click.echo(f"❌ Authentication failed: {response.status_code}")
        
    except httpx.RequestError as e:
        click.echo(f"❌ Connection failed: {e}", err=True)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        click.echo(f"❌ Server error: {e.response.status_code}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@hub_cli.command("example-config")
@click.option("--output", default="example_agent.yaml", help="Output file")
def example_config_command(output):
    """Generate an example agent configuration file"""
    example_config = {
        "name": "Example Agent",
        "description": "An example AI agent for demonstration",
        "category": "utility",
        "version": "1.0.0",
        "author": "AgentHub Team",
        "license": "MIT",
        "tags": ["example", "demo", "utility"],
        "pricing": {
            "type": "per_request",
            "price": 0.01,
            "currency": "USD"
        },
        "capabilities": [
            {
                "name": "greeting",
                "description": "Greet users with personalized messages",
                "parameters": {
                    "name": {"type": "string", "required": True}
                }
            },
            {
                "name": "calculation",
                "description": "Perform basic arithmetic operations",
                "parameters": {
                    "a": {"type": "number", "required": True},
                    "b": {"type": "number", "required": True},
                    "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]}
                }
            }
        ],
        "endpoints": [
            {
                "path": "/greet",
                "method": "POST",
                "description": "Greet a user"
            },
            {
                "path": "/calculate",
                "method": "POST", 
                "description": "Perform calculation"
            }
        ],
        "requirements": ["fastapi", "uvicorn"],
        "documentation_url": "https://example.com/docs",
        "repository_url": "https://github.com/example/agent"
    }
    
    with open(output, 'w') as f:
        yaml.dump(example_config, f, default_flow_style=False, indent=2)
    
    click.echo(f"✅ Example configuration saved to: {output}")
    click.echo("📝 Edit this file and use 'agenthub register-agent --config example_agent.yaml'")


if __name__ == "__main__":
    hub_cli()