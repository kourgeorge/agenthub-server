# AgentHub Server Migration

This document explains how the AgentHub server components were separated from the core SDK into a standalone project.

## What Was Moved

The following components were moved from the main `agenthub` package to the new `agenthub-server` project:

### Files Moved:
- `agenthub/database.py` → `agenthub-server/agenthub_server/database.py`
- `agenthub/hub_server.py` → `agenthub-server/agenthub_server/server.py`
- `agenthub/hub_cli.py` → `agenthub-server/agenthub_server/cli.py`
- `agenthub/models.py` → `agenthub-server/agenthub_server/models.py` (copied)
- `examples/agenthub_server_demo.py` → `agenthub-server/examples/demo.py`
- `AGENTHUB_SERVER.md` → `agenthub-server/README.md`

### New Project Structure:
```
agenthub-server/
├── agenthub_server/
│   ├── __init__.py
│   ├── models.py
│   ├── database.py
│   ├── server.py
│   └── cli.py
├── examples/
│   └── demo.py
├── setup.py
├── requirements.txt
├── README.md
└── MIGRATION.md
```

## Changes Made

### 1. Package Structure
- Created new `agenthub_server` Python package
- Added proper `__init__.py` with clean exports
- Updated all internal imports to use relative imports

### 2. Dependencies
- Separated dependencies: server now has its own `requirements.txt`
- Server includes FastAPI, uvicorn, httpx, click, pydantic, pyyaml
- Optional PostgreSQL support via psycopg2

### 3. CLI Interface
- Changed from `python -m agenthub.hub_cli` to `python -m agenthub_server.cli`
- Added console script: `agenthub-server` command
- All CLI commands work with new structure

### 4. Import Changes
- Core SDK imports: `from agenthub import AgentBuilder`
- Server imports: `from agenthub_server import create_hub_server, serve_hub`
- Database imports: `from agenthub_server.database import init_database`
- Models imports: `from agenthub_server.models import AgentMetadata`

### 5. Removed Dependencies
- Removed `AgentBuilder` dependency from server
- Server now accepts `AgentMetadata` objects instead of `AgentBuilder` instances
- Changed `register_local_agent()` to `register_agent_endpoint()`

## Usage Changes

### Before (Integrated):
```python
from agenthub import AgentBuilder
from agenthub.hub_server import create_hub_server

agent = AgentBuilder("my-agent")
server = create_hub_server()
server.register_local_agent(agent, port=8000)
```

### After (Separated):
```python
from agenthub import AgentBuilder  # Core SDK
from agenthub_server import create_hub_server  # Server project

agent = AgentBuilder("my-agent")
server = create_hub_server()
server.register_agent_endpoint(agent.metadata, "http://localhost:8000")
```

### CLI Changes:
```bash
# Before
python -m agenthub.hub_cli serve --port 8080

# After
python -m agenthub_server.cli serve --port 8080
# OR
agenthub-server serve --port 8080
```

## Installation

The server is now a separate package:

```bash
# Install the server
pip install ./agenthub-server

# Or with development dependencies
pip install "./agenthub-server[dev]"

# Or with PostgreSQL support
pip install "./agenthub-server[postgresql]"
```

## Benefits of Separation

1. **Clear Separation of Concerns**: Core SDK for building agents, separate server for hosting marketplace
2. **Independent Development**: Server can evolve independently from core SDK
3. **Reduced Dependencies**: Core SDK remains lightweight, server has its own dependencies
4. **Deployment Flexibility**: Server can be deployed independently
5. **Better Maintenance**: Each project has focused scope and responsibilities

## Migration for Users

Users who were using the integrated hub server features should:

1. Install the separate `agenthub-server` package
2. Update imports from `agenthub.hub_*` to `agenthub_server.*`
3. Update CLI commands to use `agenthub_server.cli` or `agenthub-server`
4. Update any integration code to use new API (metadata instead of AgentBuilder)

The core `agenthub` package remains unchanged for agent building functionality.