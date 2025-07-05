# AgentHub Server

A complete marketplace server for AI agents with database persistence, agent registry, task management, and user authentication. This is a separate project from the core [AgentHub SDK](https://github.com/agenthub/python-sdk) and provides the infrastructure for running an agent marketplace.

## 🚀 Features

- **Agent Registry**: Register and discover agents in a marketplace
- **Task Management**: Queue, execute, and track agent tasks
- **Database Persistence**: SQLite and PostgreSQL support
- **User Management**: API key authentication and credit system
- **Analytics**: Track agent performance and usage metrics
- **RESTful API**: Complete REST API for all operations
- **CLI Tools**: Command-line interface for server management
- **Background Processing**: Asynchronous task execution

## 📦 Architecture

The AgentHub server consists of several key components:

### Core Components

1. **Database Layer** (`agenthub/database.py`)
   - Multi-database support (SQLite, PostgreSQL)
   - Agent metadata and task history
   - User accounts and credits
   - Analytics and performance metrics

2. **Hub Server** (`agenthub/hub_server.py`)
   - FastAPI-based marketplace server
   - Agent registration and discovery
   - Task execution and management
   - User authentication

3. **CLI Interface** (`agenthub/hub_cli.py`)
   - Server management commands
   - Agent registration tools
   - Database administration

## 🏃 Quick Start

### 1. Start Development Server

```bash
# Start development server (no authentication)
python -m agenthub_server.cli dev --port 8080

# Or start with authentication enabled
python -m agenthub_server.cli serve --port 8080 --require-auth
```

### 2. Initialize Database

```bash
# Initialize SQLite database
python -m agenthub_server.cli init-db

# Initialize PostgreSQL database
python -m agenthub_server.cli init-db --database-url "postgresql://user:pass@localhost/agenthub"
```

### 3. Register an Agent

```bash
# Generate example configuration
python -m agenthub_server.cli example-config --output my_agent.yaml

# Register agent from config file
python -m agenthub_server.cli register-agent --config my_agent.yaml
```

### 4. List Agents

```bash
# List all registered agents
python -m agenthub_server.cli list-agents

# Filter by category
python -m agenthub_server.cli list-agents --category utility
```

## 🛠️ CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `serve` | Start production server | `hub_cli serve --port 8080` |
| `dev` | Start development server | `hub_cli dev --port 8080` |
| `init-db` | Initialize database | `hub_cli init-db --force` |
| `register-agent` | Register agent from config | `hub_cli register-agent --config agent.yaml` |
| `list-agents` | List registered agents | `hub_cli list-agents --category research` |
| `agent-info` | Get agent details | `hub_cli agent-info <agent-id>` |
| `create-user` | Create user account | `hub_cli create-user --api-key abc123` |
| `test-connection` | Test server connection | `hub_cli test-connection --url http://localhost:8080` |
| `example-config` | Generate example config | `hub_cli example-config --output agent.yaml` |

## 📋 Agent Configuration

### YAML Configuration Example

```yaml
name: "My AI Agent"
description: "An intelligent agent for data processing"
category: "analytics"
version: "1.0.0"
author: "Your Name"
license: "MIT"
tags:
  - "data"
  - "analytics"
  - "ai"

pricing:
  type: "per_request"
  price: 0.05
  currency: "USD"

capabilities:
  - name: "data_analysis"
    description: "Analyze datasets and generate insights"
    parameters:
      data: 
        type: "array"
        required: true
      format:
        type: "string"
        enum: ["json", "csv"]

endpoints:
  - path: "/analyze"
    method: "POST"
    description: "Analyze data and return insights"
  - path: "/health"
    method: "GET"
    description: "Health check endpoint"

requirements:
  - "pandas>=1.3.0"
  - "numpy>=1.21.0"

documentation_url: "https://example.com/docs"
repository_url: "https://github.com/user/agent"
```

## 🔧 Server Configuration

### Environment Variables

```bash
# Database configuration
export AGENTHUB_DATABASE_URL="sqlite:///agenthub.db"
# or PostgreSQL:
# export AGENTHUB_DATABASE_URL="postgresql://user:pass@localhost/agenthub"

# Server configuration
export AGENTHUB_HOST="0.0.0.0"
export AGENTHUB_PORT="8080"
export AGENTHUB_REQUIRE_AUTH="true"

# Logging
export AGENTHUB_LOG_LEVEL="info"
```

### Programmatic Configuration

```python
from agenthub_server import create_hub_server, serve_hub

# Create server with custom configuration
server = create_hub_server(
    database_url="postgresql://user:pass@localhost/agenthub",
    enable_cors=True,
    require_auth=True
)

# Start server
serve_hub(
    server=server,
    host="0.0.0.0",
    port=8080,
    workers=4
)
```

## 🌐 REST API

### Agent Endpoints

#### Register Agent
```http
POST /agents/register
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "metadata": {
    "name": "My Agent",
    "description": "Agent description",
    "category": "utility",
    "pricing": {"type": "per_request", "price": 0.01}
  }
}
```

#### Search Agents
```http
GET /agents?category=utility&limit=20&offset=0
```

#### Get Agent Details
```http
GET /agents/{agent_id}
```

### Task Endpoints

#### Create Task (Hire Agent)
```http
POST /tasks
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "agent_id": "agent-uuid",
  "endpoint": "/process",
  "parameters": {"data": "input"}
}
```

#### Get Task Status
```http
GET /tasks/{task_id}
```

#### Batch Tasks
```http
POST /tasks/batch
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "tasks": [
    {
      "agent_id": "agent-1",
      "endpoint": "/process",
      "parameters": {"data": "input1"}
    },
    {
      "agent_id": "agent-2", 
      "endpoint": "/analyze",
      "parameters": {"data": "input2"}
    }
  ]
}
```

### Account Endpoints

#### Get Balance
```http
GET /account/balance
Authorization: Bearer <api-key>
```

#### Get Usage History
```http
GET /account/usage?days=30&limit=100
Authorization: Bearer <api-key>
```

### Analytics Endpoints

#### Agent Analytics
```http
GET /agents/{agent_id}/analytics?days=30
Authorization: Bearer <api-key>
```

## 💾 Database Schema

### Tables

- **agents**: Agent metadata and statistics
- **tasks**: Task history and results
- **users**: User accounts and API keys
- **agent_capabilities**: Agent capability definitions
- **agent_endpoints**: Agent endpoint configurations
- **analytics**: Performance metrics and analytics

### Example Queries

```sql
-- Find top performing agents
SELECT name, total_tasks, success_rate, reliability_score
FROM agents 
WHERE status = 'active'
ORDER BY reliability_score DESC, total_tasks DESC
LIMIT 10;

-- Get recent tasks for an agent
SELECT t.*, u.name as user_name
FROM tasks t
LEFT JOIN users u ON t.user_id = u.id
WHERE t.agent_id = 'agent-uuid'
ORDER BY t.created_at DESC
LIMIT 20;

-- Calculate daily revenue
SELECT DATE(created_at) as date, 
       COUNT(*) as tasks, 
       SUM(cost) as revenue
FROM tasks 
WHERE status = 'completed' 
  AND created_at >= DATE('now', '-30 days')
GROUP BY DATE(created_at)
ORDER BY date;
```

## 🔒 Authentication & Security

### API Key Authentication

Create users with API keys:

```bash
# Create user with API key
python -m agenthub.hub_cli create-user \
  --api-key "ah_1234567890abcdef" \
  --email "user@example.com" \
  --name "John Doe" \
  --credits 1000
```

Use API keys in requests:

```bash
curl -H "Authorization: Bearer ah_1234567890abcdef" \
     http://localhost:8080/account/balance
```

### Development Mode

For development, disable authentication:

```python
server = create_hub_server(require_auth=False)
```

## 📊 Monitoring & Analytics

### Agent Performance Metrics

- **Reliability Score**: Overall agent reliability (0-100)
- **Success Rate**: Percentage of successful tasks
- **Average Response Time**: Mean task execution time
- **Total Tasks**: Cumulative task count
- **Last Seen**: Last activity timestamp

### Task Analytics

- **Daily Statistics**: Tasks per day, success rates
- **Cost Analysis**: Revenue tracking and billing
- **Error Tracking**: Failed task analysis
- **Performance Trends**: Response time trends

## 🚀 Deployment

### Production Deployment

```bash
# Production server with multiple workers
python -m agenthub_server.cli serve \
  --host 0.0.0.0 \
  --port 8080 \
  --workers 4 \
  --database-url "postgresql://user:pass@db-host/agenthub" \
  --require-auth \
  --log-level info
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "-m", "agenthub_server.cli", "serve", \
     "--host", "0.0.0.0", "--port", "8080"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  agenthub:
    build: .
    ports:
      - "8080:8080"
    environment:
      AGENTHUB_DATABASE_URL: "postgresql://user:pass@db:5432/agenthub"
    depends_on:
      - db

  db:
    image: postgres:13
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: agenthub
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenthub-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agenthub-server
  template:
    metadata:
      labels:
        app: agenthub-server
    spec:
      containers:
      - name: agenthub
        image: agenthub/server:latest
        ports:
        - containerPort: 8080
        env:
        - name: AGENTHUB_DATABASE_URL
          value: "postgresql://user:pass@postgres:5432/agenthub"
        - name: AGENTHUB_REQUIRE_AUTH
          value: "true"
---
apiVersion: v1
kind: Service
metadata:
  name: agenthub-service
spec:
  selector:
    app: agenthub-server
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

## 🔧 Development

### Running the Demo

```bash
# Run the complete demo
python examples/demo.py
```

This demo will:
1. Create multiple AI agents (calculator, text processor, data analyzer)
2. Start individual agent servers
3. Start the AgentHub marketplace server
4. Register agents with the marketplace
5. Demonstrate hiring agents and task execution
6. Show analytics and monitoring

### Creating Custom Agents

```python
from agenthub import AgentBuilder  # From the core AgentHub SDK
from agenthub_server import create_hub_server

# Create agent using the core SDK
agent = AgentBuilder("my-custom-agent")

@agent.endpoint("/process", description="Process data")
def process_data(request):
    data = request.json.get("data")
    # Process data here
    return {"result": f"Processed: {data}"}

agent.set_metadata({
    "name": "Custom Agent",
    "description": "My custom AI agent",
    "category": "custom",
    "pricing": {"type": "per_request", "price": 0.01}
})

# Register with hub server
server = create_hub_server()
agent_id = server.register_agent_endpoint(
    agent.metadata,
    "http://localhost:8001"
)
```

### Testing

```bash
# Test server connection
python -m agenthub_server.cli test-connection --url http://localhost:8080

# Test with authentication
python -m agenthub_server.cli test-connection \
  --url http://localhost:8080 \
  --api-key ah_1234567890abcdef

# Manual testing with curl
curl http://localhost:8080/health
curl http://localhost:8080/agents
curl -X POST http://localhost:8080/tasks \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"agent-uuid","endpoint":"/process","parameters":{"data":"test"}}'
```

## 🔍 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
lsof -i :8080

# Use different port
python -m agenthub_server.cli serve --port 8081
```

#### Database Connection Issues
```bash
# Check database file permissions (SQLite)
ls -la agenthub.db

# Test PostgreSQL connection
psql postgresql://user:pass@localhost/agenthub -c "SELECT 1;"
```

#### Agent Registration Failures
```bash
# Validate agent configuration
python -c "
from agenthub_server.models import AgentMetadata
import yaml
with open('agent.yaml') as f:
    data = yaml.safe_load(f)
metadata = AgentMetadata(**data)
print('✅ Configuration valid')
"
```

### Debug Mode

Enable debug logging:

```bash
python -m agenthub_server.cli dev --port 8080
# or
export AGENTHUB_LOG_LEVEL=debug
python -m agenthub_server.cli serve
```

### Health Checks

```bash
# Check server health
curl http://localhost:8080/health

# Check database connectivity
python -c "
from agenthub_server.database import init_database
db = init_database('sqlite:///agenthub.db')
print('✅ Database connected')
"
```

## 📚 Examples

See the `examples/` directory for complete examples:

- `demo.py`: Complete marketplace demo
- Agent configuration files in YAML format
- Integration examples with different frameworks

## 🤝 Contributing

To contribute to the AgentHub server:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.