# AgentHub Marketplace: Complete Agent Lifecycle Implementation

## Overview

This implementation provides a complete marketplace solution for AI agents with comprehensive lifecycle management, covering all 8 stages of the agent lifecycle from registration to deregistration. The system supports Docker-based agents with the Agent Communication Protocol (ACP) and provides both API and CLI interfaces for customers to manage their agent instances.

## Agent Lifecycle Stages

### 1. 🔄 Registration
**Purpose**: Register agents in the marketplace with metadata and configurations.

**Implementation**:
- Enhanced database storage with lifecycle tracking
- Docker agent support with image management
- Metadata validation and storage
- Automatic lifecycle stage tracking

**API Endpoints**:
```
POST /agents/register          # Standard agent registration
POST /agents/register-docker   # Docker agent registration
```

**CLI Commands**:
```bash
# Register standard agent
agenthub register-agent --config agent.yaml

# Register Docker agent
agenthub register-docker-agent --config agent.yaml --docker-image myrepo/agent:latest
```

### 2. 🔍 Discovery and Selection
**Purpose**: Allow customers to browse and discover available agents.

**Implementation**:
- Enhanced search with marketplace information
- Pricing details and availability
- Performance metrics and customer usage
- Instance count tracking

**API Endpoints**:
```
GET /marketplace/agents        # Enhanced agent discovery
```

**CLI Commands**:
```bash
# Discover agents in marketplace
agenthub marketplace-discover --category utility --limit 10 --api-key your-key
```

**Enhanced Information Provided**:
```json
{
  "marketplace_info": {
    "availability": {
      "available": true,
      "max_instances": 10,
      "current_instances": 3
    },
    "pricing_info": {
      "type": "per_request",
      "price": 0.01,
      "currency": "USD"
    },
    "customer_instances": 2,
    "total_instances": 15,
    "performance_metrics": {
      "average_response_time": 0.5,
      "success_rate": 0.99,
      "availability": 0.999
    }
  }
}
```

### 3. 🚀 Instantiation (Start)
**Purpose**: Create customer-specific agent instances.

**Implementation**:
- Customer-specific agent instances
- Automatic Docker container startup
- ACP protocol connection
- Instance configuration support
- Resource allocation and port management

**API Endpoints**:
```
POST /marketplace/instances    # Create agent instance
```

**CLI Commands**:
```bash
# Create agent instance
agenthub instance-create agent-uuid --api-key your-key --config instance.json
```

**Instance Creation Process**:
1. Validate agent availability
2. Create instance record
3. Start Docker container (if applicable)
4. Establish ACP connection
5. Begin monitoring
6. Return instance details

### 4. ⚡ Active/Running
**Purpose**: Maintain active agent instances ready for task execution.

**Implementation**:
- Continuous instance monitoring
- Resource usage tracking
- Task execution on specific instances
- Health status monitoring
- Performance metrics collection

**API Endpoints**:
```
POST /marketplace/instances/{id}/execute    # Execute task on instance
GET  /marketplace/instances/{id}            # Get instance details
```

**Monitoring Features**:
- CPU and memory usage
- Network utilization
- Task execution count
- Uptime tracking
- Health status checks

### 5. 📊 Monitoring and Maintenance
**Purpose**: Ensure instances run smoothly with proactive maintenance.

**Implementation**:
- Background monitoring tasks (every 30 seconds per instance)
- Global maintenance loop (every 60 seconds)
- Resource usage updates
- Health checks and error tracking
- Billing information updates
- Automatic cleanup of terminated instances

**Monitoring Components**:
- **Instance Monitoring**: Individual instance health and resource tracking
- **Global Maintenance**: Cleanup, billing updates, and system health
- **Error Handling**: Error counting and recovery attempts
- **Performance Tracking**: Response times and success rates

**Health Check Features**:
```json
{
  "health_status": {
    "healthy": true,
    "last_heartbeat": "2024-01-01T12:00:00Z",
    "error_count": 0,
    "last_error": null
  }
}
```

### 6. ⏸️ Pause/Resume
**Purpose**: Allow customers to temporarily pause instances to save costs.

**Implementation**:
- Docker container pause/unpause
- ACP connection management
- Billing pause/resume
- Monitoring state management
- Status tracking

**API Endpoints**:
```
POST /marketplace/instances/{id}/pause     # Pause instance
POST /marketplace/instances/{id}/resume    # Resume instance
```

**CLI Commands**:
```bash
# Pause instance
agenthub instance-pause instance-uuid --api-key your-key

# Resume instance
agenthub instance-resume instance-uuid --api-key your-key
```

**Pause/Resume Process**:
1. **Pause**: Stop monitoring → Disconnect ACP → Pause container → Update status
2. **Resume**: Unpause container → Reconnect ACP → Restart monitoring → Update status

### 7. 🛑 Termination (Stop)
**Purpose**: Cleanly shut down agent instances when no longer needed.

**Implementation**:
- Graceful instance shutdown
- Final billing calculation
- Resource cleanup
- Container removal
- Connection termination

**API Endpoints**:
```
DELETE /marketplace/instances/{id}         # Terminate instance
```

**CLI Commands**:
```bash
# Terminate instance
agenthub instance-terminate instance-uuid --api-key your-key --confirm
```

**Termination Process**:
1. Validate customer ownership
2. Stop monitoring tasks
3. Disconnect ACP connections
4. Stop and remove Docker container
5. Calculate final billing
6. Update instance status to "stopped"

### 8. 🗑️ Deregistration (Optional)
**Purpose**: Remove agents from the marketplace when no longer needed.

**Implementation**:
- Check for active instances
- Prevent deregistration with running instances
- Historical data preservation
- Docker image cleanup
- Lifecycle stage update

**API**: Currently handled through admin interfaces
**Future Enhancement**: Customer-initiated deregistration for owned agents

## Customer Dashboard and Management

### Dashboard Overview
**API Endpoint**: `GET /marketplace/dashboard`

**Features**:
- Instance summary statistics
- Cost and billing overview
- Recent activity
- Resource usage totals

**CLI Command**:
```bash
agenthub dashboard --api-key your-key
```

**Dashboard Information**:
```json
{
  "summary": {
    "total_instances": 5,
    "running_instances": 3,
    "paused_instances": 1,
    "total_cost": 24.50,
    "total_uptime_hours": 120.5
  },
  "billing": {
    "current_month_cost": 24.50,
    "currency": "USD"
  },
  "recent_instances": [...],
  "customer_id": "customer-uuid"
}
```

### Instance Management
**API Endpoints**:
```
GET    /marketplace/instances              # List customer instances
GET    /marketplace/instances/{id}         # Get instance details
POST   /marketplace/instances              # Create instance
POST   /marketplace/instances/{id}/pause   # Pause instance
POST   /marketplace/instances/{id}/resume  # Resume instance
DELETE /marketplace/instances/{id}         # Terminate instance
POST   /marketplace/instances/{id}/execute # Execute task
```

**CLI Commands**:
```bash
# List instances
agenthub instance-list --api-key your-key

# Get instance details
agenthub instance-details instance-uuid --api-key your-key

# Instance lifecycle management
agenthub instance-create agent-uuid --api-key your-key
agenthub instance-pause instance-uuid --api-key your-key
agenthub instance-resume instance-uuid --api-key your-key
agenthub instance-terminate instance-uuid --api-key your-key
```

## Billing and Cost Management

### Billing Models Supported
1. **Per Request**: Fixed cost per task execution
2. **Per Minute**: Time-based billing while running
3. **Per Hour**: Hourly billing while active
4. **Hybrid**: Combination of base cost + usage

### Billing Features
- Real-time cost calculation
- Automatic billing updates
- Final cost calculation on termination
- Historical billing records
- Cost breakdowns by instance

### Cost Structure
```json
{
  "billing_info": {
    "total_cost": 15.75,
    "usage_time": 3600.0,
    "task_executions": 150,
    "cost_breakdown": {
      "base_cost": 5.00,
      "usage_cost": 8.25,
      "task_cost": 2.50
    }
  }
}
```

## Complete Usage Examples

### Agent Developer Workflow
```bash
# 1. Create Docker agent configuration
agenthub example-config --docker --output my-agent.yaml

# 2. Register Docker agent
agenthub register-docker-agent \
  --config my-agent.yaml \
  --docker-image myrepo/my-agent:v1.0 \
  --registry-user myuser \
  --registry-pass mypass

# 3. Start server
agenthub serve --port 8080
```

### Customer Workflow
```bash
# 1. Discover available agents
agenthub marketplace-discover --category "data-analysis" --api-key customer-key

# 2. Create agent instance
agenthub instance-create agent-12345 --api-key customer-key

# 3. Monitor instance
agenthub instance-details instance-67890 --api-key customer-key

# 4. Use the instance (via API)
curl -X POST "http://localhost:8080/marketplace/instances/instance-67890/execute" \
  -H "Authorization: Bearer customer-key" \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "/analyze", "parameters": {"data": "sample"}}'

# 5. Pause when not needed
agenthub instance-pause instance-67890 --api-key customer-key

# 6. Resume when needed
agenthub instance-resume instance-67890 --api-key customer-key

# 7. View dashboard
agenthub dashboard --api-key customer-key

# 8. Terminate when done
agenthub instance-terminate instance-67890 --api-key customer-key --confirm
```

### REST API Examples

#### Discover Agents
```bash
curl "http://localhost:8080/marketplace/agents?category=utility&limit=5" \
  -H "Authorization: Bearer customer-key"
```

#### Create Instance
```bash
curl -X POST "http://localhost:8080/marketplace/instances" \
  -H "Authorization: Bearer customer-key" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-12345",
    "instance_config": {
      "memory_limit": "512M",
      "cpu_limit": "0.5"
    }
  }'
```

#### Execute Task on Instance
```bash
curl -X POST "http://localhost:8080/marketplace/instances/instance-67890/execute" \
  -H "Authorization: Bearer customer-key" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint": "/process",
    "parameters": {"input": "data to process"},
    "timeout": 30
  }'
```

## Architecture Benefits

### For Customers
- **Cost Control**: Pause/resume saves money during idle periods
- **Transparency**: Real-time billing and resource monitoring
- **Flexibility**: Choose from multiple agents and instance configurations
- **Reliability**: Health monitoring and automatic recovery
- **Simplicity**: CLI and API interfaces for all operations

### For Agent Developers
- **Easy Deployment**: Docker-based deployment with automatic management
- **Revenue Tracking**: Built-in billing and usage analytics
- **Scalability**: Multiple customers can use the same agent
- **Monitoring**: Built-in performance and health monitoring
- **Protocol Support**: ACP for reliable communication

### For Platform Operators
- **Resource Efficiency**: Automatic cleanup and resource management
- **Scalability**: Instance-based architecture supports growth
- **Monitoring**: Comprehensive monitoring and alerting
- **Security**: Customer isolation and access control
- **Flexibility**: Support for different agent types and protocols

## Technical Implementation Details

### Key Components
1. **AgentLifecycleManager**: Core lifecycle management
2. **DockerAgentManager**: Container lifecycle management
3. **ACPManager**: Agent Communication Protocol
4. **Enhanced Server**: REST API with marketplace endpoints
5. **Enhanced CLI**: Customer management commands

### Data Models
- **AgentInstance**: Customer-specific agent instance
- **AgentLifecycleStage**: Tracks agent progression through stages
- **AgentInstanceStatus**: Current state of instance
- **Resource Usage**: CPU, memory, network, task metrics
- **Billing Information**: Cost tracking and calculation

### Background Tasks
- **Instance Monitoring**: Per-instance health and resource tracking
- **Global Maintenance**: System-wide cleanup and maintenance
- **Billing Updates**: Real-time cost calculation
- **Health Checks**: Connection and service health monitoring

## Future Enhancements

1. **Auto-scaling**: Automatic instance scaling based on demand
2. **Load Balancing**: Multiple instances per agent with load distribution
3. **Advanced Billing**: Complex pricing models and discounts
4. **Analytics Dashboard**: Web-based customer dashboard
5. **Notifications**: Alerts for instance issues or billing thresholds
6. **Resource Limits**: Configurable CPU/memory constraints
7. **Geographic Distribution**: Multi-region agent deployment
8. **Backup and Recovery**: Instance state backup and restoration

This implementation provides a complete, production-ready marketplace solution that handles the full agent lifecycle with proper customer isolation, billing, monitoring, and management capabilities.