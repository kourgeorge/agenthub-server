"""
AgentHub Server Demo - Complete example using an existing AgentHub marketplace server

This example demonstrates:
1. Creating multiple AI agents using the core AgentHub SDK
2. Connecting to an existing AgentHub marketplace server on localhost:8080
3. Registering agents with the hub
4. Using the marketplace to discover and hire agents
5. Monitoring agent performance and analytics

Prerequisites:
    - AgentHub Server must be running on localhost:8080
    - Start the server with: python -m agenthub_server.cli start-server

Usage:
    python examples/demo.py

Note: This requires both the AgentHub SDK and AgentHub Server packages
"""

import asyncio
import time
import threading
import json
import sys
import os
from pathlib import Path
import logging

# Add the parent directory to the path to import the server modules
sys.path.insert(0, str(Path(__file__).parent.parent))
# AgentHub Server imports
from agenthub_server.models import AgentMetadata

# For the demo, we'll simulate AgentBuilder functionality
# In practice, you'd import from the actual agenthub package
class MockAgentBuilder:
    """Mock AgentBuilder for demo purposes"""
    
    def __init__(self, name):
        self.agent_name = name
        self.endpoints = {}
        self.metadata = None
    
    def endpoint(self, path, description=""):
        """Mock endpoint decorator"""
        def decorator(func):
            self.endpoints[path] = {
                "function": func,
                "description": description,
                "path": path
            }
            return func
        return decorator
    
    def set_metadata(self, metadata_dict):
        """Set agent metadata"""
        self.metadata = AgentMetadata(**metadata_dict)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_calculator_agent():
    """Create a calculator agent"""
    agent = MockAgentBuilder("calculator-agent")
    
    @agent.endpoint("/add", description="Add two numbers")
    def add(request):
        a = request.get("a", 0)
        b = request.get("b", 0)
        result = a + b
        return {"result": result, "operation": "addition", "inputs": {"a": a, "b": b}}
    
    @agent.endpoint("/multiply", description="Multiply two numbers")
    def multiply(request):
        a = request.get("a", 0)
        b = request.get("b", 0)
        result = a * b
        return {"result": result, "operation": "multiplication", "inputs": {"a": a, "b": b}}
    
    @agent.endpoint("/divide", description="Divide two numbers")
    def divide(request):
        a = request.get("a", 0)
        b = request.get("b", 1)
        if b == 0:
            return {"error": "Division by zero", "inputs": {"a": a, "b": b}}
        result = a / b
        return {"result": result, "operation": "division", "inputs": {"a": a, "b": b}}
    
    # Set metadata
    agent.set_metadata({
        "name": "Calculator Agent",
        "description": "Performs basic arithmetic operations with high precision",
        "category": "utility",
        "version": "1.0.0",
        "author": "AgentHub Demo",
        "license": "MIT",
        "tags": ["math", "calculator", "utility"],
        "pricing": {"type": "per_request", "price": 0.01, "currency": "USD"}
    })
    
    return agent


def create_text_processor_agent():
    """Create a text processing agent"""
    agent = MockAgentBuilder("text-processor-agent")
    
    @agent.endpoint("/uppercase", description="Convert text to uppercase")
    def uppercase(request):
        text = request.get("text", "")
        return {"result": text.upper(), "original": text, "operation": "uppercase"}
    
    @agent.endpoint("/count_words", description="Count words in text")
    def count_words(request):
        text = request.get("text", "")
        words = len(text.split())
        characters = len(text)
        return {
            "word_count": words,
            "character_count": characters,
            "original": text,
            "operation": "word_count"
        }
    
    @agent.endpoint("/reverse", description="Reverse text")
    def reverse(request):
        text = request.get("text", "")
        return {"result": text[::-1], "original": text, "operation": "reverse"}
    
    # Set metadata
    agent.set_metadata({
        "name": "Text Processor Agent",
        "description": "Processes text with various transformations and analysis",
        "category": "text_processing",
        "version": "1.2.0",
        "author": "AgentHub Demo",
        "license": "MIT",
        "tags": ["text", "processing", "nlp", "utility"],
        "pricing": {"type": "per_request", "price": 0.005, "currency": "USD"}
    })
    
    return agent


def create_data_analyzer_agent():
    """Create a data analysis agent"""
    agent = MockAgentBuilder("data-analyzer-agent")
    
    @agent.endpoint("/analyze_numbers", description="Analyze a list of numbers")
    def analyze_numbers(request):
        numbers = request.get("numbers", [])
        if not numbers:
            return {"error": "No numbers provided"}
        
        try:
            total = sum(numbers)
            count = len(numbers)
            average = total / count
            minimum = min(numbers)
            maximum = max(numbers)
            
            return {
                "count": count,
                "sum": total,
                "average": average,
                "min": minimum,
                "max": maximum,
                "range": maximum - minimum,
                "operation": "number_analysis"
            }
        except Exception as e:
            return {"error": str(e)}
    
    @agent.endpoint("/find_patterns", description="Find patterns in data")
    def find_patterns(request):
        data = request.get("data", [])
        pattern_type = request.get("pattern_type", "frequency")
        
        if pattern_type == "frequency":
            frequency = {}
            for item in data:
                frequency[str(item)] = frequency.get(str(item), 0) + 1
            return {"frequency": frequency, "most_common": max(frequency.items(), key=lambda x: x[1]) if frequency else None}
        
        return {"error": "Unsupported pattern type"}
    
    # Set metadata
    agent.set_metadata({
        "name": "Data Analyzer Agent",
        "description": "Analyzes datasets and finds patterns in data",
        "category": "analytics",
        "version": "2.0.0",
        "author": "AgentHub Demo",
        "license": "Apache-2.0",
        "tags": ["data", "analytics", "statistics", "patterns"],
        "pricing": {"type": "per_request", "price": 0.02, "currency": "USD"}
    })
    
    return agent


def start_mock_agent_server(agent, port):
    """Start a mock HTTP server for an agent"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    
    class AgentHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                
                # Find the endpoint handler
                path = self.path
                if path in agent.endpoints:
                    handler = agent.endpoints[path]["function"]
                    result = handler(request_data)
                    
                    # Wrap in AgentHub protocol format
                    response = {
                        "agent_id": agent.agent_name,
                        "endpoint": path,
                        "result": result,
                        "status": "success",
                        "timestamp": time.time()
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()
            except Exception as e:
                error_response = {
                    "agent_id": agent.agent_name,
                    "endpoint": self.path,
                    "error": str(e),
                    "status": "error",
                    "timestamp": time.time()
                }
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
        
        def log_message(self, format, *args):
            # Suppress log messages
            pass
    
    server = HTTPServer(('localhost', port), AgentHandler)
    logger.info(f"Starting mock agent server for {agent.agent_name} on port {port}")
    server.serve_forever()


def start_agent_servers(agents_config):
    """Start agent servers in separate threads"""
    def start_agent_server(agent, port):
        try:
            start_mock_agent_server(agent, port)
        except Exception as e:
            logger.error(f"Failed to start {agent.agent_name}: {e}")
    
    threads = []
    for agent, port in agents_config:
        thread = threading.Thread(target=start_agent_server, args=(agent, port), daemon=True)
        thread.start()
        threads.append(thread)
        time.sleep(1)  # Give each server time to start
    
    return threads


async def check_server_health():
    """Check if the AgentHub server is running on localhost:8080"""
    import urllib.request
    import urllib.error
    
    try:
        with urllib.request.urlopen("http://localhost:8080/health") as response:
            health = json.loads(response.read().decode())
        logger.info(f"✅ AgentHub server is running - {health.get('agents_count', 0)} agents registered")
        return True
    except urllib.error.URLError as e:
        logger.error(f"❌ AgentHub server is not running on localhost:8080: {e}")
        logger.error("Please start the server with: python -m agenthub_server.cli start-server")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking server health: {e}")
        return False


async def register_agents_with_hub(agents_config):
    """Register agents with the AgentHub marketplace via HTTP API"""
    import urllib.request
    import urllib.parse
    
    agent_ids = []
    for agent, port in agents_config:
        try:
            # Prepare agent registration data
            registration_data = {
                "name": agent.metadata.name,
                "description": agent.metadata.description,
                "category": agent.metadata.category,
                "version": agent.metadata.version,
                "author": agent.metadata.author,
                "license": agent.metadata.license,
                "tags": agent.metadata.tags,
                "pricing": agent.metadata.pricing,
                "endpoint_url": f"http://localhost:{port}",
                "endpoints": list(agent.endpoints.keys())
            }
            
            # Register with the marketplace
            req = urllib.request.Request(
                "http://localhost:8080/agents",
                data=json.dumps(registration_data).encode(),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                agent_id = result["agent_id"]
                agent_ids.append((agent_id, agent.agent_name))
                logger.info(f"✅ Registered {agent.agent_name} with ID: {agent_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to register {agent.agent_name}: {e}")
    
    return agent_ids


async def demonstrate_marketplace_usage():
    """Demonstrate using the AgentHub marketplace"""
    logger.info("🌟 Demonstrating AgentHub Marketplace Usage")
    
    # Note: In a real implementation, you'd use the AgentHub client
    # For this demo, we'll make direct HTTP requests
    import urllib.request
    import urllib.parse
    import json
    
    base_url = "http://localhost:8080"
    
    try:
        # Search for agents
        logger.info("� Searching for available agents...")
        with urllib.request.urlopen(f"{base_url}/agents") as response:
            agents_data = json.loads(response.read().decode())
        agents = agents_data["agents"]
        
        logger.info(f"📋 Found {len(agents)} agents:")
        for agent in agents:
            logger.info(f"  🤖 {agent['name']} ({agent['category']}) - {agent['total_tasks']} tasks completed")
        
        # Hire the calculator agent for a task
        calculator_agent = next((a for a in agents if "Calculator" in a['name']), None)
        if calculator_agent:
            logger.info("🧮 Hiring Calculator Agent for addition task...")
            
            task_data = {
                "agent_id": calculator_agent['id'],
                "endpoint": "/add",
                "parameters": {"a": 15, "b": 27}
            }
            
            # Create task
            req = urllib.request.Request(
                f"{base_url}/tasks",
                data=json.dumps(task_data).encode(),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                task = json.loads(response.read().decode())
            task_id = task["task_id"]
            logger.info(f"� Created task {task_id}")
            
            # Wait for task completion
            for i in range(10):
                await asyncio.sleep(1)
                with urllib.request.urlopen(f"{base_url}/tasks/{task_id}") as response:
                    task_status = json.loads(response.read().decode())
                
                if task_status["status"] == "completed":
                    result = task_status["result"]
                    logger.info(f"✅ Task completed! Result: 15 + 27 = {result['result']['result']}")
                    logger.info(f"⏱️  Execution time: {task_status['execution_time']:.3f}s")
                    break
                elif task_status["status"] == "failed":
                    logger.error(f"❌ Task failed: {task_status.get('error')}")
                    break
            else:
                logger.warning("⏰ Task did not complete within timeout")
        
        # Hire the text processor agent for another task
        text_agent = next((a for a in agents if "Text" in a['name']), None)
        if text_agent:
            logger.info("📝 Hiring Text Processor Agent for text transformation...")
            
            task_data = {
                "agent_id": text_agent['id'],
                "endpoint": "/uppercase",
                "parameters": {"text": "Hello AgentHub Marketplace!"}
            }
            
            # Create task
            req = urllib.request.Request(
                f"{base_url}/tasks",
                data=json.dumps(task_data).encode(),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                task = json.loads(response.read().decode())
            task_id = task["task_id"]
            logger.info(f"📋 Created task {task_id}")
            
            # Wait for task completion
            for i in range(10):
                await asyncio.sleep(1)
                with urllib.request.urlopen(f"{base_url}/tasks/{task_id}") as response:
                    task_status = json.loads(response.read().decode())
                
                if task_status["status"] == "completed":
                    result = task_status["result"]
                    logger.info(f"✅ Task completed! Result: '{result['result']['result']}'")
                    logger.info(f"⏱️  Execution time: {task_status['execution_time']:.3f}s")
                    break
                elif task_status["status"] == "failed":
                    logger.error(f"❌ Task failed: {task_status.get('error')}")
                    break
            else:
                logger.warning("⏰ Task did not complete within timeout")
        
        logger.info("🎯 Marketplace demo completed!")
        
    except Exception as e:
        logger.error(f"❌ Marketplace demo failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main demo function"""
    logger.info("🚀 Starting AgentHub Demo (connecting to existing server)")
    
    # Check if server is running
    if not await check_server_health():
        logger.error("❌ Cannot proceed without AgentHub server running")
        logger.info("🔧 To start the server, run: python -m agenthub_server.cli start-server")
        return
    
    # Create agents
    logger.info("🤖 Creating agents...")
    calculator = create_calculator_agent()
    text_processor = create_text_processor_agent()
    data_analyzer = create_data_analyzer_agent()
    
    agents_config = [
        (calculator, 8001),
        (text_processor, 8002),
        (data_analyzer, 8003)
    ]
    
    # Start agent servers
    logger.info("🖥️  Starting agent servers...")
    agent_threads = start_agent_servers(agents_config)
    
    # Wait for agent servers to be ready
    await asyncio.sleep(3)
    
    # Register agents with hub
    logger.info("📝 Registering agents with marketplace...")
    agent_ids = await register_agents_with_hub(agents_config)
    
    if not agent_ids:
        logger.error("❌ No agents were registered successfully")
        return
    
    # Demonstrate marketplace usage
    await asyncio.sleep(2)
    await demonstrate_marketplace_usage()
    
    # Keep demo running
    logger.info("🎯 Demo completed! Agent servers will continue running...")
    logger.info("💡 You can now:")
    logger.info("   - Visit http://localhost:8080/health to check server status")
    logger.info("   - Visit http://localhost:8080/agents to see registered agents")
    logger.info("   - Test agents directly: curl http://localhost:8001/add -d '{\"a\":5,\"b\":3}' -H 'Content-Type: application/json'")
    logger.info("   - Press Ctrl+C to stop")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("👋 Stopping demo...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Demo stopped by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()