"""
Pydantic models for AgentHub Server with fallback support
"""

from typing import Dict, Any, Optional, List, Union
from enum import Enum

# Try to import Pydantic, fall back to standard Python if not available
try:
    from pydantic import BaseModel, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    
    # Fallback BaseModel implementation
    class BaseModel:
        """Fallback BaseModel for when Pydantic is not available"""
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        def dict(self):
            """Convert to dictionary"""
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        
        def json(self):
            """Convert to JSON string"""
            import json
            return json.dumps(self.dict())
    
    # Fallback Field function
    def Field(default=None, **kwargs):
        """Fallback Field function"""
        return default
    
    # Fallback validator decorator
    def validator(field_name):
        """Fallback validator decorator"""
        def decorator(func):
            return func
        return decorator


class PricingType(str, Enum):
    """Pricing model types for agents"""
    FIXED = "fixed"
    PER_REQUEST = "per_request"
    PER_TOKEN = "per_token"
    PER_MINUTE = "per_minute"


class AgentProtocol(str, Enum):
    """Supported agent communication protocols"""
    ACP = "ACP"  # Agent Communication Protocol
    MCP = "MCP"  # Model Context Protocol
    HTTP = "HTTP"  # Standard HTTP REST API


class AgentRuntime(str, Enum):
    """Agent runtime environments"""
    EXTERNAL = "external"
    MANAGED = "managed"
    SERVERLESS = "serverless"


if PYDANTIC_AVAILABLE:
    # Proper Pydantic models when Pydantic is available
    
    class PricingModel(BaseModel):
        """Pricing configuration for an agent"""
        type: PricingType = Field(default=PricingType.PER_REQUEST)
        price: float = Field(default=0.0, ge=0.0)
        currency: str = Field(default="USD")
        
        @validator('type', pre=True)
        def convert_type_to_enum(cls, v):
            if isinstance(v, str):
                return PricingType(v)
            return v

    class AgentCapability(BaseModel):
        """Individual agent capability description"""
        name: str = Field(default="")
        description: str = Field(default="")
        parameters: Dict[str, Any] = Field(default_factory=dict)

    class AgentEndpoint(BaseModel):
        """Agent endpoint configuration"""
        path: str = Field(default="")
        method: str = Field(default="POST")
        description: str = Field(default="")
        parameters: Dict[str, Any] = Field(default_factory=dict)
        response_schema: Optional[Dict[str, Any]] = Field(default=None)

    class AgentMetadata(BaseModel):
        """Complete agent metadata"""
        name: str = Field(...)
        description: str = Field(default="")
        version: str = Field(default="1.0.0")
        category: str = Field(default="general")
        tags: List[str] = Field(default_factory=list)
        capabilities: List[AgentCapability] = Field(default_factory=list)
        endpoints: List[AgentEndpoint] = Field(default_factory=list)
        pricing: Optional[Union[PricingModel, Dict[str, Any]]] = Field(default=None)
        protocol: AgentProtocol = Field(default=AgentProtocol.ACP)
        runtime: AgentRuntime = Field(default=AgentRuntime.EXTERNAL)
        endpoint_url: Optional[str] = Field(default=None)
        requirements: List[str] = Field(default_factory=list)
        author: Optional[str] = Field(default=None)
        license: Optional[str] = Field(default=None)
        documentation_url: Optional[str] = Field(default=None)
        repository_url: Optional[str] = Field(default=None)
        
        @validator('pricing', pre=True)
        def convert_pricing(cls, v):
            if isinstance(v, dict):
                return PricingModel(**v)
            return v
        
        @validator('protocol', pre=True)
        def convert_protocol(cls, v):
            if isinstance(v, str):
                return AgentProtocol(v)
            return v
        
        @validator('runtime', pre=True)
        def convert_runtime(cls, v):
            if isinstance(v, str):
                return AgentRuntime(v)
            return v
        
        @validator('version')
        def validate_version(cls, v):
            if v:
                parts = v.split('.')
                if len(parts) != 3:
                    raise ValueError("Version must be in format X.Y.Z")
                for part in parts:
                    if not part.isdigit():
                        raise ValueError("Version parts must be numeric")
            return v

    class TaskRequest(BaseModel):
        """Task request from client to agent"""
        agent_id: str = Field(default="")
        endpoint: str = Field(default="")
        parameters: Dict[str, Any] = Field(default_factory=dict)
        callback_url: Optional[str] = Field(default=None)
        timeout: Optional[int] = Field(default=None, ge=1)
        priority: int = Field(default=0, ge=0, le=10)

    class TaskResponse(BaseModel):
        """Task response from agent to client"""
        task_id: str = Field(default="")
        status: str = Field(default="")
        result: Optional[Any] = Field(default=None)
        error: Optional[str] = Field(default=None)
        execution_time: Optional[float] = Field(default=None)
        cost: Optional[float] = Field(default=None)

    class AgentRegistration(BaseModel):
        """Agent registration request"""
        metadata: AgentMetadata
        api_key: str = Field(default="")
        
        @validator('metadata', pre=True)
        def convert_metadata(cls, v):
            if isinstance(v, dict):
                return AgentMetadata(**v)
            return v

    class AgentStatus(BaseModel):
        """Agent status information"""
        agent_id: str = Field(default="")
        status: str = Field(default="")
        last_seen: Optional[str] = Field(default=None)
        reliability_score: Optional[float] = Field(default=None, ge=0, le=100)
        total_tasks: int = Field(default=0)
        success_rate: Optional[float] = Field(default=None, ge=0, le=1)
        average_response_time: Optional[float] = Field(default=None)

else:
    # Fallback models when Pydantic is not available
    
    class PricingModel(BaseModel):
        """Pricing configuration for an agent"""
        
        def __init__(self, **kwargs):
            self.type = kwargs.get('type', PricingType.PER_REQUEST)
            self.price = kwargs.get('price', 0.0)
            self.currency = kwargs.get('currency', 'USD')
            
            # Convert string to enum if needed
            if isinstance(self.type, str):
                self.type = PricingType(self.type)
            
            # Validate price
            if self.price < 0:
                raise ValueError("Price must be non-negative")
            
            super().__init__(**kwargs)

    class AgentCapability(BaseModel):
        """Individual agent capability description"""
        
        def __init__(self, **kwargs):
            self.name = kwargs.get('name', '')
            self.description = kwargs.get('description', '')
            self.parameters = kwargs.get('parameters', {})
            super().__init__(**kwargs)

    class AgentEndpoint(BaseModel):
        """Agent endpoint configuration"""
        
        def __init__(self, **kwargs):
            self.path = kwargs.get('path', '')
            self.method = kwargs.get('method', 'POST')
            self.description = kwargs.get('description', '')
            self.parameters = kwargs.get('parameters', {})
            self.response_schema = kwargs.get('response_schema', None)
            super().__init__(**kwargs)

    class AgentMetadata(BaseModel):
        """Complete agent metadata"""
        
        def __init__(self, **kwargs):
            # Remove pricing from kwargs before calling super() to prevent overwrite
            pricing_data = kwargs.pop('pricing', None)
            
            self.name = kwargs.get('name', '')
            self.description = kwargs.get('description', '')
            self.version = kwargs.get('version', '1.0.0')
            self.category = kwargs.get('category', 'general')
            self.tags = kwargs.get('tags', [])
            self.capabilities = kwargs.get('capabilities', [])
            self.endpoints = kwargs.get('endpoints', [])
            self.protocol = kwargs.get('protocol', AgentProtocol.ACP)
            self.runtime = kwargs.get('runtime', AgentRuntime.EXTERNAL)
            self.endpoint_url = kwargs.get('endpoint_url', None)
            self.requirements = kwargs.get('requirements', [])
            self.author = kwargs.get('author', None)
            self.license = kwargs.get('license', None)
            self.documentation_url = kwargs.get('documentation_url', None)
            self.repository_url = kwargs.get('repository_url', None)
            
            # Convert pricing to PricingModel if it's a dict
            if pricing_data is not None and isinstance(pricing_data, dict):
                self.pricing = PricingModel(**pricing_data)
            else:
                self.pricing = pricing_data
            
            # Convert string enums
            if isinstance(self.protocol, str):
                self.protocol = AgentProtocol(self.protocol)
            if isinstance(self.runtime, str):
                self.runtime = AgentRuntime(self.runtime)
            
            # Convert capabilities list
            capabilities_list = []
            for cap in self.capabilities:
                if isinstance(cap, dict):
                    capabilities_list.append(AgentCapability(**cap))
                else:
                    capabilities_list.append(cap)
            self.capabilities = capabilities_list
            
            # Convert endpoints list
            endpoints_list = []
            for ep in self.endpoints:
                if isinstance(ep, dict):
                    endpoints_list.append(AgentEndpoint(**ep))
                else:
                    endpoints_list.append(ep)
            self.endpoints = endpoints_list
            
            # Validate required fields
            if not self.name or len(self.name.strip()) == 0:
                raise ValueError("Agent name cannot be empty")
            
            # Validate version format
            if self.version:
                parts = self.version.split('.')
                if len(parts) != 3:
                    raise ValueError("Version must be in format X.Y.Z")
                for part in parts:
                    if not part.isdigit():
                        raise ValueError("Version parts must be numeric")
            
            super().__init__(**kwargs)

    class TaskRequest(BaseModel):
        """Task request from client to agent"""
        
        def __init__(self, **kwargs):
            self.agent_id = kwargs.get('agent_id', '')
            self.endpoint = kwargs.get('endpoint', '')
            self.parameters = kwargs.get('parameters', {})
            self.callback_url = kwargs.get('callback_url', None)
            self.timeout = kwargs.get('timeout', None)
            self.priority = kwargs.get('priority', 0)
            
            # Validate timeout
            if self.timeout is not None and self.timeout < 1:
                raise ValueError("Timeout must be at least 1 second")
            
            # Validate priority
            if not (0 <= self.priority <= 10):
                raise ValueError("Priority must be between 0 and 10")
            
            super().__init__(**kwargs)

    class TaskResponse(BaseModel):
        """Task response from agent to client"""
        
        def __init__(self, **kwargs):
            self.task_id = kwargs.get('task_id', '')
            self.status = kwargs.get('status', '')
            self.result = kwargs.get('result', None)
            self.error = kwargs.get('error', None)
            self.execution_time = kwargs.get('execution_time', None)
            self.cost = kwargs.get('cost', None)
            super().__init__(**kwargs)

    class AgentRegistration(BaseModel):
        """Agent registration request"""
        
        def __init__(self, **kwargs):
            self.metadata = kwargs.get('metadata')
            self.api_key = kwargs.get('api_key', '')
            
            # Convert metadata to AgentMetadata if it's a dict
            if isinstance(self.metadata, dict):
                self.metadata = AgentMetadata(**self.metadata)
            
            super().__init__(**kwargs)

    class AgentStatus(BaseModel):
        """Agent status information"""
        
        def __init__(self, **kwargs):
            self.agent_id = kwargs.get('agent_id', '')
            self.status = kwargs.get('status', '')
            self.last_seen = kwargs.get('last_seen', None)
            self.reliability_score = kwargs.get('reliability_score', None)
            self.total_tasks = kwargs.get('total_tasks', 0)
            self.success_rate = kwargs.get('success_rate', None)
            self.average_response_time = kwargs.get('average_response_time', None)
            
            # Validate reliability score
            if self.reliability_score is not None and not (0 <= self.reliability_score <= 100):
                raise ValueError("Reliability score must be between 0 and 100")
            
            # Validate success rate
            if self.success_rate is not None and not (0 <= self.success_rate <= 1):
                raise ValueError("Success rate must be between 0 and 1")
            
            super().__init__(**kwargs)