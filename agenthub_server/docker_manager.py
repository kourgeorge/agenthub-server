"""
Docker Agent Manager for AgentHub Server
Handles Docker container lifecycle management for agents
"""

import docker
import json
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import signal
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class DockerAgentManager:
    """
    Manages Docker containers for agents
    """
    
    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        """
        Initialize Docker Agent Manager
        
        Args:
            docker_client: Docker client instance (optional)
        """
        try:
            self.docker_client = docker_client or docker.from_env()
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise
        
        # Track running containers
        self.running_containers: Dict[str, Dict[str, Any]] = {}
        self.container_lock = threading.Lock()
        
        # Network for agent communication
        self.network_name = "agenthub_network"
        self._ensure_network()
    
    def _ensure_network(self):
        """Ensure the AgentHub network exists"""
        try:
            self.docker_client.networks.get(self.network_name)
            logger.info(f"Network {self.network_name} already exists")
        except docker.errors.NotFound:
            logger.info(f"Creating network {self.network_name}")
            self.docker_client.networks.create(
                self.network_name,
                driver="bridge",
                labels={"app": "agenthub"}
            )
    
    def register_agent_docker(
        self, 
        agent_id: str, 
        docker_image: str,
        agent_metadata: Dict[str, Any],
        registry_credentials: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Register an agent with Docker deployment
        
        Args:
            agent_id: Unique agent identifier
            docker_image: Docker image name/tag
            agent_metadata: Agent metadata
            registry_credentials: Docker registry credentials
            
        Returns:
            Agent registration info
        """
        try:
            # Pull Docker image if needed
            logger.info(f"Pulling Docker image: {docker_image}")
            if registry_credentials:
                self.docker_client.images.pull(
                    docker_image,
                    auth_config=registry_credentials
                )
            else:
                self.docker_client.images.pull(docker_image)
            
            # Validate image
            image = self.docker_client.images.get(docker_image)
            logger.info(f"Docker image {docker_image} ready")
            
            # Store agent configuration
            agent_config = {
                "agent_id": agent_id,
                "docker_image": docker_image,
                "metadata": agent_metadata,
                "registry_credentials": registry_credentials,
                "created_at": datetime.now().isoformat(),
                "status": "registered"
            }
            
            return agent_config
            
        except Exception as e:
            logger.error(f"Failed to register Docker agent {agent_id}: {e}")
            raise
    
    def start_agent_container(
        self, 
        agent_id: str, 
        docker_image: str,
        agent_metadata: Dict[str, Any],
        port_mapping: Optional[Dict[int, int]] = None
    ) -> Dict[str, Any]:
        """
        Start a Docker container for an agent
        
        Args:
            agent_id: Unique agent identifier
            docker_image: Docker image name/tag
            agent_metadata: Agent metadata
            port_mapping: Port mapping (container_port -> host_port)
            
        Returns:
            Container information
        """
        with self.container_lock:
            try:
                # Check if container already running
                if agent_id in self.running_containers:
                    container_info = self.running_containers[agent_id]
                    if container_info["status"] == "running":
                        logger.info(f"Agent {agent_id} container already running")
                        return container_info
                
                # Find available port
                if not port_mapping:
                    available_port = self._find_available_port()
                    port_mapping = {8000: available_port}  # Default agent port
                
                # Container configuration
                container_name = f"agenthub_agent_{agent_id}"
                
                # Environment variables
                environment = {
                    "AGENTHUB_AGENT_ID": agent_id,
                    "AGENTHUB_AGENT_PORT": "8000",
                    "AGENTHUB_PROTOCOL": "ACP",
                    "PYTHONUNBUFFERED": "1"
                }
                
                # Add agent metadata as env vars
                if agent_metadata:
                    environment["AGENTHUB_AGENT_METADATA"] = json.dumps(agent_metadata)
                
                # Start container
                logger.info(f"Starting container for agent {agent_id}")
                container = self.docker_client.containers.run(
                    docker_image,
                    name=container_name,
                    ports=port_mapping,
                    environment=environment,
                    network=self.network_name,
                    detach=True,
                    restart_policy={"Name": "unless-stopped"},
                    labels={
                        "app": "agenthub",
                        "agent_id": agent_id,
                        "created_by": "agenthub_server"
                    }
                )
                
                # Wait for container to be ready
                self._wait_for_container_ready(container, timeout=30)
                
                # Container info
                container_info = {
                    "agent_id": agent_id,
                    "container_id": container.id,
                    "container_name": container_name,
                    "docker_image": docker_image,
                    "port_mapping": port_mapping,
                    "endpoint_url": f"http://localhost:{list(port_mapping.values())[0]}",
                    "status": "running",
                    "started_at": datetime.now().isoformat(),
                    "metadata": agent_metadata
                }
                
                self.running_containers[agent_id] = container_info
                logger.info(f"Agent {agent_id} container started successfully")
                
                return container_info
                
            except Exception as e:
                logger.error(f"Failed to start container for agent {agent_id}: {e}")
                raise
    
    def stop_agent_container(self, agent_id: str) -> bool:
        """
        Stop a Docker container for an agent
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if stopped successfully
        """
        with self.container_lock:
            try:
                if agent_id not in self.running_containers:
                    logger.warning(f"No running container found for agent {agent_id}")
                    return False
                
                container_info = self.running_containers[agent_id]
                container_id = container_info["container_id"]
                
                logger.info(f"Stopping container for agent {agent_id}")
                container = self.docker_client.containers.get(container_id)
                container.stop(timeout=10)
                container.remove()
                
                # Update status
                container_info["status"] = "stopped"
                container_info["stopped_at"] = datetime.now().isoformat()
                
                logger.info(f"Agent {agent_id} container stopped successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to stop container for agent {agent_id}: {e}")
                return False
    
    def get_agent_container_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get container information for an agent
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Container information or None
        """
        with self.container_lock:
            return self.running_containers.get(agent_id)
    
    def list_running_containers(self) -> List[Dict[str, Any]]:
        """
        List all running agent containers
        
        Returns:
            List of container information
        """
        with self.container_lock:
            return list(self.running_containers.values())
    
    def cleanup_stopped_containers(self):
        """Clean up stopped containers"""
        try:
            # Get all containers with agenthub label
            containers = self.docker_client.containers.list(
                all=True,
                filters={"label": "app=agenthub"}
            )
            
            for container in containers:
                if container.status == "exited":
                    logger.info(f"Removing stopped container {container.name}")
                    container.remove()
            
            # Update running containers dict
            with self.container_lock:
                to_remove = []
                for agent_id, info in self.running_containers.items():
                    try:
                        container = self.docker_client.containers.get(info["container_id"])
                        if container.status != "running":
                            to_remove.append(agent_id)
                    except docker.errors.NotFound:
                        to_remove.append(agent_id)
                
                for agent_id in to_remove:
                    del self.running_containers[agent_id]
                    logger.info(f"Removed stopped container info for agent {agent_id}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup containers: {e}")
    
    def _find_available_port(self, start_port: int = 8001) -> int:
        """Find an available port"""
        import socket
        
        for port in range(start_port, start_port + 1000):
            if port not in [info["port_mapping"].get(8000) for info in self.running_containers.values()]:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    if sock.connect_ex(('localhost', port)) != 0:
                        return port
        
        raise Exception("No available ports found")
    
    def _wait_for_container_ready(self, container, timeout: int = 30):
        """Wait for container to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                container.reload()
                if container.status == "running":
                    # Additional check - try to connect to the agent
                    time.sleep(2)  # Give the agent time to start
                    return
                elif container.status == "exited":
                    logs = container.logs().decode('utf-8')
                    raise Exception(f"Container exited unexpectedly. Logs: {logs}")
                    
            except Exception as e:
                if time.time() - start_time >= timeout:
                    raise Exception(f"Container failed to start within {timeout}s: {e}")
                
            time.sleep(1)
        
        raise Exception(f"Container failed to start within {timeout}s")
    
    def get_container_logs(self, agent_id: str, tail: int = 100) -> str:
        """
        Get logs from agent container
        
        Args:
            agent_id: Agent identifier
            tail: Number of lines to return
            
        Returns:
            Container logs
        """
        try:
            if agent_id not in self.running_containers:
                return "No running container found"
            
            container_info = self.running_containers[agent_id]
            container = self.docker_client.containers.get(container_info["container_id"])
            
            logs = container.logs(tail=tail).decode('utf-8')
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get logs for agent {agent_id}: {e}")
            return f"Error getting logs: {e}"
    
    def get_container_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get container resource usage statistics
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Container statistics
        """
        try:
            if agent_id not in self.running_containers:
                return {"error": "No running container found"}
            
            container_info = self.running_containers[agent_id]
            container = self.docker_client.containers.get(container_info["container_id"])
            
            stats = container.stats(stream=False)
            
            # Extract useful metrics
            cpu_usage = stats.get('cpu_stats', {})
            memory_usage = stats.get('memory_stats', {})
            
            return {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for agent {agent_id}: {e}")
            return {"error": str(e)}
    
    def shutdown(self):
        """Shutdown all managed containers"""
        logger.info("Shutting down Docker Agent Manager")
        
        with self.container_lock:
            for agent_id in list(self.running_containers.keys()):
                try:
                    self.stop_agent_container(agent_id)
                except Exception as e:
                    logger.error(f"Error stopping container for agent {agent_id}: {e}")
        
        logger.info("Docker Agent Manager shutdown complete")