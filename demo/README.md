# AgentHub Marketplace Demo

A comprehensive demonstration of the complete agent lifecycle in the AgentHub marketplace, showcasing all 8 stages from registration to deregistration with Docker-based agents and customer management.

## Demo Overview

This demo creates a realistic marketplace scenario with:
- **3 Sample Agents**: Data Analyzer, Text Processor, and Image Generator
- **2 Sample Customers**: Alice Johnson and Bob Smith
- **Complete Lifecycle**: All 8 stages of agent management
- **Real Docker Containers**: Actual containerized agents
- **Interactive Workflow**: Step-by-step progression through each stage

## What You'll See

### 🔄 Stage 1: Registration
- Automatic Docker image building for 3 sample agents
- Agent registration with metadata and pricing
- Database storage with lifecycle tracking

### 🔍 Stage 2: Discovery and Selection
- Marketplace browsing with enhanced agent information
- Pricing details, availability status, and performance metrics
- Customer-specific view of available agents

### 🚀 Stage 3: Instantiation
- Customer-specific agent instance creation
- Automatic Docker container startup
- Resource allocation and port management
- ACP protocol connection establishment

### ⚡ Stage 4: Active/Running
- Task execution on specific agent instances
- Real processing results from different agent types
- Performance tracking and billing updates

### 📊 Stage 5: Monitoring and Maintenance
- Real-time resource usage monitoring (CPU, memory, uptime)
- Health status checking and error tracking
- ACP protocol connection monitoring
- Automatic billing calculations

### ⏸️ Stage 6: Pause/Resume
- Cost-saving pause functionality with Docker container pause
- Billing pause during idle periods
- Seamless resume with state restoration

### 🛑 Stage 7: Termination
- Graceful instance shutdown with cleanup
- Final billing calculation and reporting
- Resource deallocation and container removal

### 🗑️ Stage 8: Deregistration
- Safe agent removal with active instance checking
- Historical data preservation
- Marketplace catalog updates

### 📊 Customer Dashboard
- Instance overview and usage statistics
- Real-time billing and cost tracking
- Activity monitoring and health status

## Prerequisites

- **Python 3.8+** - Required for AgentHub server
- **Docker** - Must be running for container management
- **Internet Access** - For downloading base Python images
- **10-15 minutes** - Demo duration with explanations

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install fastapi uvicorn httpx pyyaml docker websockets
   ```

2. **Start Docker**
   ```bash
   # Make sure Docker is running
   docker info
   ```

3. **Run the Demo**
   ```bash
   # Simple runner with requirement checks
   python demo/run_demo.py
   
   # Or run directly
   python demo/marketplace_demo.py
   ```

## Demo Features

### Sample Agents Created

1. **Data Analyzer** (`agenthub/data-analyzer:latest`)
   - Category: Analytics
   - Capabilities: Data analysis, sentiment analysis, business insights
   - Price: $0.02 per request

2. **Text Processor** (`agenthub/text-processor:latest`)
   - Category: NLP
   - Capabilities: Language detection, entity extraction, text processing
   - Price: $0.03 per request

3. **Image Generator** (`agenthub/image-generator:latest`)
   - Category: Creative
   - Capabilities: AI image generation, style transfer, descriptions
   - Price: $0.05 per request

### Sample Customers

1. **Alice Johnson** (alice@techcorp.com)
   - API Key: `ak_alice_12345678`
   - Credits: $100.00
   - Role: Primary user for most demos

2. **Bob Smith** (bob@startup.io)
   - API Key: `ak_bob_87654321`
   - Credits: $50.00
   - Role: Used for termination demo

### Sample Tasks Executed

1. **Analytics Task**: "Analyze customer satisfaction data for Q4 2024"
2. **NLP Task**: "Process this contract for key terms and conditions"  
3. **Creative Task**: "Generate a logo for TechCorp startup"
4. **Business Task**: "Review quarterly financial performance metrics"

## Technical Details

### Architecture Demonstrated

- **AgentHub Server**: FastAPI-based marketplace server
- **Docker Manager**: Container lifecycle management
- **ACP Protocol**: Agent Communication Protocol with WebSocket/HTTP
- **Lifecycle Manager**: Complete 8-stage lifecycle tracking
- **Database**: SQLite with agent, customer, and instance data
- **CLI Interface**: Customer management commands

### Agent Implementation

Each demo agent includes:
- **FastAPI Server**: REST API endpoints
- **ACP Support**: Protocol handshake, task execution, heartbeat
- **Category-Specific Processing**: Realistic simulation of different agent types
- **Health Monitoring**: Status reporting and error handling
- **Docker Integration**: Environment variables and container management

### Real-Time Features

- **Resource Monitoring**: CPU, memory, network usage tracking
- **Health Checks**: Connection status and heartbeat monitoring
- **Billing Updates**: Real-time cost calculation and tracking
- **Instance Management**: Pause/resume/terminate with state management

## Interactive Elements

The demo pauses between each stage, allowing you to:
- **Read Output**: Understand what's happening at each step
- **See Results**: View actual task execution results
- **Monitor Resources**: Observe real resource usage
- **Track Costs**: See billing calculations in real-time

## Cleanup

The demo automatically cleans up:
- **Docker Containers**: Stops and removes all created containers
- **Docker Images**: Leaves images for potential reuse
- **Database**: Preserves demo database (`demo_agenthub.db`) for inspection
- **Server Process**: Gracefully shuts down the AgentHub server

## Troubleshooting

### Common Issues

1. **Docker Not Running**
   ```bash
   # Start Docker service
   sudo systemctl start docker  # Linux
   # Or start Docker Desktop on Windows/Mac
   ```

2. **Permission Denied (Docker)**
   ```bash
   # Add user to docker group (Linux)
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

3. **Port Already in Use**
   ```bash
   # Check what's using port 8080
   lsof -i :8080
   # Kill the process or use a different port
   ```

4. **Missing Dependencies**
   ```bash
   # Install all required packages
   pip install -r requirements.txt
   ```

### Demo Logs

The demo creates several log files:
- Server logs in the console output
- Agent container logs accessible via `docker logs`
- Database file: `demo_agenthub.db`

## Extending the Demo

You can modify the demo to:
- **Add More Agents**: Create additional agent types
- **Change Pricing**: Modify pricing models and costs
- **Custom Tasks**: Add different task types and parameters
- **More Customers**: Create additional customer scenarios
- **Advanced Features**: Add auto-scaling, load balancing

## API Testing

While the demo runs, you can also test the API directly:

```bash
# Discover agents
curl "http://localhost:8080/marketplace/agents" \
  -H "Authorization: Bearer ak_alice_12345678"

# Create instance
curl -X POST "http://localhost:8080/marketplace/instances" \
  -H "Authorization: Bearer ak_alice_12345678" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "your-agent-id", "instance_config": {}}'

# Execute task
curl -X POST "http://localhost:8080/marketplace/instances/your-instance-id/execute" \
  -H "Authorization: Bearer ak_alice_12345678" \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "/process", "parameters": {"data": "test"}}'
```

## What This Demo Proves

This demonstration validates that the AgentHub marketplace provides:

✅ **Complete Lifecycle Management** - All 8 stages implemented and working
✅ **Docker Integration** - Full container lifecycle with ACP protocol
✅ **Customer Isolation** - Multiple customers with separate instances
✅ **Real-Time Monitoring** - Resource usage, health, and billing tracking
✅ **Cost Management** - Pause/resume for cost optimization
✅ **Scalable Architecture** - Instance-based model supporting growth
✅ **Developer Experience** - Easy agent registration and deployment
✅ **Customer Experience** - Simple instance management and task execution

The demo showcases a production-ready marketplace solution that handles the complete agent lifecycle with proper customer isolation, billing, monitoring, and management capabilities.