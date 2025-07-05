"""
Agent Lifecycle Manager for AgentHub Marketplace
Handles the complete lifecycle of agents from registration to deregistration
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class AgentLifecycleStage(str, Enum):
    """Agent lifecycle stages"""
    REGISTERED = "registered"
    DISCOVERED = "discovered"
    INSTANTIATING = "instantiating"
    ACTIVE = "active"
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    DEREGISTERED = "deregistered"
    ERROR = "error"


class AgentInstanceStatus(str, Enum):
    """Agent instance status"""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AgentInstance:
    """Represents a customer-specific agent instance"""
    
    def __init__(
        self,
        instance_id: str,
        agent_id: str,
        customer_id: str,
        instance_config: Dict[str, Any]
    ):
        self.instance_id = instance_id
        self.agent_id = agent_id
        self.customer_id = customer_id
        self.instance_config = instance_config
        self.status = AgentInstanceStatus.STOPPED
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self.paused_at: Optional[datetime] = None
        self.resource_usage = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "network_usage": 0.0,
            "task_count": 0,
            "uptime": 0.0
        }
        self.health_status = {
            "healthy": True,
            "last_heartbeat": None,
            "error_count": 0,
            "last_error": None
        }
        self.billing_info = {
            "total_cost": 0.0,
            "usage_time": 0.0,
            "task_executions": 0
        }


class AgentLifecycleManager:
    """
    Manages the complete lifecycle of agents in the marketplace
    """
    
    def __init__(self, docker_manager, acp_manager, database_manager):
        """
        Initialize Agent Lifecycle Manager
        
        Args:
            docker_manager: Docker agent manager
            acp_manager: ACP protocol manager
            database_manager: Database manager
        """
        self.docker_manager = docker_manager
        self.acp_manager = acp_manager
        self.db = database_manager
        
        # Track agent instances by customer
        self.agent_instances: Dict[str, AgentInstance] = {}
        self.customer_instances: Dict[str, List[str]] = {}
        self.instance_lock = threading.Lock()
        
        # Monitoring and maintenance
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.maintenance_interval = 60  # seconds
        
        # Start background tasks
        self.maintenance_task = None
        self.start_background_tasks()
    
    def start_background_tasks(self):
        """Start background maintenance tasks"""
        if self.maintenance_task is None:
            self.maintenance_task = asyncio.create_task(self._maintenance_loop())
    
    async def _maintenance_loop(self):
        """Background maintenance loop"""
        while True:
            try:
                await self._perform_maintenance()
                await asyncio.sleep(self.maintenance_interval)
            except Exception as e:
                logger.error(f"Maintenance loop error: {e}")
                await asyncio.sleep(self.maintenance_interval)
    
    async def _perform_maintenance(self):
        """Perform maintenance tasks"""
        try:
            # Update resource usage for all instances
            await self._update_resource_usage()
            
            # Check health of all instances
            await self._health_check_all_instances()
            
            # Clean up terminated instances
            await self._cleanup_terminated_instances()
            
            # Update billing information
            await self._update_billing_info()
            
        except Exception as e:
            logger.error(f"Maintenance error: {e}")
    
    # Stage 1: Registration (Enhanced)
    async def register_agent(
        self,
        agent_metadata: Dict[str, Any],
        docker_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a new agent in the marketplace
        
        Args:
            agent_metadata: Agent metadata
            docker_config: Docker configuration if applicable
            
        Returns:
            Agent ID
        """
        try:
            # Register in database
            agent_id = self.db.register_agent(agent_metadata)
            
            # If Docker agent, register with Docker manager
            if docker_config:
                self.docker_manager.register_agent_docker(
                    agent_id=agent_id,
                    docker_image=docker_config["docker_image"],
                    agent_metadata=agent_metadata,
                    registry_credentials=docker_config.get("registry_credentials")
                )
            
            # Update agent lifecycle stage
            await self._update_agent_stage(agent_id, AgentLifecycleStage.REGISTERED)
            
            logger.info(f"Agent {agent_id} registered successfully")
            return agent_id
            
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            raise
    
    # Stage 2: Discovery and Selection (Enhanced)
    async def discover_agents(
        self,
        customer_id: str,
        search_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Discover available agents based on customer criteria
        
        Args:
            customer_id: Customer identifier
            search_criteria: Search filters and criteria
            
        Returns:
            List of matching agents with marketplace information
        """
        try:
            # Search agents in database
            agents = self.db.search_agents(
                category=search_criteria.get("category"),
                name_pattern=search_criteria.get("name"),
                limit=search_criteria.get("limit", 20),
                offset=search_criteria.get("offset", 0)
            )
            
            # Enhance with marketplace information
            enhanced_agents = []
            for agent in agents:
                enhanced_agent = agent.copy()
                
                # Add marketplace-specific info
                enhanced_agent["marketplace_info"] = {
                    "availability": await self._check_agent_availability(agent["id"]),
                    "pricing_info": await self._get_pricing_info(agent["id"]),
                    "customer_instances": len(self._get_customer_instances(customer_id, agent["id"])),
                    "total_instances": await self._get_total_instances(agent["id"]),
                    "performance_metrics": await self._get_performance_metrics(agent["id"])
                }
                
                enhanced_agents.append(enhanced_agent)
            
            return enhanced_agents
            
        except Exception as e:
            logger.error(f"Failed to discover agents: {e}")
            raise
    
    # Stage 3: Instantiation (Enhanced)
    async def instantiate_agent(
        self,
        agent_id: str,
        customer_id: str,
        instance_config: Dict[str, Any]
    ) -> str:
        """
        Create a new agent instance for a customer
        
        Args:
            agent_id: Agent identifier
            customer_id: Customer identifier
            instance_config: Instance-specific configuration
            
        Returns:
            Instance ID
        """
        try:
            instance_id = str(uuid.uuid4())
            
            # Create agent instance
            instance = AgentInstance(
                instance_id=instance_id,
                agent_id=agent_id,
                customer_id=customer_id,
                instance_config=instance_config
            )
            
            with self.instance_lock:
                self.agent_instances[instance_id] = instance
                
                if customer_id not in self.customer_instances:
                    self.customer_instances[customer_id] = []
                self.customer_instances[customer_id].append(instance_id)
            
            # Update instance status
            instance.status = AgentInstanceStatus.STARTING
            
            # Get agent metadata
            agent = self.db.get_agent(agent_id)
            if not agent:
                raise Exception(f"Agent {agent_id} not found")
            
            # Update agent lifecycle stage
            await self._update_agent_stage(agent_id, AgentLifecycleStage.INSTANTIATING)
            
            # Start the agent container/process
            await self._start_agent_instance(instance, agent)
            
            logger.info(f"Agent instance {instance_id} instantiated for customer {customer_id}")
            return instance_id
            
        except Exception as e:
            logger.error(f"Failed to instantiate agent: {e}")
            # Cleanup on failure
            if instance_id in self.agent_instances:
                await self._cleanup_instance(instance_id)
            raise
    
    async def _start_agent_instance(self, instance: AgentInstance, agent: Dict[str, Any]):
        """Start an agent instance"""
        try:
            metadata = agent.get("metadata", {})
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            # Check if Docker agent
            docker_image = metadata.get("docker_image")
            if docker_image:
                # Start Docker container
                container_info = self.docker_manager.start_agent_container(
                    agent_id=instance.agent_id,
                    docker_image=docker_image,
                    agent_metadata=metadata
                )
                
                instance.instance_config["container_info"] = container_info
                instance.instance_config["endpoint_url"] = container_info["endpoint_url"]
            
            # Connect via ACP if supported
            protocol = metadata.get("protocol", "HTTP")
            if protocol == "ACP":
                endpoint_url = instance.instance_config.get("endpoint_url")
                if endpoint_url:
                    success = await self.acp_manager.connect_agent(instance.agent_id, endpoint_url)
                    if not success:
                        logger.warning(f"Failed to establish ACP connection for instance {instance.instance_id}")
            
            # Update instance status
            instance.status = AgentInstanceStatus.RUNNING
            instance.started_at = datetime.now()
            
            # Start monitoring for this instance
            await self._start_instance_monitoring(instance.instance_id)
            
        except Exception as e:
            instance.status = AgentInstanceStatus.ERROR
            instance.health_status["last_error"] = str(e)
            raise
    
    # Stage 4 & 5: Active/Running and Monitoring
    async def _start_instance_monitoring(self, instance_id: str):
        """Start monitoring for an agent instance"""
        if instance_id not in self.monitoring_tasks:
            self.monitoring_tasks[instance_id] = asyncio.create_task(
                self._monitor_instance(instance_id)
            )
    
    async def _monitor_instance(self, instance_id: str):
        """Monitor an agent instance"""
        while instance_id in self.agent_instances:
            try:
                instance = self.agent_instances[instance_id]
                
                if instance.status != AgentInstanceStatus.RUNNING:
                    break
                
                # Update resource usage
                await self._update_instance_resource_usage(instance)
                
                # Check health
                await self._check_instance_health(instance)
                
                # Update billing
                await self._update_instance_billing(instance)
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"Monitoring error for instance {instance_id}: {e}")
                await asyncio.sleep(30)
    
    async def _update_instance_resource_usage(self, instance: AgentInstance):
        """Update resource usage for an instance"""
        try:
            # Get container stats if Docker agent
            if "container_info" in instance.instance_config:
                stats = self.docker_manager.get_container_stats(instance.agent_id)
                if "error" not in stats:
                    # Parse Docker stats
                    cpu_stats = stats.get("cpu_usage", {})
                    memory_stats = stats.get("memory_usage", {})
                    
                    # Update resource usage
                    instance.resource_usage.update({
                        "cpu_usage": self._parse_cpu_usage(cpu_stats),
                        "memory_usage": self._parse_memory_usage(memory_stats),
                        "last_updated": datetime.now().isoformat()
                    })
            
            # Update uptime
            if instance.started_at:
                instance.resource_usage["uptime"] = (
                    datetime.now() - instance.started_at
                ).total_seconds()
                
        except Exception as e:
            logger.error(f"Failed to update resource usage for {instance.instance_id}: {e}")
    
    def _parse_cpu_usage(self, cpu_stats: Dict[str, Any]) -> float:
        """Parse CPU usage from Docker stats"""
        try:
            # Simplified CPU usage calculation
            cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            system_delta = cpu_stats.get("system_cpu_usage", 0)
            
            if system_delta > 0:
                return (cpu_delta / system_delta) * 100.0
            return 0.0
        except:
            return 0.0
    
    def _parse_memory_usage(self, memory_stats: Dict[str, Any]) -> float:
        """Parse memory usage from Docker stats"""
        try:
            usage = memory_stats.get("usage", 0)
            limit = memory_stats.get("limit", 1)
            return (usage / limit) * 100.0 if limit > 0 else 0.0
        except:
            return 0.0
    
    async def _check_instance_health(self, instance: AgentInstance):
        """Check health of an agent instance"""
        try:
            # Check ACP connection health
            if instance.agent_id in self.acp_manager.clients:
                client = self.acp_manager.clients[instance.agent_id]
                is_healthy = client.is_healthy()
                
                instance.health_status.update({
                    "healthy": is_healthy,
                    "last_heartbeat": client.last_heartbeat.isoformat() if client.last_heartbeat else None
                })
                
                if not is_healthy:
                    instance.health_status["error_count"] += 1
                    logger.warning(f"Instance {instance.instance_id} health check failed")
            
        except Exception as e:
            instance.health_status.update({
                "healthy": False,
                "last_error": str(e),
                "error_count": instance.health_status.get("error_count", 0) + 1
            })
    
    # Stage 6: Pause/Resume
    async def pause_agent_instance(self, instance_id: str, customer_id: str) -> bool:
        """
        Pause an agent instance
        
        Args:
            instance_id: Instance identifier
            customer_id: Customer identifier for authorization
            
        Returns:
            True if paused successfully
        """
        try:
            with self.instance_lock:
                instance = self.agent_instances.get(instance_id)
                if not instance:
                    raise Exception(f"Instance {instance_id} not found")
                
                if instance.customer_id != customer_id:
                    raise Exception("Unauthorized access to instance")
                
                if instance.status != AgentInstanceStatus.RUNNING:
                    raise Exception(f"Instance is not running (current status: {instance.status})")
            
            # Pause container if Docker agent
            if "container_info" in instance.instance_config:
                container = self.docker_manager.docker_client.containers.get(
                    instance.instance_config["container_info"]["container_id"]
                )
                container.pause()
            
            # Disconnect ACP if connected
            if instance.agent_id in self.acp_manager.clients:
                await self.acp_manager.disconnect_agent(instance.agent_id)
            
            # Update instance status
            instance.status = AgentInstanceStatus.PAUSED
            instance.paused_at = datetime.now()
            
            # Stop monitoring
            if instance_id in self.monitoring_tasks:
                self.monitoring_tasks[instance_id].cancel()
                del self.monitoring_tasks[instance_id]
            
            logger.info(f"Instance {instance_id} paused successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause instance {instance_id}: {e}")
            return False
    
    async def resume_agent_instance(self, instance_id: str, customer_id: str) -> bool:
        """
        Resume a paused agent instance
        
        Args:
            instance_id: Instance identifier
            customer_id: Customer identifier for authorization
            
        Returns:
            True if resumed successfully
        """
        try:
            with self.instance_lock:
                instance = self.agent_instances.get(instance_id)
                if not instance:
                    raise Exception(f"Instance {instance_id} not found")
                
                if instance.customer_id != customer_id:
                    raise Exception("Unauthorized access to instance")
                
                if instance.status != AgentInstanceStatus.PAUSED:
                    raise Exception(f"Instance is not paused (current status: {instance.status})")
            
            # Resume container if Docker agent
            if "container_info" in instance.instance_config:
                container = self.docker_manager.docker_client.containers.get(
                    instance.instance_config["container_info"]["container_id"]
                )
                container.unpause()
            
            # Reconnect ACP if supported
            agent = self.db.get_agent(instance.agent_id)
            metadata = agent.get("metadata", {})
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            protocol = metadata.get("protocol", "HTTP")
            if protocol == "ACP":
                endpoint_url = instance.instance_config.get("endpoint_url")
                if endpoint_url:
                    await self.acp_manager.connect_agent(instance.agent_id, endpoint_url)
            
            # Update instance status
            instance.status = AgentInstanceStatus.RUNNING
            instance.paused_at = None
            
            # Restart monitoring
            await self._start_instance_monitoring(instance_id)
            
            logger.info(f"Instance {instance_id} resumed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume instance {instance_id}: {e}")
            return False
    
    # Stage 7: Termination
    async def terminate_agent_instance(self, instance_id: str, customer_id: str) -> bool:
        """
        Terminate an agent instance
        
        Args:
            instance_id: Instance identifier
            customer_id: Customer identifier for authorization
            
        Returns:
            True if terminated successfully
        """
        try:
            with self.instance_lock:
                instance = self.agent_instances.get(instance_id)
                if not instance:
                    raise Exception(f"Instance {instance_id} not found")
                
                if instance.customer_id != customer_id:
                    raise Exception("Unauthorized access to instance")
            
            # Update status
            instance.status = AgentInstanceStatus.STOPPING
            
            # Stop monitoring
            if instance_id in self.monitoring_tasks:
                self.monitoring_tasks[instance_id].cancel()
                del self.monitoring_tasks[instance_id]
            
            # Disconnect ACP
            if instance.agent_id in self.acp_manager.clients:
                await self.acp_manager.disconnect_agent(instance.agent_id)
            
            # Stop container if Docker agent
            if "container_info" in instance.instance_config:
                success = self.docker_manager.stop_agent_container(instance.agent_id)
                if not success:
                    logger.warning(f"Failed to stop container for instance {instance_id}")
            
            # Update final status
            instance.status = AgentInstanceStatus.STOPPED
            instance.stopped_at = datetime.now()
            
            # Calculate final billing
            await self._finalize_instance_billing(instance)
            
            logger.info(f"Instance {instance_id} terminated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to terminate instance {instance_id}: {e}")
            instance.status = AgentInstanceStatus.ERROR
            return False
    
    # Stage 8: Deregistration
    async def deregister_agent(self, agent_id: str) -> bool:
        """
        Deregister an agent from the marketplace
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if deregistered successfully
        """
        try:
            # Check for active instances
            active_instances = [
                instance for instance in self.agent_instances.values()
                if instance.agent_id == agent_id and instance.status in [
                    AgentInstanceStatus.RUNNING, AgentInstanceStatus.PAUSED
                ]
            ]
            
            if active_instances:
                raise Exception(f"Cannot deregister agent with active instances: {len(active_instances)}")
            
            # Update agent status in database
            # Note: Implementation would mark as deregistered rather than delete
            # to preserve historical data
            
            # Clean up any Docker images/configs
            self.docker_manager.cleanup_stopped_containers()
            
            # Update agent lifecycle stage
            await self._update_agent_stage(agent_id, AgentLifecycleStage.DEREGISTERED)
            
            logger.info(f"Agent {agent_id} deregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deregister agent {agent_id}: {e}")
            return False
    
    # Utility methods
    async def _update_agent_stage(self, agent_id: str, stage: AgentLifecycleStage):
        """Update agent lifecycle stage"""
        # Implementation would update database with current stage
        logger.info(f"Agent {agent_id} stage updated to {stage}")
    
    def _get_customer_instances(self, customer_id: str, agent_id: Optional[str] = None) -> List[str]:
        """Get customer instances, optionally filtered by agent"""
        instances = self.customer_instances.get(customer_id, [])
        if agent_id:
            instances = [
                iid for iid in instances
                if self.agent_instances[iid].agent_id == agent_id
            ]
        return instances
    
    async def _check_agent_availability(self, agent_id: str) -> Dict[str, Any]:
        """Check agent availability"""
        return {
            "available": True,
            "max_instances": 10,  # Could be configurable
            "current_instances": await self._get_total_instances(agent_id)
        }
    
    async def _get_pricing_info(self, agent_id: str) -> Dict[str, Any]:
        """Get pricing information for agent"""
        agent = self.db.get_agent(agent_id)
        metadata = agent.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        
        pricing = metadata.get("pricing", {})
        return {
            "type": pricing.get("type", "per_request"),
            "price": pricing.get("price", 0.0),
            "currency": pricing.get("currency", "USD"),
            "billing_model": "pay_per_use"
        }
    
    async def _get_total_instances(self, agent_id: str) -> int:
        """Get total number of instances for an agent"""
        return len([
            instance for instance in self.agent_instances.values()
            if instance.agent_id == agent_id
        ])
    
    async def _get_performance_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get performance metrics for an agent"""
        # Implementation would aggregate metrics from all instances
        return {
            "average_response_time": 0.5,
            "success_rate": 0.99,
            "availability": 0.999,
            "total_tasks": 1000
        }
    
    async def _update_resource_usage(self):
        """Update resource usage for all instances"""
        for instance in self.agent_instances.values():
            if instance.status == AgentInstanceStatus.RUNNING:
                await self._update_instance_resource_usage(instance)
    
    async def _health_check_all_instances(self):
        """Health check for all instances"""
        for instance in self.agent_instances.values():
            if instance.status == AgentInstanceStatus.RUNNING:
                await self._check_instance_health(instance)
    
    async def _cleanup_terminated_instances(self):
        """Clean up terminated instances older than 24 hours"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        to_remove = []
        for instance_id, instance in self.agent_instances.items():
            if (instance.status == AgentInstanceStatus.STOPPED and 
                instance.stopped_at and instance.stopped_at < cutoff_time):
                to_remove.append(instance_id)
        
        for instance_id in to_remove:
            await self._cleanup_instance(instance_id)
    
    async def _cleanup_instance(self, instance_id: str):
        """Clean up an instance completely"""
        with self.instance_lock:
            instance = self.agent_instances.get(instance_id)
            if instance:
                # Remove from customer instances
                customer_id = instance.customer_id
                if customer_id in self.customer_instances:
                    if instance_id in self.customer_instances[customer_id]:
                        self.customer_instances[customer_id].remove(instance_id)
                
                # Remove from instances
                del self.agent_instances[instance_id]
        
        # Cancel monitoring task
        if instance_id in self.monitoring_tasks:
            self.monitoring_tasks[instance_id].cancel()
            del self.monitoring_tasks[instance_id]
    
    async def _update_billing_info(self):
        """Update billing information for all instances"""
        for instance in self.agent_instances.values():
            await self._update_instance_billing(instance)
    
    async def _update_instance_billing(self, instance: AgentInstance):
        """Update billing for a specific instance"""
        try:
            if instance.status == AgentInstanceStatus.RUNNING and instance.started_at:
                # Calculate usage time
                current_time = datetime.now()
                usage_time = (current_time - instance.started_at).total_seconds()
                instance.billing_info["usage_time"] = usage_time
                
                # Get pricing info
                agent = self.db.get_agent(instance.agent_id)
                pricing_info = await self._get_pricing_info(instance.agent_id)
                
                # Calculate cost based on pricing model
                pricing_type = pricing_info.get("type", "per_request")
                price = pricing_info.get("price", 0.0)
                
                if pricing_type == "per_minute":
                    cost = (usage_time / 60.0) * price
                elif pricing_type == "per_hour":
                    cost = (usage_time / 3600.0) * price
                else:
                    cost = instance.billing_info["task_executions"] * price
                
                instance.billing_info["total_cost"] = cost
                
        except Exception as e:
            logger.error(f"Failed to update billing for {instance.instance_id}: {e}")
    
    async def _finalize_instance_billing(self, instance: AgentInstance):
        """Finalize billing when instance is terminated"""
        await self._update_instance_billing(instance)
        
        # Store final billing in database
        # Implementation would save billing record to database
        logger.info(f"Final billing for {instance.instance_id}: ${instance.billing_info['total_cost']:.2f}")
    
    # Public API methods
    def get_customer_instances(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all instances for a customer"""
        instance_ids = self.customer_instances.get(customer_id, [])
        instances = []
        
        for instance_id in instance_ids:
            instance = self.agent_instances.get(instance_id)
            if instance:
                instances.append({
                    "instance_id": instance.instance_id,
                    "agent_id": instance.agent_id,
                    "status": instance.status,
                    "created_at": instance.created_at.isoformat(),
                    "started_at": instance.started_at.isoformat() if instance.started_at else None,
                    "resource_usage": instance.resource_usage,
                    "health_status": instance.health_status,
                    "billing_info": instance.billing_info
                })
        
        return instances
    
    def get_instance_details(self, instance_id: str, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an instance"""
        instance = self.agent_instances.get(instance_id)
        if not instance or instance.customer_id != customer_id:
            return None
        
        return {
            "instance_id": instance.instance_id,
            "agent_id": instance.agent_id,
            "customer_id": instance.customer_id,
            "status": instance.status,
            "created_at": instance.created_at.isoformat(),
            "started_at": instance.started_at.isoformat() if instance.started_at else None,
            "stopped_at": instance.stopped_at.isoformat() if instance.stopped_at else None,
            "paused_at": instance.paused_at.isoformat() if instance.paused_at else None,
            "instance_config": instance.instance_config,
            "resource_usage": instance.resource_usage,
            "health_status": instance.health_status,
            "billing_info": instance.billing_info
        }
    
    async def shutdown(self):
        """Shutdown the lifecycle manager"""
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        # Cancel maintenance task
        if self.maintenance_task:
            self.maintenance_task.cancel()
        
        # Terminate all running instances gracefully
        for instance in self.agent_instances.values():
            if instance.status == AgentInstanceStatus.RUNNING:
                await self.terminate_agent_instance(instance.instance_id, instance.customer_id)
        
        logger.info("Agent Lifecycle Manager shutdown complete")