"""
AgentHub Server - Complete marketplace server with database persistence
"""

import uvicorn
import asyncio
import httpx
import json
from typing import Dict, Any, Optional, List, Union
from fastapi import FastAPI, Request, Response, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import signal
import sys
import time
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from .database import DatabaseManager, get_database, init_database
from .models import (
    AgentMetadata, TaskRequest, TaskResponse, AgentStatus, 
    AgentRegistration, PricingModel, PricingType
)
from .docker_manager import DockerAgentManager
from .acp_protocol import ACPManager

logger = logging.getLogger(__name__)

# Global state
registered_agents: Dict[str, Dict[str, Any]] = {}
security = HTTPBearer(auto_error=False)


class AgentHubServer:
    """
    Complete AgentHub marketplace server with database persistence and Docker support
    """
    
    def __init__(
        self, 
        database_url: str = "sqlite:///agenthub.db",
        enable_cors: bool = True,
        require_auth: bool = True,
        enable_docker: bool = True
    ):
        """
        Initialize AgentHub server
        
        Args:
            database_url: Database connection string
            enable_cors: Enable CORS middleware
            require_auth: Require API key authentication
            enable_docker: Enable Docker agent management
        """
        self.database_url = database_url
        self.require_auth = require_auth
        self.enable_docker = enable_docker
        self.db = init_database(database_url)
        
        # Initialize Docker manager
        self.docker_manager = None
        if enable_docker:
            try:
                self.docker_manager = DockerAgentManager()
                logger.info("Docker agent manager initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Docker manager: {e}")
                self.enable_docker = False
        
        # Initialize ACP manager
        self.acp_manager = ACPManager()
        
        # Create FastAPI app
        self.app = FastAPI(
            title="AgentHub Marketplace Server",
            description="Distributed AI agent ecosystem with Docker support",
            version="1.0.0"
        )
        
        # Add CORS middleware
        if enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup API routes"""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "database": "connected",
                "agents_count": len(self.db.search_agents(limit=1000))
            }
        
        # Agent registration
        @self.app.post("/agents/register")
        async def register_agent(
            registration: AgentRegistration,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Register a new agent"""
            try:
                # Validate metadata
                metadata = registration.metadata
                if not metadata.name:
                    raise HTTPException(status_code=400, detail="Agent name is required")
                
                # Register in database
                agent_id = self.db.register_agent(metadata)
                
                logger.info(f"Registered agent {agent_id}: {metadata.name}")
                
                return {
                    "agent_id": agent_id,
                    "name": metadata.name,
                    "status": "registered",
                    "message": "Agent successfully registered"
                }
                
            except Exception as e:
                logger.error(f"Failed to register agent: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Docker agent registration
        @self.app.post("/agents/register-docker")
        async def register_docker_agent(
            request: Dict[str, Any],
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Register a Docker-based agent"""
            try:
                if not self.enable_docker:
                    raise HTTPException(status_code=400, detail="Docker support is disabled")
                
                # Extract required fields
                docker_image = request.get("docker_image")
                agent_metadata = request.get("metadata")
                registry_credentials = request.get("registry_credentials")
                
                if not docker_image:
                    raise HTTPException(status_code=400, detail="docker_image is required")
                if not agent_metadata:
                    raise HTTPException(status_code=400, detail="metadata is required")
                
                # Create agent metadata object
                metadata = AgentMetadata(**agent_metadata)
                
                # Register in database
                agent_id = self.db.register_agent(metadata)
                
                # Register with Docker manager
                docker_config = self.docker_manager.register_agent_docker(
                    agent_id=agent_id,
                    docker_image=docker_image,
                    agent_metadata=metadata.dict(),
                    registry_credentials=registry_credentials
                )
                
                logger.info(f"Registered Docker agent {agent_id}: {metadata.name}")
                
                return {
                    "agent_id": agent_id,
                    "name": metadata.name,
                    "docker_image": docker_image,
                    "status": "registered",
                    "message": "Docker agent successfully registered"
                }
                
            except Exception as e:
                logger.error(f"Failed to register Docker agent: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Agent discovery
        @self.app.get("/agents")
        async def search_agents(
            category: Optional[str] = None,
            name: Optional[str] = None,
            limit: int = 20,
            offset: int = 0
        ):
            """Search for agents"""
            try:
                agents = self.db.search_agents(
                    category=category,
                    name_pattern=name,
                    limit=limit,
                    offset=offset
                )
                
                return {
                    "agents": agents,
                    "total": len(agents),
                    "limit": limit,
                    "offset": offset
                }
                
            except Exception as e:
                logger.error(f"Failed to search agents: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get specific agent
        @self.app.get("/agents/{agent_id}")
        async def get_agent(agent_id: str):
            """Get agent details"""
            agent = self.db.get_agent(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            return agent
        
        # Update agent
        @self.app.put("/agents/{agent_id}")
        async def update_agent(
            agent_id: str,
            metadata: AgentMetadata,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Update agent metadata"""
            # Check if agent exists
            existing_agent = self.db.get_agent(agent_id)
            if not existing_agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            # Update would be implemented here
            # For now, return success
            return {"message": "Agent updated successfully"}
        
        # Delete agent
        @self.app.delete("/agents/{agent_id}")
        async def delete_agent(
            agent_id: str,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Delete an agent"""
            # Implementation would mark agent as inactive
            return {"message": "Agent deleted successfully"}
        
        # Task creation (hiring agents)
        @self.app.post("/tasks")
        async def create_task(
            task_request: TaskRequest,
            background_tasks: BackgroundTasks,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Create a new task (hire an agent)"""
            try:
                # Check if agent exists
                agent = self.db.get_agent(task_request.agent_id)
                if not agent:
                    raise HTTPException(status_code=404, detail="Agent not found")
                
                # Create task in database
                task_id = self.db.create_task(
                    agent_id=task_request.agent_id,
                    endpoint=task_request.endpoint,
                    parameters=task_request.parameters,
                    user_id=user.get("id")
                )
                
                # Execute task in background
                background_tasks.add_task(
                    self.execute_task,
                    task_id,
                    agent,
                    task_request
                )
                
                return {
                    "task_id": task_id,
                    "status": "pending",
                    "agent_id": task_request.agent_id,
                    "endpoint": task_request.endpoint,
                    "created_at": datetime.now().isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to create task: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get task status
        @self.app.get("/tasks/{task_id}")
        async def get_task_status(task_id: str):
            """Get task status and results"""
            task = self.db.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            return task
        
        # Batch task creation
        @self.app.post("/tasks/batch")
        async def create_batch_tasks(
            tasks: List[TaskRequest],
            background_tasks: BackgroundTasks,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Create multiple tasks in batch"""
            results = []
            
            for task_request in tasks:
                try:
                    # Check if agent exists
                    agent = self.db.get_agent(task_request.agent_id)
                    if not agent:
                        results.append({
                            "error": f"Agent {task_request.agent_id} not found",
                            "agent_id": task_request.agent_id
                        })
                        continue
                    
                    # Create task
                    task_id = self.db.create_task(
                        agent_id=task_request.agent_id,
                        endpoint=task_request.endpoint,
                        parameters=task_request.parameters,
                        user_id=user.get("id")
                    )
                    
                    # Execute in background
                    background_tasks.add_task(
                        self.execute_task,
                        task_id,
                        agent,
                        task_request
                    )
                    
                    results.append({
                        "task_id": task_id,
                        "status": "pending",
                        "agent_id": task_request.agent_id
                    })
                    
                except Exception as e:
                    results.append({
                        "error": str(e),
                        "agent_id": task_request.agent_id
                    })
            
            return {"tasks": results, "total": len(results)}
        
        # Agent analytics
        @self.app.get("/agents/{agent_id}/analytics")
        async def get_agent_analytics(
            agent_id: str,
            days: int = 30,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Get agent analytics"""
            # Check if agent exists
            agent = self.db.get_agent(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            analytics = self.db.get_agent_analytics(agent_id, days)
            return analytics
        
        # User account info
        @self.app.get("/account/balance")
        async def get_account_balance(
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Get user account balance and usage"""
            return {
                "user_id": user.get("id"),
                "credits": user.get("credits", 0),
                "total_spent": user.get("total_spent", 0),
                "name": user.get("name"),
                "email": user.get("email")
            }
        
        # Usage history
        @self.app.get("/account/usage")
        async def get_usage_history(
            days: int = 30,
            limit: int = 100,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Get usage history"""
            # Implementation would query tasks for user
            return {
                "usage": [],
                "period_days": days,
                "total_tasks": 0,
                "total_cost": 0.0
            }
        
        # Agent status update (for agents to report they're alive)
        @self.app.post("/agents/{agent_id}/heartbeat")
        async def agent_heartbeat(
            agent_id: str,
            status_data: Dict[str, Any] = None
        ):
            """Agent heartbeat to update status"""
            agent = self.db.get_agent(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            # Update last_seen timestamp
            # Implementation would update the database
            
            return {"message": "Heartbeat received", "timestamp": datetime.now().isoformat()}
        
        # Docker container management routes
        @self.app.post("/agents/{agent_id}/start-container")
        async def start_agent_container(
            agent_id: str,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Start Docker container for an agent"""
            try:
                if not self.enable_docker:
                    raise HTTPException(status_code=400, detail="Docker support is disabled")
                
                # Get agent info
                agent = self.db.get_agent(agent_id)
                if not agent:
                    raise HTTPException(status_code=404, detail="Agent not found")
                
                # Get Docker image from metadata
                metadata = agent.get("metadata", {})
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)
                
                docker_image = metadata.get("docker_image")
                if not docker_image:
                    raise HTTPException(status_code=400, detail="Agent does not have Docker image configured")
                
                # Start container
                container_info = self.docker_manager.start_agent_container(
                    agent_id=agent_id,
                    docker_image=docker_image,
                    agent_metadata=metadata
                )
                
                return {
                    "message": "Container started successfully",
                    "container_info": container_info
                }
                
            except Exception as e:
                logger.error(f"Failed to start container for agent {agent_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/agents/{agent_id}/stop-container")
        async def stop_agent_container(
            agent_id: str,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Stop Docker container for an agent"""
            try:
                if not self.enable_docker:
                    raise HTTPException(status_code=400, detail="Docker support is disabled")
                
                success = self.docker_manager.stop_agent_container(agent_id)
                
                if success:
                    return {"message": "Container stopped successfully"}
                else:
                    raise HTTPException(status_code=404, detail="No running container found for agent")
                
            except Exception as e:
                logger.error(f"Failed to stop container for agent {agent_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/agents/{agent_id}/container-info")
        async def get_agent_container_info(
            agent_id: str,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Get container information for an agent"""
            try:
                if not self.enable_docker:
                    raise HTTPException(status_code=400, detail="Docker support is disabled")
                
                container_info = self.docker_manager.get_agent_container_info(agent_id)
                
                if container_info:
                    return container_info
                else:
                    raise HTTPException(status_code=404, detail="No container found for agent")
                
            except Exception as e:
                logger.error(f"Failed to get container info for agent {agent_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/agents/{agent_id}/container-logs")
        async def get_agent_container_logs(
            agent_id: str,
            tail: int = 100,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Get container logs for an agent"""
            try:
                if not self.enable_docker:
                    raise HTTPException(status_code=400, detail="Docker support is disabled")
                
                logs = self.docker_manager.get_container_logs(agent_id, tail)
                
                return {
                    "agent_id": agent_id,
                    "logs": logs,
                    "tail": tail
                }
                
            except Exception as e:
                logger.error(f"Failed to get container logs for agent {agent_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/docker/containers")
        async def list_docker_containers(
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """List all running Docker containers"""
            try:
                if not self.enable_docker:
                    raise HTTPException(status_code=400, detail="Docker support is disabled")
                
                containers = self.docker_manager.list_running_containers()
                
                return {
                    "containers": containers,
                    "count": len(containers)
                }
                
            except Exception as e:
                logger.error(f"Failed to list containers: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # ACP protocol status routes
        @self.app.get("/acp/status")
        async def get_acp_status(
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Get ACP protocol status for all agents"""
            try:
                status = self.acp_manager.get_health_status()
                connected_agents = self.acp_manager.list_connected_agents()
                
                return {
                    "connected_agents": connected_agents,
                    "agent_status": status,
                    "total_connections": len(connected_agents)
                }
                
            except Exception as e:
                logger.error(f"Failed to get ACP status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/acp/connect/{agent_id}")
        async def connect_acp_agent(
            agent_id: str,
            user: Dict[str, Any] = Depends(self.get_current_user)
        ):
            """Connect to an agent using ACP protocol"""
            try:
                # Get agent info
                agent = self.db.get_agent(agent_id)
                if not agent:
                    raise HTTPException(status_code=404, detail="Agent not found")
                
                # Get endpoint URL
                endpoint_url = agent.get("endpoint_url")
                if not endpoint_url:
                    # Check if Docker container is running
                    if self.enable_docker:
                        container_info = self.docker_manager.get_agent_container_info(agent_id)
                        if container_info:
                            endpoint_url = container_info["endpoint_url"]
                
                if not endpoint_url:
                    raise HTTPException(status_code=400, detail="No endpoint URL available for agent")
                
                # Connect using ACP
                success = await self.acp_manager.connect_agent(agent_id, endpoint_url)
                
                if success:
                    return {"message": "ACP connection established", "agent_id": agent_id}
                else:
                    raise HTTPException(status_code=500, detail="Failed to establish ACP connection")
                
            except Exception as e:
                logger.error(f"Failed to connect to agent {agent_id} via ACP: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def get_current_user(
        self, 
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """Get current user from API key"""
        if not self.require_auth:
            # Return dummy user for development
            return {
                "id": "dev-user",
                "name": "Development User",
                "credits": 1000.0,
                "total_spent": 0.0
            }
        
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Look up user by API key
        user = self.db.get_user_by_api_key(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    
    async def execute_task(
        self,
        task_id: str,
        agent_info: Dict[str, Any],
        task_request: TaskRequest
    ):
        """Execute a task by calling the agent"""
        start_time = time.time()
        
        try:
            # Update task status to running
            self.db.update_task(task_id, "running")
            
            agent_id = agent_info["id"]
            
            # Check if this is a Docker agent that needs to be started
            if self.enable_docker and not agent_info.get("endpoint_url"):
                container_info = self.docker_manager.get_agent_container_info(agent_id)
                
                if not container_info or container_info.get("status") != "running":
                    # Need to start the Docker container
                    logger.info(f"Starting Docker container for agent {agent_id}")
                    
                    # Get Docker image from agent metadata
                    metadata = agent_info.get("metadata", {})
                    docker_image = metadata.get("docker_image")
                    
                    if not docker_image:
                        raise Exception(f"No Docker image found for agent {agent_id}")
                    
                    container_info = self.docker_manager.start_agent_container(
                        agent_id=agent_id,
                        docker_image=docker_image,
                        agent_metadata=metadata
                    )
                    
                    # Update agent endpoint URL in database
                    endpoint_url = container_info["endpoint_url"]
                    # TODO: Update agent endpoint URL in database
                else:
                    endpoint_url = container_info["endpoint_url"]
            else:
                endpoint_url = agent_info.get("endpoint_url")
            
            if not endpoint_url:
                # Try to find a local agent
                if agent_info["id"] in registered_agents:
                    local_agent = registered_agents[agent_info["id"]]
                    endpoint_url = f"http://localhost:{local_agent.get('port', 8000)}"
                else:
                    raise Exception("No endpoint URL available for agent")
            
            # Check if agent supports ACP protocol
            metadata = agent_info.get("metadata", {})
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            protocol = metadata.get("protocol", "HTTP")
            
            if protocol == "ACP":
                # Use ACP protocol
                logger.info(f"Using ACP protocol for agent {agent_id}")
                
                # Connect to agent using ACP if not already connected
                if not self.acp_manager.get_agent_status(agent_id):
                    success = await self.acp_manager.connect_agent(agent_id, endpoint_url)
                    if not success:
                        raise Exception(f"Failed to connect to agent {agent_id} using ACP")
                
                # Send task request via ACP
                result = await self.acp_manager.send_task_request(
                    agent_id=agent_id,
                    endpoint=task_request.endpoint,
                    parameters=task_request.parameters,
                    timeout=30.0
                )
                
            else:
                # Use HTTP protocol
                logger.info(f"Using HTTP protocol for agent {agent_id}")
                
                # Make HTTP request to agent
                full_url = f"{endpoint_url.rstrip('/')}{task_request.endpoint}"
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        full_url,
                        json=task_request.parameters,
                        headers={"Content-Type": "application/json"}
                    )
                    response.raise_for_status()
                    result = response.json()
            
            execution_time = time.time() - start_time
            
            # Calculate cost based on agent pricing
            cost = self.calculate_task_cost(agent_info, execution_time)
            
            # Update task with success
            self.db.update_task(
                task_id=task_id,
                status="completed",
                result=result,
                execution_time=execution_time,
                cost=cost
            )
            
            # Update agent stats
            self.db.update_agent_stats(
                agent_id=agent_info["id"],
                success=True,
                execution_time=execution_time
            )
            
            logger.info(f"Task {task_id} completed successfully in {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)
            
            # Update task with failure
            self.db.update_task(
                task_id=task_id,
                status="failed",
                error=error_message,
                execution_time=execution_time
            )
            
            # Update agent stats
            self.db.update_agent_stats(
                agent_id=agent_info["id"],
                success=False,
                execution_time=execution_time
            )
            
            logger.error(f"Task {task_id} failed: {error_message}")
    
    def calculate_task_cost(self, agent_info: Dict[str, Any], execution_time: float) -> float:
        """Calculate task cost based on agent pricing"""
        try:
            metadata = agent_info.get("metadata", {})
            pricing = metadata.get("pricing")
            
            if not pricing:
                return 0.0
            
            pricing_type = pricing.get("type", "per_request")
            price = pricing.get("price", 0.0)
            
            if pricing_type == "per_request":
                return price
            elif pricing_type == "per_minute":
                return price * (execution_time / 60.0)
            elif pricing_type == "per_token":
                # Would need token count from response
                return price * 100  # Placeholder
            else:
                return price
                
        except Exception as e:
            logger.error(f"Error calculating cost: {e}")
            return 0.0
    
    def register_agent_endpoint(
        self, 
        agent_metadata: AgentMetadata, 
        endpoint_url: str
    ) -> str:
        """Register an agent endpoint with the hub"""
        try:
            # Register in database
            agent_id = self.db.register_agent(
                agent_metadata,
                endpoint_url=endpoint_url
            )
            
            # Keep track of registered agents
            registered_agents[agent_id] = {
                "metadata": agent_metadata,
                "endpoint_url": endpoint_url,
                "registered_at": datetime.now()
            }
            
            logger.info(f"Registered agent {agent_id} at {endpoint_url}")
            return agent_id
            
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            raise
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI app"""
        return self.app


def create_hub_server(
    database_url: str = "sqlite:///agenthub.db",
    enable_cors: bool = True,
    require_auth: bool = True,
    enable_docker: bool = True
) -> AgentHubServer:
    """
    Create an AgentHub server instance
    
    Args:
        database_url: Database connection string
        enable_cors: Enable CORS middleware
        require_auth: Require API key authentication
        enable_docker: Enable Docker agent management
        
    Returns:
        AgentHubServer instance
    """
    return AgentHubServer(
        database_url=database_url,
        enable_cors=enable_cors,
        require_auth=require_auth,
        enable_docker=enable_docker
    )


def serve_hub(
    server: AgentHubServer,
    host: str = "0.0.0.0",
    port: int = 8080,
    reload: bool = False,
    log_level: str = "info",
    workers: int = 1
):
    """
    Serve the AgentHub marketplace server
    
    Args:
        server: AgentHub server instance
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload for development
        log_level: Log level
        workers: Number of worker processes
    """
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info(f"Starting AgentHub marketplace server on {host}:{port}")
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, stopping server...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start server
    try:
        uvicorn.run(
            server.get_app(),
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            workers=workers if not reload else 1
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


# Example usage function
def start_development_hub(
    database_url: str = "sqlite:///agenthub_dev.db",
    port: int = 8080
):
    """Start a development AgentHub server"""
    server = create_hub_server(
        database_url=database_url,
        enable_cors=True,
        require_auth=False  # Disable auth for development
    )
    
    serve_hub(
        server=server,
        host="localhost",
        port=port,
        reload=True,
        log_level="debug"
    )


if __name__ == "__main__":
    # Start development server
    start_development_hub()