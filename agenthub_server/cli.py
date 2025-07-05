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


@hub_cli.command("register-docker-agent")
@click.option("--config", required=True, help="Agent configuration file (YAML or JSON)")
@click.option("--docker-image", required=True, help="Docker image name/tag")
@click.option("--database-url", default="sqlite:///agenthub.db", help="Database URL")
@click.option("--registry-user", help="Docker registry username")
@click.option("--registry-pass", help="Docker registry password")
@click.option("--registry-url", help="Docker registry URL")
def register_docker_agent_command(config, docker_image, database_url, registry_user, registry_pass, registry_url):
    """Register a Docker-based agent from configuration file"""
    click.echo(f"🐳 Registering Docker agent from: {config}")
    click.echo(f"📦 Docker image: {docker_image}")
    
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
        
        # Add Docker image to metadata
        config_data["docker_image"] = docker_image
        config_data["runtime"] = "managed"
        config_data["protocol"] = "ACP"
        
        # Create metadata
        metadata = AgentMetadata(**config_data)
        
        # Initialize database and register
        db = init_database(database_url)
        agent_id = db.register_agent(metadata)
        
        # Initialize Docker manager and register
        try:
            from .docker_manager import DockerAgentManager
            docker_manager = DockerAgentManager()
            
            # Prepare registry credentials
            registry_credentials = None
            if registry_user and registry_pass:
                registry_credentials = {
                    "username": registry_user,
                    "password": registry_pass
                }
                if registry_url:
                    registry_credentials["registry"] = registry_url
            
            # Register with Docker manager
            docker_config = docker_manager.register_agent_docker(
                agent_id=agent_id,
                docker_image=docker_image,
                agent_metadata=metadata.dict(),
                registry_credentials=registry_credentials
            )
            
            click.echo(f"✅ Docker agent registered successfully!")
            click.echo(f"🆔 Agent ID: {agent_id}")
            click.echo(f"📛 Name: {metadata.name}")
            click.echo(f"📂 Category: {metadata.category}")
            click.echo(f"🐳 Docker Image: {docker_image}")
            click.echo(f"🔧 Runtime: {metadata.runtime}")
            click.echo(f"📡 Protocol: {metadata.protocol}")
            
        except Exception as e:
            click.echo(f"⚠️  Agent registered in database but Docker registration failed: {e}")
            click.echo(f"🆔 Agent ID: {agent_id}")
            click.echo("💡 You can start the container manually later")
        
    except Exception as e:
        click.echo(f"❌ Failed to register Docker agent: {e}", err=True)
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


@hub_cli.command("start-container")
@click.argument("agent_id")
@click.option("--database-url", default="sqlite:///agenthub.db", help="Database URL")
def start_container_command(agent_id, database_url):
    """Start Docker container for an agent"""
    click.echo(f"🐳 Starting container for agent: {agent_id}")
    
    try:
        # Get agent info
        db = init_database(database_url)
        agent = db.get_agent(agent_id)
        
        if not agent:
            click.echo(f"❌ Agent not found: {agent_id}")
            sys.exit(1)
        
        # Get Docker image from metadata
        metadata = agent.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        
        docker_image = metadata.get("docker_image")
        if not docker_image:
            click.echo(f"❌ Agent {agent_id} does not have Docker image configured")
            sys.exit(1)
        
        # Initialize Docker manager
        from .docker_manager import DockerAgentManager
        docker_manager = DockerAgentManager()
        
        # Start container
        container_info = docker_manager.start_agent_container(
            agent_id=agent_id,
            docker_image=docker_image,
            agent_metadata=metadata
        )
        
        click.echo(f"✅ Container started successfully!")
        click.echo(f"🆔 Container ID: {container_info['container_id']}")
        click.echo(f"📛 Container Name: {container_info['container_name']}")
        click.echo(f"🌐 Endpoint URL: {container_info['endpoint_url']}")
        
    except Exception as e:
        click.echo(f"❌ Failed to start container: {e}", err=True)
        sys.exit(1)


@hub_cli.command("stop-container")
@click.argument("agent_id")
def stop_container_command(agent_id):
    """Stop Docker container for an agent"""
    click.echo(f"🛑 Stopping container for agent: {agent_id}")
    
    try:
        # Initialize Docker manager
        from .docker_manager import DockerAgentManager
        docker_manager = DockerAgentManager()
        
        # Stop container
        success = docker_manager.stop_agent_container(agent_id)
        
        if success:
            click.echo(f"✅ Container stopped successfully!")
        else:
            click.echo(f"❌ No running container found for agent {agent_id}")
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"❌ Failed to stop container: {e}", err=True)
        sys.exit(1)


@hub_cli.command("list-containers")
def list_containers_command():
    """List all running Docker containers"""
    click.echo("🐳 Listing Docker containers...")
    
    try:
        # Initialize Docker manager
        from .docker_manager import DockerAgentManager
        docker_manager = DockerAgentManager()
        
        # List containers
        containers = docker_manager.list_running_containers()
        
        if not containers:
            click.echo("📭 No running containers found")
            return
        
        click.echo(f"📋 Found {len(containers)} running container(s):")
        click.echo()
        
        for container in containers:
            click.echo(f"🐳 {container['container_name']}")
            click.echo(f"   Agent ID: {container['agent_id']}")
            click.echo(f"   Container ID: {container['container_id'][:12]}...")
            click.echo(f"   Docker Image: {container['docker_image']}")
            click.echo(f"   Status: {container['status']}")
            click.echo(f"   Endpoint: {container['endpoint_url']}")
            click.echo(f"   Started: {container['started_at']}")
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ Failed to list containers: {e}", err=True)
        sys.exit(1)


@hub_cli.command("container-logs")
@click.argument("agent_id")
@click.option("--tail", default=100, help="Number of lines to show")
def container_logs_command(agent_id, tail):
    """Get logs from agent container"""
    click.echo(f"📜 Getting logs for agent: {agent_id}")
    
    try:
        # Initialize Docker manager
        from .docker_manager import DockerAgentManager
        docker_manager = DockerAgentManager()
        
        # Get logs
        logs = docker_manager.get_container_logs(agent_id, tail)
        
        if logs:
            click.echo(f"📋 Last {tail} lines of logs:")
            click.echo("=" * 50)
            click.echo(logs)
            click.echo("=" * 50)
        else:
            click.echo(f"❌ No logs found for agent {agent_id}")
        
    except Exception as e:
        click.echo(f"❌ Failed to get logs: {e}", err=True)
        sys.exit(1)


@hub_cli.command("example-config")
@click.option("--output", default="example_agent.yaml", help="Output file")
@click.option("--docker", is_flag=True, help="Generate Docker agent configuration")
def example_config_command(output, docker):
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
    
    if docker:
        example_config["runtime"] = "managed"
        example_config["protocol"] = "ACP"
        example_config["docker_image"] = "example/agent:latest"
        
        # Add ACP endpoints
        example_config["endpoints"].extend([
            {
                "path": "/acp/handshake",
                "method": "POST",
                "description": "ACP handshake"
            },
            {
                "path": "/acp/task",
                "method": "POST",
                "description": "ACP task execution"
            },
            {
                "path": "/acp/heartbeat",
                "method": "POST",
                "description": "ACP heartbeat"
            }
        ])
    
    with open(output, 'w') as f:
        yaml.dump(example_config, f, default_flow_style=False, indent=2)
    
    click.echo(f"✅ Example configuration saved to: {output}")
    
    if docker:
        click.echo("🐳 Docker agent configuration generated")
        click.echo("📝 Edit this file and use 'agenthub register-docker-agent --config example_agent.yaml --docker-image your/image:tag'")
    else:
        click.echo("📝 Edit this file and use 'agenthub register-agent --config example_agent.yaml'")


@hub_cli.command("marketplace-discover")
@click.option("--category", help="Filter by category")
@click.option("--name", help="Filter by name pattern")
@click.option("--limit", default=10, help="Maximum number of agents to show")
@click.option("--api-key", help="API key for authentication")
@click.option("--server-url", default="http://localhost:8080", help="Server URL")
def marketplace_discover_command(category, name, limit, api_key, server_url):
    """Discover agents in the marketplace"""
    click.echo("🔍 Discovering agents in marketplace...")
    
    try:
        import httpx
        
        params = {"limit": limit}
        if category:
            params["category"] = category
        if name:
            params["name"] = name
        
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        response = httpx.get(f"{server_url}/marketplace/agents", params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        agents = data.get("agents", [])
        
        if not agents:
            click.echo("📭 No agents found")
            return
        
        click.echo(f"📋 Found {len(agents)} agent(s):")
        click.echo()
        
        for agent in agents:
            marketplace_info = agent.get("marketplace_info", {})
            pricing_info = marketplace_info.get("pricing_info", {})
            
            click.echo(f"🤖 {agent['name']}")
            click.echo(f"   ID: {agent['id']}")
            click.echo(f"   Category: {agent['category']}")
            click.echo(f"   Description: {agent['description']}")
            click.echo(f"   Version: {agent['version']}")
            click.echo(f"   Price: {pricing_info.get('price', 0)} {pricing_info.get('currency', 'USD')} per {pricing_info.get('type', 'request')}")
            click.echo(f"   Instances: {marketplace_info.get('total_instances', 0)}")
            click.echo(f"   Your Instances: {marketplace_info.get('customer_instances', 0)}")
            click.echo()
        
    except Exception as e:
        click.echo(f"❌ Failed to discover agents: {e}", err=True)
        sys.exit(1)


@hub_cli.command("instance-create")
@click.argument("agent_id")
@click.option("--api-key", required=True, help="API key for authentication")
@click.option("--server-url", default="http://localhost:8080", help="Server URL")
@click.option("--config", help="Instance configuration JSON file")
def instance_create_command(agent_id, api_key, server_url, config):
    """Create a new agent instance"""
    click.echo(f"🚀 Creating instance for agent: {agent_id}")
    
    try:
        import httpx
        
        # Load instance config if provided
        instance_config = {}
        if config:
            config_path = Path(config)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    instance_config = json.load(f)
        
        headers = {"Authorization": f"Bearer {api_key}"}
        data = {
            "agent_id": agent_id,
            "instance_config": instance_config
        }
        
        response = httpx.post(f"{server_url}/marketplace/instances", json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        click.echo(f"✅ Instance created successfully!")
        click.echo(f"🆔 Instance ID: {result['instance_id']}")
        click.echo(f"🤖 Agent ID: {result['agent_id']}")
        click.echo(f"📊 Status: {result['status']}")
        
    except Exception as e:
        click.echo(f"❌ Failed to create instance: {e}", err=True)
        sys.exit(1)


@hub_cli.command("instance-list")
@click.option("--api-key", required=True, help="API key for authentication")
@click.option("--server-url", default="http://localhost:8080", help="Server URL")
def instance_list_command(api_key, server_url):
    """List your agent instances"""
    click.echo("📋 Listing your agent instances...")
    
    try:
        import httpx
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = httpx.get(f"{server_url}/marketplace/instances", headers=headers)
        response.raise_for_status()
        
        data = response.json()
        instances = data.get("instances", [])
        
        if not instances:
            click.echo("📭 No instances found")
            return
        
        click.echo(f"📊 Found {len(instances)} instance(s):")
        click.echo()
        
        for instance in instances:
            billing = instance.get("billing_info", {})
            resource = instance.get("resource_usage", {})
            health = instance.get("health_status", {})
            
            click.echo(f"🔧 {instance['instance_id'][:8]}...")
            click.echo(f"   Agent ID: {instance['agent_id']}")
            click.echo(f"   Status: {instance['status']}")
            click.echo(f"   Created: {instance['created_at']}")
            click.echo(f"   Uptime: {resource.get('uptime', 0)/3600:.2f} hours")
            click.echo(f"   Tasks: {resource.get('task_count', 0)}")
            click.echo(f"   Cost: ${billing.get('total_cost', 0):.2f}")
            click.echo(f"   Health: {'✅' if health.get('healthy', False) else '❌'}")
            click.echo()
        
    except Exception as e:
        click.echo(f"❌ Failed to list instances: {e}", err=True)
        sys.exit(1)


@hub_cli.command("instance-details")
@click.argument("instance_id")
@click.option("--api-key", required=True, help="API key for authentication")
@click.option("--server-url", default="http://localhost:8080", help="Server URL")
def instance_details_command(instance_id, api_key, server_url):
    """Get detailed information about an instance"""
    click.echo(f"🔍 Getting details for instance: {instance_id}")
    
    try:
        import httpx
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = httpx.get(f"{server_url}/marketplace/instances/{instance_id}", headers=headers)
        response.raise_for_status()
        
        instance = response.json()
        
        click.echo(f"🔧 Instance Details")
        click.echo(f"{'='*50}")
        click.echo(f"Instance ID: {instance['instance_id']}")
        click.echo(f"Agent ID: {instance['agent_id']}")
        click.echo(f"Status: {instance['status']}")
        click.echo(f"Created: {instance['created_at']}")
        if instance.get('started_at'):
            click.echo(f"Started: {instance['started_at']}")
        if instance.get('stopped_at'):
            click.echo(f"Stopped: {instance['stopped_at']}")
        
        click.echo()
        click.echo("📊 Resource Usage:")
        resource = instance.get("resource_usage", {})
        click.echo(f"   CPU: {resource.get('cpu_usage', 0):.1f}%")
        click.echo(f"   Memory: {resource.get('memory_usage', 0):.1f}%")
        click.echo(f"   Uptime: {resource.get('uptime', 0)/3600:.2f} hours")
        click.echo(f"   Tasks: {resource.get('task_count', 0)}")
        
        click.echo()
        click.echo("💰 Billing:")
        billing = instance.get("billing_info", {})
        click.echo(f"   Total Cost: ${billing.get('total_cost', 0):.2f}")
        click.echo(f"   Usage Time: {billing.get('usage_time', 0)/3600:.2f} hours")
        click.echo(f"   Task Executions: {billing.get('task_executions', 0)}")
        
        click.echo()
        click.echo("🏥 Health Status:")
        health = instance.get("health_status", {})
        click.echo(f"   Healthy: {'✅' if health.get('healthy', False) else '❌'}")
        if health.get('last_heartbeat'):
            click.echo(f"   Last Heartbeat: {health['last_heartbeat']}")
        if health.get('error_count', 0) > 0:
            click.echo(f"   Error Count: {health['error_count']}")
        
    except Exception as e:
        click.echo(f"❌ Failed to get instance details: {e}", err=True)
        sys.exit(1)


@hub_cli.command("instance-pause")
@click.argument("instance_id")
@click.option("--api-key", required=True, help="API key for authentication")
@click.option("--server-url", default="http://localhost:8080", help="Server URL")
def instance_pause_command(instance_id, api_key, server_url):
    """Pause an agent instance"""
    click.echo(f"⏸️  Pausing instance: {instance_id}")
    
    try:
        import httpx
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = httpx.post(f"{server_url}/marketplace/instances/{instance_id}/pause", headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        click.echo(f"✅ {result['message']}")
        click.echo(f"📊 Status: {result['status']}")
        
    except Exception as e:
        click.echo(f"❌ Failed to pause instance: {e}", err=True)
        sys.exit(1)


@hub_cli.command("instance-resume")
@click.argument("instance_id")
@click.option("--api-key", required=True, help="API key for authentication")
@click.option("--server-url", default="http://localhost:8080", help="Server URL")
def instance_resume_command(instance_id, api_key, server_url):
    """Resume a paused agent instance"""
    click.echo(f"▶️  Resuming instance: {instance_id}")
    
    try:
        import httpx
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = httpx.post(f"{server_url}/marketplace/instances/{instance_id}/resume", headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        click.echo(f"✅ {result['message']}")
        click.echo(f"📊 Status: {result['status']}")
        
    except Exception as e:
        click.echo(f"❌ Failed to resume instance: {e}", err=True)
        sys.exit(1)


@hub_cli.command("instance-terminate")
@click.argument("instance_id")
@click.option("--api-key", required=True, help="API key for authentication")
@click.option("--server-url", default="http://localhost:8080", help="Server URL")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def instance_terminate_command(instance_id, api_key, server_url, confirm):
    """Terminate an agent instance"""
    if not confirm:
        if not click.confirm(f"Are you sure you want to terminate instance {instance_id}?"):
            click.echo("❌ Operation cancelled")
            return
    
    click.echo(f"🛑 Terminating instance: {instance_id}")
    
    try:
        import httpx
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = httpx.delete(f"{server_url}/marketplace/instances/{instance_id}", headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        click.echo(f"✅ {result['message']}")
        click.echo(f"📊 Status: {result['status']}")
        
    except Exception as e:
        click.echo(f"❌ Failed to terminate instance: {e}", err=True)
        sys.exit(1)


@hub_cli.command("dashboard")
@click.option("--api-key", required=True, help="API key for authentication")
@click.option("--server-url", default="http://localhost:8080", help="Server URL")
def dashboard_command(api_key, server_url):
    """Show customer dashboard"""
    click.echo("📊 Customer Dashboard")
    click.echo("=" * 50)
    
    try:
        import httpx
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = httpx.get(f"{server_url}/marketplace/dashboard", headers=headers)
        response.raise_for_status()
        
        data = response.json()
        summary = data.get("summary", {})
        billing = data.get("billing", {})
        recent = data.get("recent_instances", [])
        
        click.echo(f"Customer ID: {data['customer_id']}")
        click.echo()
        
        click.echo("📈 Summary:")
        click.echo(f"   Total Instances: {summary.get('total_instances', 0)}")
        click.echo(f"   Running: {summary.get('running_instances', 0)}")
        click.echo(f"   Paused: {summary.get('paused_instances', 0)}")
        click.echo(f"   Total Uptime: {summary.get('total_uptime_hours', 0):.2f} hours")
        click.echo()
        
        click.echo("💰 Billing:")
        click.echo(f"   Current Month: ${billing.get('current_month_cost', 0):.2f} {billing.get('currency', 'USD')}")
        click.echo()
        
        if recent:
            click.echo("🕒 Recent Instances:")
            for instance in recent[:3]:  # Show top 3
                click.echo(f"   🔧 {instance['instance_id'][:8]}... ({instance['status']})")
        
    except Exception as e:
        click.echo(f"❌ Failed to get dashboard: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    hub_cli()