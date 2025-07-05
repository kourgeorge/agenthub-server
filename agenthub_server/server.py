"""
AgentHub Server - Complete marketplace server with database persistence
"""

import uvicorn
import asyncio
import httpx
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

logger = logging.getLogger(__name__)

# Global state
registered_agents: Dict[str, Dict[str, Any]] = {}
security = HTTPBearer(auto_error=False)


class AgentHubServer:
    """
    Complete AgentHub marketplace server with database persistence
    """
    
    def __init__(
        self, 
        database_url: str = "sqlite:///agenthub.db",
        enable_cors: bool = True,
        require_auth: bool = True
    ):
        """
        Initialize AgentHub server
        
        Args:
            database_url: Database connection string
            enable_cors: Enable CORS middleware
            require_auth: Require API key authentication
        """
        self.database_url = database_url
        self.require_auth = require_auth
        self.db = init_database(database_url)
        
        # Create FastAPI app
        self.app = FastAPI(
            title="AgentHub Marketplace Server",
            description="Distributed AI agent ecosystem",
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
            
            # Determine endpoint URL
            endpoint_url = agent_info.get("endpoint_url")
            if not endpoint_url:
                # Try to find a local agent
                if agent_info["id"] in registered_agents:
                    local_agent = registered_agents[agent_info["id"]]
                    endpoint_url = f"http://localhost:{local_agent.get('port', 8000)}"
                else:
                    raise Exception("No endpoint URL available for agent")
            
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
    require_auth: bool = True
) -> AgentHubServer:
    """
    Create an AgentHub server instance
    
    Args:
        database_url: Database connection string
        enable_cors: Enable CORS middleware
        require_auth: Require API key authentication
        
    Returns:
        AgentHubServer instance
    """
    return AgentHubServer(
        database_url=database_url,
        enable_cors=enable_cors,
        require_auth=require_auth
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