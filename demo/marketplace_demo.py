#!/usr/bin/env python3
"""
AgentHub Marketplace Demo
Demonstrates all 8 stages of the agent lifecycle with Docker agents and customer management
"""

import asyncio
import json
import time
import subprocess
import sys
import os
import threading
import signal
from pathlib import Path
from typing import Dict, List, Any
import logging
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketplaceDemo:
    """Complete marketplace demonstration"""
    
    def __init__(self):
        self.demo_dir = Path(__file__).parent
        self.server_process = None
        self.agent_containers = []
        self.server_url = "http://localhost:8080"
        self.demo_agents = {}
        self.demo_customers = {}
        self.demo_instances = {}
        
        # Demo data
        self.sample_agents = [
            {
                "name": "Data Analyzer",
                "description": "Advanced data analysis and visualization agent",
                "category": "analytics",
                "version": "1.2.0",
                "docker_image": "agenthub/data-analyzer:latest"
            },
            {
                "name": "Text Processor",
                "description": "Natural language processing and text analysis",
                "category": "nlp",
                "version": "2.1.0",
                "docker_image": "agenthub/text-processor:latest"
            },
            {
                "name": "Image Generator",
                "description": "AI-powered image generation and editing",
                "category": "creative",
                "version": "1.0.5",
                "docker_image": "agenthub/image-generator:latest"
            }
        ]
        
        self.sample_customers = [
            {
                "name": "Alice Johnson",
                "email": "alice@techcorp.com",
                "api_key": "ak_alice_12345678",
                "credits": 100.0
            },
            {
                "name": "Bob Smith",
                "email": "bob@startup.io",
                "api_key": "ak_bob_87654321",
                "credits": 50.0
            }
        ]
    
    async def run_demo(self):
        """Run the complete marketplace demo"""
        print("🚀 AgentHub Marketplace Demo")
        print("=" * 60)
        
        try:
            # Setup phase
            await self.setup_demo_environment()
            
            # Stage 1: Registration
            await self.demo_agent_registration()
            
            # Stage 2: Discovery and Selection
            await self.demo_agent_discovery()
            
            # Stage 3: Instantiation
            await self.demo_instance_creation()
            
            # Stage 4: Active/Running
            await self.demo_task_execution()
            
            # Stage 5: Monitoring and Maintenance
            await self.demo_monitoring()
            
            # Stage 6: Pause/Resume
            await self.demo_pause_resume()
            
            # Stage 7: Termination
            await self.demo_termination()
            
            # Stage 8: Deregistration
            await self.demo_deregistration()
            
            # Customer dashboard overview
            await self.demo_customer_dashboard()
            
        except KeyboardInterrupt:
            print("\n⚠️  Demo interrupted by user")
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
        finally:
            await self.cleanup_demo()
    
    async def setup_demo_environment(self):
        """Setup the demo environment"""
        print("\n📋 Setting up demo environment...")
        
        # Create demo directories
        self.demo_dir.mkdir(exist_ok=True)
        
        # Create sample agent configurations
        await self.create_sample_agent_configs()
        
        # Create sample Docker agents
        await self.create_sample_docker_agents()
        
        # Start the AgentHub server
        await self.start_agenthub_server()
        
        # Initialize database and create users
        await self.initialize_database()
        
        print("✅ Demo environment ready!")
    
    async def create_sample_agent_configs(self):
        """Create configuration files for sample agents"""
        print("📝 Creating sample agent configurations...")
        
        for agent in self.sample_agents:
            config = {
                "name": agent["name"],
                "description": agent["description"],
                "category": agent["category"],
                "version": agent["version"],
                "author": "AgentHub Demo",
                "license": "MIT",
                "runtime": "managed",
                "protocol": "ACP",
                "pricing": {
                    "type": "per_request",
                    "price": round(0.01 + hash(agent["name"]) % 10 / 100, 2),
                    "currency": "USD"
                },
                "capabilities": [
                    {
                        "name": "process",
                        "description": f"Main processing capability for {agent['name']}",
                        "parameters": {
                            "data": {"type": "string", "required": True}
                        }
                    }
                ],
                "endpoints": [
                    {
                        "path": "/process",
                        "method": "POST",
                        "description": "Process data"
                    },
                    {
                        "path": "/acp/handshake",
                        "method": "POST",
                        "description": "ACP handshake"
                    },
                    {
                        "path": "/acp/task",
                        "method": "POST",
                        "description": "ACP task execution"
                    }
                ]
            }
            
            config_file = self.demo_dir / f"{agent['name'].lower().replace(' ', '_')}_config.yaml"
            
            import yaml
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            agent["config_file"] = config_file
    
    async def create_sample_docker_agents(self):
        """Create sample Docker agent implementations"""
        print("🐳 Creating sample Docker agents...")
        
        for agent in self.sample_agents:
            agent_dir = self.demo_dir / f"{agent['name'].lower().replace(' ', '_')}_agent"
            agent_dir.mkdir(exist_ok=True)
            
            # Create agent implementation
            agent_code = self.generate_agent_code(agent)
            with open(agent_dir / "agent.py", 'w') as f:
                f.write(agent_code)
            
            # Create requirements.txt
            requirements = """fastapi>=0.68.0
uvicorn>=0.15.0
pydantic>=1.8.0
httpx>=0.24.0
websockets>=12.0
"""
            with open(agent_dir / "requirements.txt", 'w') as f:
                f.write(requirements)
            
            # Create Dockerfile
            dockerfile = f"""FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY agent.py .

EXPOSE 8000

CMD ["python", "agent.py"]
"""
            with open(agent_dir / "Dockerfile", 'w') as f:
                f.write(dockerfile)
            
            # Build Docker image
            print(f"🔨 Building Docker image for {agent['name']}...")
            result = subprocess.run([
                "docker", "build", "-t", agent["docker_image"], str(agent_dir)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"⚠️  Warning: Failed to build {agent['name']} image: {result.stderr}")
                print("   Continuing demo without this agent...")
                continue
            
            agent["docker_built"] = True
    
    def generate_agent_code(self, agent: Dict[str, Any]) -> str:
        """Generate sample agent implementation code"""
        agent_name = agent["name"]
        category = agent["category"]
        
        return f'''#!/usr/bin/env python3
"""
{agent_name} Agent - Demo Implementation
Category: {category}
"""

import asyncio
import json
import uuid
import time
import os
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="{agent_name}", description="{agent['description']}")

class TaskRequest(BaseModel):
    data: str
    parameters: Dict[str, Any] = {{}}

class TaskResponse(BaseModel):
    result: Any
    status: str = "completed"
    agent_name: str = "{agent_name}"
    timestamp: str

class ACPHandshakeRequest(BaseModel):
    protocol_version: str = "1.0"
    client_type: str

class ACPTaskRequest(BaseModel):
    endpoint: str
    parameters: Dict[str, Any]
    timeout: float = 30.0

# Agent metadata from environment
agent_id = os.getenv("AGENTHUB_AGENT_ID", "demo-agent")
agent_port = int(os.getenv("AGENTHUB_AGENT_PORT", "8000"))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {{
        "status": "healthy",
        "agent": "{agent_name}",
        "timestamp": datetime.now().isoformat(),
        "agent_id": agent_id
    }}

@app.post("/process")
async def process_data(request: TaskRequest):
    """Main processing endpoint"""
    try:
        # Simulate processing based on category
        result = await simulate_processing(request.data, "{category}")
        
        return TaskResponse(
            result=result,
            status="completed",
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Processing error: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/acp/handshake")
async def acp_handshake(request: ACPHandshakeRequest):
    """ACP protocol handshake"""
    return {{
        "status": "ready",
        "protocol_version": "1.0",
        "agent_id": agent_id,
        "agent_name": "{agent_name}",
        "capabilities": ["process"],
        "timestamp": datetime.now().isoformat()
    }}

@app.post("/acp/task")
async def acp_task(request: ACPTaskRequest):
    """ACP task execution"""
    try:
        if request.endpoint == "/process":
            data = request.parameters.get("data", "")
            result = await simulate_processing(data, "{category}")
            
            return {{
                "status": "completed",
                "result": result,
                "agent_id": agent_id,
                "execution_time": 0.5,
                "timestamp": datetime.now().isoformat()
            }}
        else:
            raise HTTPException(status_code=404, detail="Endpoint not found")
    except Exception as e:
        logger.error(f"ACP task error: {{e}}")
        return {{
            "status": "failed",
            "error": str(e),
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        }}

@app.post("/acp/heartbeat")
async def acp_heartbeat():
    """ACP heartbeat"""
    return {{
        "status": "alive",
        "agent_id": agent_id,
        "timestamp": datetime.now().isoformat()
    }}

async def simulate_processing(data: str, category: str) -> Dict[str, Any]:
    """Simulate category-specific processing"""
    # Add realistic processing delay
    await asyncio.sleep(0.1 + len(data) / 1000)
    
    if category == "analytics":
        return {{
            "analysis": {{
                "data_length": len(data),
                "word_count": len(data.split()),
                "sentiment": "positive" if "good" in data.lower() else "neutral",
                "confidence": 0.85,
                "categories": ["business", "technology"],
                "summary": f"Analyzed {{len(data)}} characters of data"
            }},
            "processing_time": 0.1,
            "agent": "{agent_name}"
        }}
    elif category == "nlp":
        return {{
            "text_analysis": {{
                "language": "en",
                "entities": ["demo", "text", "processing"],
                "keywords": data.split()[:5],
                "readability_score": 7.5,
                "processed_text": data.upper(),
                "token_count": len(data.split())
            }},
            "processing_time": 0.15,
            "agent": "{agent_name}"
        }}
    elif category == "creative":
        return {{
            "generation": {{
                "prompt": data,
                "image_url": f"https://demo.images/{agent_name.lower().replace(' ', '-')}.jpg",
                "style": "realistic",
                "dimensions": "1024x1024",
                "seed": hash(data) % 10000,
                "description": f"Generated image based on: {{data[:50]}}..."
            }},
            "processing_time": 0.3,
            "agent": "{agent_name}"
        }}
    else:
        return {{
            "generic_result": {{
                "input": data,
                "output": f"Processed by {{agent_name}}: {{data}}",
                "metadata": {{
                    "category": category,
                    "timestamp": datetime.now().isoformat()
                }}
            }},
            "agent": "{agent_name}"
        }}

if __name__ == "__main__":
    logger.info(f"Starting {{agent_name}} agent on port {{agent_port}}")
    uvicorn.run(app, host="0.0.0.0", port=agent_port)
'''
    
    async def start_agenthub_server(self):
        """Start the AgentHub server"""
        print("🖥️  Starting AgentHub server...")
        
        # Start server in development mode
        cmd = [
            sys.executable, "-m", "agenthub_server.cli", "dev",
            "--port", "8080",
            "--database-url", "sqlite:///demo_agenthub.db"
        ]
        
        self.server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for server to start
        await self.wait_for_server()
        print("✅ AgentHub server started")
    
    async def wait_for_server(self, timeout: int = 30):
        """Wait for server to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.server_url}/health", timeout=5.0)
                    if response.status_code == 200:
                        return
            except:
                pass
            
            await asyncio.sleep(1)
        
        raise Exception("Server failed to start within timeout")
    
    async def initialize_database(self):
        """Initialize database and create demo users"""
        print("🗄️  Initializing database and creating demo users...")
        
        for customer in self.sample_customers:
            cmd = [
                sys.executable, "-m", "agenthub_server.cli", "create-user",
                "--api-key", customer["api_key"],
                "--email", customer["email"],
                "--name", customer["name"],
                "--credits", str(customer["credits"]),
                "--database-url", "sqlite:///demo_agenthub.db"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"⚠️  Warning: Failed to create user {customer['name']}: {result.stderr}")
    
    async def demo_agent_registration(self):
        """Demo Stage 1: Agent Registration"""
        print("\n" + "="*60)
        print("🔄 STAGE 1: AGENT REGISTRATION")
        print("="*60)
        
        for agent in self.sample_agents:
            if not agent.get("docker_built"):
                continue
                
            print(f"\n📝 Registering agent: {agent['name']}")
            
            cmd = [
                sys.executable, "-m", "agenthub_server.cli", "register-docker-agent",
                "--config", str(agent["config_file"]),
                "--docker-image", agent["docker_image"],
                "--database-url", "sqlite:///demo_agenthub.db"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extract agent ID from output
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if "Agent ID:" in line:
                        agent_id = line.split("Agent ID:")[1].strip()
                        agent["id"] = agent_id
                        self.demo_agents[agent_id] = agent
                        print(f"✅ Registered {agent['name']} with ID: {agent_id}")
                        break
            else:
                print(f"❌ Failed to register {agent['name']}: {result.stderr}")
        
        print(f"\n📊 Registration Summary: {len(self.demo_agents)} agents registered")
        self.pause_for_user()
    
    async def demo_agent_discovery(self):
        """Demo Stage 2: Discovery and Selection"""
        print("\n" + "="*60)
        print("🔍 STAGE 2: DISCOVERY AND SELECTION")
        print("="*60)
        
        customer = self.sample_customers[0]  # Use Alice for discovery
        
        print(f"\n👤 Customer: {customer['name']} discovering agents...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.server_url}/marketplace/agents",
                    headers={"Authorization": f"Bearer {customer['api_key']}"},
                    params={"limit": 10}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    agents = data.get("agents", [])
                    
                    print(f"\n📋 Found {len(agents)} agents in marketplace:")
                    
                    for agent in agents:
                        marketplace_info = agent.get("marketplace_info", {})
                        pricing_info = marketplace_info.get("pricing_info", {})
                        
                        print(f"\n🤖 {agent['name']}")
                        print(f"   📂 Category: {agent['category']}")
                        print(f"   📝 Description: {agent['description']}")
                        print(f"   💰 Price: ${pricing_info.get('price', 0)} per {pricing_info.get('type', 'request')}")
                        print(f"   🏃 Total Instances: {marketplace_info.get('total_instances', 0)}")
                        print(f"   👤 Your Instances: {marketplace_info.get('customer_instances', 0)}")
                        
                        availability = marketplace_info.get("availability", {})
                        if availability.get("available"):
                            print("   ✅ Available")
                        else:
                            print("   ❌ Not Available")
                
                else:
                    print(f"❌ Discovery failed: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Discovery error: {e}")
        
        self.pause_for_user()
    
    async def demo_instance_creation(self):
        """Demo Stage 3: Instantiation"""
        print("\n" + "="*60)
        print("🚀 STAGE 3: INSTANTIATION")
        print("="*60)
        
        # Create instances for both customers
        for customer in self.sample_customers:
            print(f"\n👤 {customer['name']} creating agent instances...")
            
            # Create 2 instances per customer
            agent_ids = list(self.demo_agents.keys())[:2]
            
            for agent_id in agent_ids:
                agent = self.demo_agents[agent_id]
                print(f"\n🔧 Creating instance of {agent['name']}...")
                
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            f"{self.server_url}/marketplace/instances",
                            headers={"Authorization": f"Bearer {customer['api_key']}"},
                            json={
                                "agent_id": agent_id,
                                "instance_config": {
                                    "memory_limit": "512M",
                                    "cpu_limit": "0.5"
                                }
                            }
                        )
                        
                        if response.status_code == 200:
                            instance_data = response.json()
                            instance_id = instance_data["instance_id"]
                            
                            self.demo_instances[instance_id] = {
                                "instance_id": instance_id,
                                "agent_id": agent_id,
                                "customer_id": customer["api_key"],
                                "agent_name": agent["name"]
                            }
                            
                            print(f"✅ Instance created: {instance_id[:8]}...")
                            print(f"   🤖 Agent: {agent['name']}")
                            print(f"   📊 Status: {instance_data['status']}")
                            
                            # Wait a moment for container to start
                            await asyncio.sleep(3)
                        
                        else:
                            print(f"❌ Failed to create instance: {response.status_code}")
                            print(f"   Error: {response.text}")
                
                except Exception as e:
                    print(f"❌ Instance creation error: {e}")
        
        print(f"\n📊 Instantiation Summary: {len(self.demo_instances)} instances created")
        self.pause_for_user()
    
    async def demo_task_execution(self):
        """Demo Stage 4: Active/Running"""
        print("\n" + "="*60)
        print("⚡ STAGE 4: ACTIVE/RUNNING - TASK EXECUTION")
        print("="*60)
        
        # Execute tasks on different instances
        sample_tasks = [
            {"data": "Analyze customer satisfaction data for Q4 2024", "agent_type": "analytics"},
            {"data": "Process this contract for key terms and conditions", "agent_type": "nlp"},
            {"data": "Generate a logo for TechCorp startup", "agent_type": "creative"},
            {"data": "Review quarterly financial performance metrics", "agent_type": "analytics"}
        ]
        
        customer = self.sample_customers[0]  # Use Alice for task execution
        
        for i, task in enumerate(sample_tasks):
            if i >= len(self.demo_instances):
                break
                
            instance_id = list(self.demo_instances.keys())[i]
            instance = self.demo_instances[instance_id]
            
            print(f"\n🎯 Executing task {i+1} on {instance['agent_name']} instance...")
            print(f"   📝 Task: {task['data'][:50]}...")
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.server_url}/marketplace/instances/{instance_id}/execute",
                        headers={"Authorization": f"Bearer {customer['api_key']}"},
                        json={
                            "endpoint": "/process",
                            "parameters": {"data": task["data"]},
                            "timeout": 30
                        }
                    )
                    
                    if response.status_code == 200:
                        task_data = response.json()
                        print(f"✅ Task submitted: {task_data['task_id'][:8]}...")
                        print(f"   📊 Status: {task_data['status']}")
                        
                        # Wait for task completion and show result
                        await self.wait_for_task_completion(task_data['task_id'], customer['api_key'])
                    
                    else:
                        print(f"❌ Task execution failed: {response.status_code}")
            
            except Exception as e:
                print(f"❌ Task execution error: {e}")
            
            await asyncio.sleep(2)  # Brief pause between tasks
        
        self.pause_for_user()
    
    async def wait_for_task_completion(self, task_id: str, api_key: str):
        """Wait for task completion and show result"""
        for _ in range(10):  # Wait up to 10 seconds
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.server_url}/tasks/{task_id}",
                        headers={"Authorization": f"Bearer {api_key}"}
                    )
                    
                    if response.status_code == 200:
                        task_data = response.json()
                        if task_data.get("status") == "completed":
                            result = task_data.get("result", {})
                            print(f"   ✅ Task completed in {task_data.get('execution_time', 0):.2f}s")
                            print(f"   💰 Cost: ${task_data.get('cost', 0):.3f}")
                            
                            # Show a sample of the result
                            if isinstance(result, dict):
                                if "analysis" in result:
                                    analysis = result["analysis"]
                                    print(f"   📊 Analysis: {analysis.get('summary', 'Data processed')}")
                                elif "text_analysis" in result:
                                    text_analysis = result["text_analysis"]
                                    print(f"   📝 Language: {text_analysis.get('language', 'unknown')}")
                                    print(f"   🔤 Tokens: {text_analysis.get('token_count', 0)}")
                                elif "generation" in result:
                                    generation = result["generation"]
                                    print(f"   🎨 Generated: {generation.get('description', 'Image created')}")
                            return
                        elif task_data.get("status") == "failed":
                            print(f"   ❌ Task failed: {task_data.get('error', 'Unknown error')}")
                            return
            except:
                pass
            
            await asyncio.sleep(1)
        
        print("   ⏳ Task still running...")
    
    async def demo_monitoring(self):
        """Demo Stage 5: Monitoring and Maintenance"""
        print("\n" + "="*60)
        print("📊 STAGE 5: MONITORING AND MAINTENANCE")
        print("="*60)
        
        customer = self.sample_customers[0]
        
        print(f"\n🔍 Monitoring instances for {customer['name']}...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.server_url}/marketplace/instances",
                    headers={"Authorization": f"Bearer {customer['api_key']}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    instances = data.get("instances", [])
                    
                    print(f"\n📈 Instance Monitoring Report:")
                    print("-" * 50)
                    
                    for instance in instances:
                        resource_usage = instance.get("resource_usage", {})
                        health_status = instance.get("health_status", {})
                        billing_info = instance.get("billing_info", {})
                        
                        print(f"\n🔧 Instance: {instance['instance_id'][:8]}...")
                        print(f"   🤖 Agent: {instance['agent_id'][:8]}...")
                        print(f"   📊 Status: {instance['status']}")
                        print(f"   ⏱️  Uptime: {resource_usage.get('uptime', 0)/3600:.2f} hours")
                        print(f"   💾 CPU: {resource_usage.get('cpu_usage', 0):.1f}%")
                        print(f"   🧠 Memory: {resource_usage.get('memory_usage', 0):.1f}%")
                        print(f"   🎯 Tasks: {resource_usage.get('task_count', 0)}")
                        print(f"   💰 Cost: ${billing_info.get('total_cost', 0):.2f}")
                        print(f"   🏥 Health: {'✅' if health_status.get('healthy', False) else '❌'}")
                
                else:
                    print(f"❌ Monitoring failed: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
        
        # Show ACP status
        print(f"\n📡 ACP Protocol Status:")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.server_url}/acp/status",
                    headers={"Authorization": f"Bearer {customer['api_key']}"}
                )
                
                if response.status_code == 200:
                    acp_data = response.json()
                    connected_agents = acp_data.get("connected_agents", [])
                    print(f"   🔗 Connected Agents: {len(connected_agents)}")
                    print(f"   📊 Total Connections: {acp_data.get('total_connections', 0)}")
        except:
            print("   ⚠️  ACP status unavailable")
        
        self.pause_for_user()
    
    async def demo_pause_resume(self):
        """Demo Stage 6: Pause/Resume"""
        print("\n" + "="*60)
        print("⏸️ STAGE 6: PAUSE/RESUME")
        print("="*60)
        
        customer = self.sample_customers[0]
        instance_id = list(self.demo_instances.keys())[0] if self.demo_instances else None
        
        if not instance_id:
            print("❌ No instances available for pause/resume demo")
            return
        
        instance = self.demo_instances[instance_id]
        
        print(f"\n⏸️  Pausing instance of {instance['agent_name']}...")
        print("   💡 Use case: Save costs during idle periods")
        
        try:
            async with httpx.AsyncClient() as client:
                # Pause instance
                response = await client.post(
                    f"{self.server_url}/marketplace/instances/{instance_id}/pause",
                    headers={"Authorization": f"Bearer {customer['api_key']}"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ {result['message']}")
                    print(f"   📊 Status: {result['status']}")
                    
                    await asyncio.sleep(3)
                    
                    # Show instance details while paused
                    await self.show_instance_details(instance_id, customer['api_key'])
                    
                    print(f"\n▶️  Resuming instance...")
                    
                    # Resume instance
                    response = await client.post(
                        f"{self.server_url}/marketplace/instances/{instance_id}/resume",
                        headers={"Authorization": f"Bearer {customer['api_key']}"}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"✅ {result['message']}")
                        print(f"   📊 Status: {result['status']}")
                        
                        await asyncio.sleep(2)
                        await self.show_instance_details(instance_id, customer['api_key'])
                    
                    else:
                        print(f"❌ Resume failed: {response.status_code}")
                
                else:
                    print(f"❌ Pause failed: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Pause/Resume error: {e}")
        
        self.pause_for_user()
    
    async def show_instance_details(self, instance_id: str, api_key: str):
        """Show detailed instance information"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.server_url}/marketplace/instances/{instance_id}",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                
                if response.status_code == 200:
                    instance = response.json()
                    billing = instance.get("billing_info", {})
                    
                    print(f"   📊 Current Status: {instance['status']}")
                    print(f"   💰 Current Cost: ${billing.get('total_cost', 0):.3f}")
                    if instance.get('paused_at'):
                        print(f"   ⏸️  Paused At: {instance['paused_at']}")
        except:
            pass
    
    async def demo_termination(self):
        """Demo Stage 7: Termination"""
        print("\n" + "="*60)
        print("🛑 STAGE 7: TERMINATION")
        print("="*60)
        
        customer = self.sample_customers[1]  # Use Bob for termination
        customer_instances = [
            inst_id for inst_id, inst in self.demo_instances.items()
            if inst["customer_id"] == customer["api_key"]
        ]
        
        if not customer_instances:
            print(f"❌ No instances found for {customer['name']}")
            return
        
        instance_id = customer_instances[0]
        instance = self.demo_instances[instance_id]
        
        print(f"\n🛑 {customer['name']} terminating instance of {instance['agent_name']}...")
        print("   💡 Use case: No longer needed, final billing calculation")
        
        # Show pre-termination details
        await self.show_instance_details(instance_id, customer['api_key'])
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.server_url}/marketplace/instances/{instance_id}",
                    headers={"Authorization": f"Bearer {customer['api_key']}"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ {result['message']}")
                    print(f"   📊 Final Status: {result['status']}")
                    
                    # Show final billing
                    await asyncio.sleep(2)
                    print("\n💰 Final Billing Summary:")
                    await self.show_instance_details(instance_id, customer['api_key'])
                    
                    # Remove from demo instances
                    del self.demo_instances[instance_id]
                
                else:
                    print(f"❌ Termination failed: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Termination error: {e}")
        
        self.pause_for_user()
    
    async def demo_deregistration(self):
        """Demo Stage 8: Deregistration"""
        print("\n" + "="*60)
        print("🗑️ STAGE 8: DEREGISTRATION")
        print("="*60)
        
        print("\n🗑️  Agent deregistration demo:")
        print("   💡 Use case: Remove agent from marketplace")
        print("   ⚠️  Only possible when no active instances exist")
        
        # Check for active instances
        active_instances = len(self.demo_instances)
        
        if active_instances > 0:
            print(f"\n⚠️  Cannot deregister agents: {active_instances} active instances exist")
            print("   📝 In a real scenario, all instances must be terminated first")
            print("   🔄 This protects against accidental data loss")
        else:
            print("\n✅ All instances terminated - agents can now be deregistered")
            print("   🔧 Admin process would mark agents as 'deregistered'")
            print("   📊 Historical data preserved for analytics")
        
        print("\n📋 Deregistration Process:")
        print("   1. ✅ Check for active instances")
        print("   2. ✅ Validate permissions")
        print("   3. ✅ Mark as deregistered (preserve data)")
        print("   4. ✅ Clean up Docker resources")
        print("   5. ✅ Update marketplace catalog")
        
        self.pause_for_user()
    
    async def demo_customer_dashboard(self):
        """Show customer dashboard overview"""
        print("\n" + "="*60)
        print("📊 CUSTOMER DASHBOARD OVERVIEW")
        print("="*60)
        
        for customer in self.sample_customers:
            print(f"\n👤 Dashboard for {customer['name']}:")
            print("-" * 40)
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.server_url}/marketplace/dashboard",
                        headers={"Authorization": f"Bearer {customer['api_key']}"}
                    )
                    
                    if response.status_code == 200:
                        dashboard = response.json()
                        summary = dashboard.get("summary", {})
                        billing = dashboard.get("billing", {})
                        
                        print(f"📈 Summary:")
                        print(f"   Total Instances: {summary.get('total_instances', 0)}")
                        print(f"   Running: {summary.get('running_instances', 0)}")
                        print(f"   Paused: {summary.get('paused_instances', 0)}")
                        print(f"   Total Uptime: {summary.get('total_uptime_hours', 0):.2f} hours")
                        
                        print(f"\n💰 Billing:")
                        print(f"   Current Month: ${billing.get('current_month_cost', 0):.2f}")
                        print(f"   Currency: {billing.get('currency', 'USD')}")
                        
                        recent = dashboard.get("recent_instances", [])
                        if recent:
                            print(f"\n🕒 Recent Activity:")
                            for instance in recent[:3]:
                                print(f"   🔧 {instance['instance_id'][:8]}... ({instance['status']})")
                    
                    else:
                        print(f"❌ Dashboard unavailable: {response.status_code}")
            
            except Exception as e:
                print(f"❌ Dashboard error: {e}")
        
        self.pause_for_user()
    
    def pause_for_user(self):
        """Pause for user to read output"""
        try:
            input("\n⏸️  Press Enter to continue to next stage...")
        except KeyboardInterrupt:
            raise
    
    async def cleanup_demo(self):
        """Clean up demo environment"""
        print("\n🧹 Cleaning up demo environment...")
        
        # Stop all containers
        for agent in self.sample_agents:
            if agent.get("docker_built"):
                try:
                    subprocess.run([
                        "docker", "stop", f"agenthub_agent_{agent.get('id', 'unknown')}"
                    ], capture_output=True)
                    subprocess.run([
                        "docker", "rm", f"agenthub_agent_{agent.get('id', 'unknown')}"
                    ], capture_output=True)
                except:
                    pass
        
        # Stop server
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
        
        print("✅ Cleanup complete")

async def main():
    """Main demo function"""
    demo = MarketplaceDemo()
    
    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        print("\n\n🛑 Demo interrupted by user")
        asyncio.create_task(demo.cleanup_demo())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await demo.run_demo()
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await demo.cleanup_demo()

if __name__ == "__main__":
    print("🚀 Starting AgentHub Marketplace Demo...")
    print("This demo will showcase all 8 stages of the agent lifecycle")
    print("Make sure Docker is running and you have the required dependencies")
    print("\nPress Ctrl+C at any time to stop the demo\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo terminated by user")
    except Exception as e:
        print(f"\n❌ Demo startup failed: {e}")