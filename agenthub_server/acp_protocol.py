"""
Agent Communication Protocol (ACP) Implementation
Handles standardized communication between server and agents
"""

import json
import asyncio
import httpx
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum
import websockets
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ACPMessageType(str, Enum):
    """ACP message types"""
    HANDSHAKE = "handshake"
    HEARTBEAT = "heartbeat"
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class ACPStatus(str, Enum):
    """ACP connection status"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class ACPMessage:
    """ACP message structure"""
    type: ACPMessageType
    agent_id: str
    message_id: str
    payload: Dict[str, Any]
    timestamp: str
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps({
            "type": self.type,
            "agent_id": self.agent_id,
            "message_id": self.message_id,
            "payload": self.payload,
            "timestamp": self.timestamp
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ACPMessage':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls(
            type=ACPMessageType(data["type"]),
            agent_id=data["agent_id"],
            message_id=data["message_id"],
            payload=data["payload"],
            timestamp=data["timestamp"]
        )


class ACPClient:
    """
    ACP client for communicating with agents
    """
    
    def __init__(self, agent_id: str, endpoint_url: str):
        """
        Initialize ACP client
        
        Args:
            agent_id: Agent identifier
            endpoint_url: Agent endpoint URL
        """
        self.agent_id = agent_id
        self.endpoint_url = endpoint_url
        self.status = ACPStatus.DISCONNECTED
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.message_handlers: Dict[ACPMessageType, Callable] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.last_heartbeat: Optional[datetime] = None
        
        # Set up default message handlers
        self.message_handlers[ACPMessageType.HEARTBEAT] = self._handle_heartbeat
        self.message_handlers[ACPMessageType.STATUS_UPDATE] = self._handle_status_update
        self.message_handlers[ACPMessageType.ERROR] = self._handle_error
    
    async def connect(self, timeout: float = 30.0) -> bool:
        """
        Connect to agent using ACP protocol
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected successfully
        """
        try:
            self.status = ACPStatus.CONNECTING
            
            # Try WebSocket connection first
            if await self._try_websocket_connection(timeout):
                return True
            
            # Fall back to HTTP polling
            if await self._try_http_connection(timeout):
                return True
            
            logger.error(f"Failed to connect to agent {self.agent_id}")
            self.status = ACPStatus.ERROR
            return False
            
        except Exception as e:
            logger.error(f"Connection error for agent {self.agent_id}: {e}")
            self.status = ACPStatus.ERROR
            return False
    
    async def _try_websocket_connection(self, timeout: float) -> bool:
        """Try to establish WebSocket connection"""
        try:
            ws_url = self.endpoint_url.replace('http://', 'ws://').replace('https://', 'wss://')
            ws_url = f"{ws_url.rstrip('/')}/acp"
            
            logger.info(f"Attempting WebSocket connection to {ws_url}")
            
            self.websocket = await asyncio.wait_for(
                websockets.connect(ws_url),
                timeout=timeout
            )
            
            # Send handshake
            handshake_msg = ACPMessage(
                type=ACPMessageType.HANDSHAKE,
                agent_id=self.agent_id,
                message_id=str(uuid.uuid4()),
                payload={"protocol_version": "1.0", "client_type": "agenthub_server"},
                timestamp=datetime.now().isoformat()
            )
            
            await self.websocket.send(handshake_msg.to_json())
            
            # Wait for handshake response
            response_str = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=10.0
            )
            
            response = ACPMessage.from_json(response_str)
            
            if response.type == ACPMessageType.HANDSHAKE and response.payload.get("status") == "ready":
                self.status = ACPStatus.CONNECTED
                logger.info(f"WebSocket connection established with agent {self.agent_id}")
                
                # Start message handler
                asyncio.create_task(self._handle_websocket_messages())
                
                # Start heartbeat
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"WebSocket connection failed for agent {self.agent_id}: {e}")
            return False
    
    async def _try_http_connection(self, timeout: float) -> bool:
        """Try to establish HTTP connection"""
        try:
            self.http_client = httpx.AsyncClient(timeout=timeout)
            
            # Send handshake
            handshake_payload = {
                "protocol_version": "1.0",
                "client_type": "agenthub_server"
            }
            
            response = await self.http_client.post(
                f"{self.endpoint_url}/acp/handshake",
                json=handshake_payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ready":
                    self.status = ACPStatus.CONNECTED
                    logger.info(f"HTTP connection established with agent {self.agent_id}")
                    
                    # Start heartbeat
                    self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"HTTP connection failed for agent {self.agent_id}: {e}")
            return False
    
    async def send_task_request(
        self, 
        endpoint: str, 
        parameters: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Send a task request to the agent
        
        Args:
            endpoint: Agent endpoint to call
            parameters: Task parameters
            timeout: Request timeout
            
        Returns:
            Task response
        """
        try:
            self.status = ACPStatus.BUSY
            
            message_id = str(uuid.uuid4())
            
            task_msg = ACPMessage(
                type=ACPMessageType.TASK_REQUEST,
                agent_id=self.agent_id,
                message_id=message_id,
                payload={
                    "endpoint": endpoint,
                    "parameters": parameters,
                    "timeout": timeout
                },
                timestamp=datetime.now().isoformat()
            )
            
            if self.websocket:
                # WebSocket request
                future = asyncio.Future()
                self.pending_requests[message_id] = future
                
                await self.websocket.send(task_msg.to_json())
                
                # Wait for response
                response = await asyncio.wait_for(future, timeout=timeout)
                
                self.status = ACPStatus.READY
                return response
                
            elif self.http_client:
                # HTTP request
                response = await self.http_client.post(
                    f"{self.endpoint_url}/acp/task",
                    json=task_msg.payload
                )
                
                response.raise_for_status()
                result = response.json()
                
                self.status = ACPStatus.READY
                return result
            
            else:
                raise Exception("No active connection")
                
        except Exception as e:
            logger.error(f"Task request failed for agent {self.agent_id}: {e}")
            self.status = ACPStatus.ERROR
            raise
    
    async def _handle_websocket_messages(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    acp_message = ACPMessage.from_json(message)
                    
                    # Handle response to pending request
                    if acp_message.type == ACPMessageType.TASK_RESPONSE:
                        message_id = acp_message.payload.get("request_id")
                        if message_id in self.pending_requests:
                            future = self.pending_requests.pop(message_id)
                            future.set_result(acp_message.payload)
                    
                    # Handle other message types
                    elif acp_message.type in self.message_handlers:
                        handler = self.message_handlers[acp_message.type]
                        await handler(acp_message)
                        
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed for agent {self.agent_id}")
            self.status = ACPStatus.DISCONNECTED
        except Exception as e:
            logger.error(f"WebSocket error for agent {self.agent_id}: {e}")
            self.status = ACPStatus.ERROR
    
    async def _heartbeat_loop(self):
        """Heartbeat loop to keep connection alive"""
        while self.status in [ACPStatus.CONNECTED, ACPStatus.READY, ACPStatus.BUSY]:
            try:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
                heartbeat_msg = ACPMessage(
                    type=ACPMessageType.HEARTBEAT,
                    agent_id=self.agent_id,
                    message_id=str(uuid.uuid4()),
                    payload={"timestamp": datetime.now().isoformat()},
                    timestamp=datetime.now().isoformat()
                )
                
                if self.websocket:
                    await self.websocket.send(heartbeat_msg.to_json())
                elif self.http_client:
                    await self.http_client.post(
                        f"{self.endpoint_url}/acp/heartbeat",
                        json=heartbeat_msg.payload
                    )
                
                self.last_heartbeat = datetime.now()
                
            except Exception as e:
                logger.error(f"Heartbeat error for agent {self.agent_id}: {e}")
                self.status = ACPStatus.ERROR
                break
    
    async def _handle_heartbeat(self, message: ACPMessage):
        """Handle heartbeat message"""
        self.last_heartbeat = datetime.now()
        logger.debug(f"Received heartbeat from agent {self.agent_id}")
    
    async def _handle_status_update(self, message: ACPMessage):
        """Handle status update message"""
        new_status = message.payload.get("status")
        if new_status:
            logger.info(f"Agent {self.agent_id} status update: {new_status}")
    
    async def _handle_error(self, message: ACPMessage):
        """Handle error message"""
        error_msg = message.payload.get("error", "Unknown error")
        logger.error(f"Agent {self.agent_id} error: {error_msg}")
        self.status = ACPStatus.ERROR
    
    async def disconnect(self):
        """Disconnect from agent"""
        try:
            self.status = ACPStatus.DISCONNECTED
            
            # Cancel heartbeat task
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                
            # Send shutdown message
            if self.websocket:
                shutdown_msg = ACPMessage(
                    type=ACPMessageType.SHUTDOWN,
                    agent_id=self.agent_id,
                    message_id=str(uuid.uuid4()),
                    payload={"reason": "server_shutdown"},
                    timestamp=datetime.now().isoformat()
                )
                
                try:
                    await self.websocket.send(shutdown_msg.to_json())
                    await self.websocket.close()
                except:
                    pass
                
            # Close HTTP client
            if self.http_client:
                await self.http_client.aclose()
            
            logger.info(f"Disconnected from agent {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting from agent {self.agent_id}: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to agent"""
        return self.status in [ACPStatus.CONNECTED, ACPStatus.READY]
    
    def is_healthy(self) -> bool:
        """Check if agent connection is healthy"""
        if not self.is_connected():
            return False
        
        if self.last_heartbeat:
            time_since_heartbeat = datetime.now() - self.last_heartbeat
            return time_since_heartbeat.total_seconds() < 120  # 2 minutes
        
        return True


class ACPManager:
    """
    Manager for ACP connections to multiple agents
    """
    
    def __init__(self):
        """Initialize ACP manager"""
        self.clients: Dict[str, ACPClient] = {}
        self.connection_lock = threading.Lock()
    
    async def connect_agent(self, agent_id: str, endpoint_url: str) -> bool:
        """
        Connect to an agent
        
        Args:
            agent_id: Agent identifier
            endpoint_url: Agent endpoint URL
            
        Returns:
            True if connected successfully
        """
        with self.connection_lock:
            # Check if already connected
            if agent_id in self.clients:
                client = self.clients[agent_id]
                if client.is_connected():
                    return True
            
            # Create new client
            client = ACPClient(agent_id, endpoint_url)
            self.clients[agent_id] = client
        
        # Connect to agent
        success = await client.connect()
        
        if not success:
            with self.connection_lock:
                del self.clients[agent_id]
        
        return success
    
    async def send_task_request(
        self, 
        agent_id: str, 
        endpoint: str, 
        parameters: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Send task request to agent
        
        Args:
            agent_id: Agent identifier
            endpoint: Agent endpoint
            parameters: Task parameters
            timeout: Request timeout
            
        Returns:
            Task response
        """
        with self.connection_lock:
            if agent_id not in self.clients:
                raise Exception(f"No connection to agent {agent_id}")
            
            client = self.clients[agent_id]
        
        if not client.is_connected():
            raise Exception(f"Agent {agent_id} is not connected")
        
        return await client.send_task_request(endpoint, parameters, timeout)
    
    async def disconnect_agent(self, agent_id: str):
        """Disconnect from agent"""
        with self.connection_lock:
            if agent_id in self.clients:
                client = self.clients[agent_id]
                await client.disconnect()
                del self.clients[agent_id]
    
    async def disconnect_all(self):
        """Disconnect from all agents"""
        with self.connection_lock:
            agent_ids = list(self.clients.keys())
        
        for agent_id in agent_ids:
            await self.disconnect_agent(agent_id)
    
    def get_agent_status(self, agent_id: str) -> Optional[ACPStatus]:
        """Get agent connection status"""
        with self.connection_lock:
            if agent_id in self.clients:
                return self.clients[agent_id].status
        return None
    
    def list_connected_agents(self) -> List[str]:
        """List connected agents"""
        with self.connection_lock:
            return [
                agent_id for agent_id, client in self.clients.items()
                if client.is_connected()
            ]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all connections"""
        with self.connection_lock:
            status = {}
            for agent_id, client in self.clients.items():
                status[agent_id] = {
                    "status": client.status,
                    "healthy": client.is_healthy(),
                    "last_heartbeat": client.last_heartbeat.isoformat() if client.last_heartbeat else None
                }
            return status