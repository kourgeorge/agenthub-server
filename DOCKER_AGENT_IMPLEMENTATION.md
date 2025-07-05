# Docker Agent Implementation with ACP Protocol

## Overview

This implementation extends the AgentHub server to support Docker-based agent deployment with the Agent Communication Protocol (ACP). The system now supports:

1. **Docker Agent Management**: Automatic container lifecycle management for agents
2. **Agent Communication Protocol (ACP)**: Standardized communication between server and agents
3. **Enhanced CLI**: Commands for Docker agent registration and container management
4. **Dynamic Agent Deployment**: On-demand container startup when agents are needed

## Architecture

### Core Components

#### 1. Docker Agent Manager (`docker_manager.py`)
- **Purpose**: Manages Docker container lifecycle for agents
- **Features**:
  - Container creation and startup
  - Container monitoring and health checks
  - Port management and networking
  - Resource cleanup
  - Container logs and statistics

#### 2. ACP Protocol (`acp_protocol.py`)
- **Purpose**: Standardized communication protocol between server and agents
- **Features**:
  - WebSocket and HTTP fallback support
  - Message-based communication
  - Heartbeat monitoring
  - Connection management
  - Task execution protocol

#### 3. Enhanced Server (`server.py`)
- **Purpose**: Extended AgentHub server with Docker and ACP support
- **Features**:
  - Docker agent registration
  - Automatic container startup
  - ACP protocol integration
  - Container management endpoints
  - Health monitoring

#### 4. Enhanced CLI (`cli.py`)
- **Purpose**: Command-line interface for Docker agent management
- **Features**:
  - Docker agent registration
  - Container lifecycle commands
  - Log viewing
  - Status monitoring

## Docker Agent Registration Process

### Method 1: Using CLI

```bash
# 1. Generate Docker agent configuration
agenthub example-config --output my_agent.yaml --docker

# 2. Register Docker agent
agenthub register-docker-agent \
  --config my_agent.yaml \
  --docker-image myrepo/my-agent:latest \
  --registry-user myuser \
  --registry-pass mypass
```

### Method 2: Using API

```bash
# Register Docker agent via REST API
curl -X POST "http://localhost:8080/agents/register-docker" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "docker_image": "myrepo/my-agent:latest",
    "metadata": {
      "name": "My Agent",
      "description": "Docker-based AI agent",
      "category": "utility",
      "version": "1.0.0",
      "runtime": "managed",
      "protocol": "ACP"
    }
  }'
```

## Agent Communication Protocol (ACP)

### Protocol Overview

ACP is a message-based protocol supporting both WebSocket and HTTP transport:

- **WebSocket**: Real-time bidirectional communication
- **HTTP**: Fallback for polling-based communication
- **JSON Messages**: Structured message format
- **Heartbeat**: Connection health monitoring

### Message Types

```python
class ACPMessageType(str, Enum):
    HANDSHAKE = "handshake"
    HEARTBEAT = "heartbeat"
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    SHUTDOWN = "shutdown"
```

### Message Structure

```json
{
  "type": "task_request",
  "agent_id": "agent-uuid",
  "message_id": "message-uuid",
  "payload": {
    "endpoint": "/process",
    "parameters": {"data": "input"},
    "timeout": 30.0
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Container Management

### Automatic Container Startup

When a user requests a task from a Docker agent:

1. **Check Container Status**: Verify if container is running
2. **Start Container**: If not running, start new container
3. **Wait for Ready**: Wait for agent to become available
4. **Establish Connection**: Connect using ACP protocol
5. **Execute Task**: Send task request to agent

### Container Configuration

Containers are started with:

```python
environment = {
    "AGENTHUB_AGENT_ID": agent_id,
    "AGENTHUB_AGENT_PORT": "8000",
    "AGENTHUB_PROTOCOL": "ACP",
    "AGENTHUB_AGENT_METADATA": json.dumps(metadata)
}
```

### Port Management

- **Dynamic Port Allocation**: Automatically find available ports
- **Port Mapping**: Map container port 8000 to host port
- **Network Creation**: Use dedicated Docker network for agents

## CLI Commands

### Docker Agent Registration

```bash
# Register Docker agent
agenthub register-docker-agent \
  --config agent.yaml \
  --docker-image myrepo/agent:latest

# Generate Docker configuration
agenthub example-config --docker --output docker_agent.yaml
```

### Container Management

```bash
# Start container
agenthub start-container <agent-id>

# Stop container
agenthub stop-container <agent-id>

# List containers
agenthub list-containers

# View container logs
agenthub container-logs <agent-id> --tail 50
```

### Server Management

```bash
# Start server with Docker support
agenthub serve --port 8080 --enable-docker

# Start development server
agenthub dev --port 8080
```

## API Endpoints

### Docker Agent Management

```
POST /agents/register-docker        # Register Docker agent
POST /agents/{id}/start-container   # Start agent container
POST /agents/{id}/stop-container    # Stop agent container
GET  /agents/{id}/container-info    # Get container info
GET  /agents/{id}/container-logs    # Get container logs
GET  /docker/containers             # List all containers
```

### ACP Protocol Management

```
GET  /acp/status                    # Get ACP status
POST /acp/connect/{agent_id}        # Connect to agent via ACP
```

## Agent Implementation Requirements

### Docker Agent Structure

Your Docker agent should implement:

1. **ACP Endpoints** (preferred):
   - `GET /acp/handshake` - Protocol handshake
   - `POST /acp/task` - Task execution
   - `POST /acp/heartbeat` - Health check
   - `WebSocket /acp` - Real-time communication

2. **HTTP Endpoints** (fallback):
   - Standard REST endpoints as defined in metadata

### Environment Variables

Your agent should read these environment variables:

```bash
AGENTHUB_AGENT_ID          # Agent identifier
AGENTHUB_AGENT_PORT        # Port to bind to (default: 8000)
AGENTHUB_PROTOCOL          # Protocol to use (ACP/HTTP)
AGENTHUB_AGENT_METADATA    # Agent metadata JSON
```

### Dockerfile Example

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "agent.py"]
```

## Configuration Examples

### Basic Docker Agent Config

```yaml
name: "My Docker Agent"
description: "AI agent running in Docker"
category: "utility"
version: "1.0.0"
runtime: "managed"
protocol: "ACP"

endpoints:
  - path: "/process"
    method: "POST"
    description: "Process data"
  - path: "/acp/handshake"
    method: "POST"
    description: "ACP handshake"
  - path: "/acp/task"
    method: "POST"
    description: "ACP task execution"

pricing:
  type: "per_request"
  price: 0.01
  currency: "USD"
```

## Task Execution Flow

1. **Task Request**: User submits task via API
2. **Agent Resolution**: Server identifies target agent
3. **Container Check**: Check if agent container is running
4. **Container Start**: Start container if needed
5. **Protocol Detection**: Determine communication protocol (ACP/HTTP)
6. **Connection**: Establish ACP connection or HTTP client
7. **Task Execution**: Send task to agent
8. **Response**: Receive and process response
9. **Result Storage**: Store task result in database

## Benefits

### For Agent Developers
- **Simplified Deployment**: Just provide Docker image
- **Automatic Scaling**: Containers started on demand
- **Standardized Communication**: ACP protocol handles complexity
- **Resource Management**: Automatic cleanup and monitoring

### For Users
- **Transparent Operation**: No need to manage containers
- **Reliable Execution**: Automatic retry and error handling
- **Performance Monitoring**: Built-in metrics and logging
- **Cost Optimization**: Pay-per-use model

### For System Administrators
- **Centralized Management**: Single point of control
- **Resource Monitoring**: Container resource usage
- **Scaling Control**: Configure container limits
- **Security**: Isolated container execution

## Troubleshooting

### Common Issues

1. **Docker Connection Failed**
   - Check Docker daemon is running
   - Verify Docker permissions
   - Check network connectivity

2. **Container Start Failed**
   - Verify Docker image exists
   - Check registry credentials
   - Review container logs

3. **ACP Connection Failed**
   - Check agent implements ACP endpoints
   - Verify port mapping
   - Check firewall settings

### Debug Commands

```bash
# Check Docker status
docker ps -a --filter "label=app=agenthub"

# View container logs
agenthub container-logs <agent-id>

# Check ACP connections
curl http://localhost:8080/acp/status

# Test agent endpoint
curl http://localhost:8001/acp/handshake
```

## Future Enhancements

- **Kubernetes Support**: Deploy agents in Kubernetes
- **Load Balancing**: Multiple instances per agent
- **Auto-scaling**: Scale based on demand
- **Persistent Storage**: Data persistence across restarts
- **Custom Networks**: Advanced networking configuration
- **Resource Limits**: CPU and memory constraints
- **Health Checks**: Advanced health monitoring
- **Metrics Collection**: Detailed performance metrics