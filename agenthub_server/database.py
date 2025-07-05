"""
Database layer for AgentHub server with SQLite/PostgreSQL support
"""

import sqlite3
import json
import time
import uuid
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from pathlib import Path
import logging

try:
    import psycopg2
    import psycopg2.extras
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

from models import AgentMetadata, TaskRequest, TaskResponse, AgentStatus

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager for AgentHub with support for SQLite and PostgreSQL
    """
    
    def __init__(self, database_url: str = "sqlite:///agenthub.db"):
        """
        Initialize database manager
        
        Args:
            database_url: Database connection string
                          - SQLite: "sqlite:///path/to/db.db"
                          - PostgreSQL: "postgresql://user:pass@host:port/dbname"
        """
        self.database_url = database_url
        self.db_type = "sqlite" if database_url.startswith("sqlite") else "postgresql"
        
        if self.db_type == "postgresql" and not POSTGRESQL_AVAILABLE:
            raise ImportError("psycopg2 required for PostgreSQL support")
        
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        if self.db_type == "sqlite":
            db_path = self.database_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn
        else:
            # PostgreSQL
            url_parts = self.database_url.replace("postgresql://", "").split("/")
            auth_host = url_parts[0]
            database = url_parts[1] if len(url_parts) > 1 else "agenthub"
            
            if "@" in auth_host:
                auth, host_port = auth_host.split("@")
                user, password = auth.split(":")
            else:
                host_port = auth_host
                user, password = "postgres", ""
            
            if ":" in host_port:
                host, port = host_port.split(":")
                port = int(port)
            else:
                host, port = host_port, 5432
            
            return psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                cursor_factory=psycopg2.extras.DictCursor
            )
    
    def init_database(self):
        """Initialize database tables"""
        if self.db_type == "sqlite":
            self._init_sqlite()
        else:
            self._init_postgresql()
    
    def _init_sqlite(self):
        """Initialize SQLite database"""
        with self.get_connection() as conn:
            # Agents table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    version TEXT,
                    author TEXT,
                    metadata JSON,
                    endpoint_url TEXT,
                    status TEXT DEFAULT 'active',
                    reliability_score REAL DEFAULT 100.0,
                    total_tasks INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 1.0,
                    average_response_time REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    parameters JSON,
                    result JSON,
                    status TEXT DEFAULT 'pending',
                    error TEXT,
                    execution_time REAL,
                    cost REAL,
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (agent_id) REFERENCES agents (id)
                )
            """)
            
            # Users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    api_key TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    name TEXT,
                    credits REAL DEFAULT 100.0,
                    total_spent REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Agent capabilities table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_capabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    parameters JSON,
                    FOREIGN KEY (agent_id) REFERENCES agents (id)
                )
            """)
            
            # Agent endpoints table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_endpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    method TEXT DEFAULT 'POST',
                    description TEXT,
                    parameters JSON,
                    response_schema JSON,
                    FOREIGN KEY (agent_id) REFERENCES agents (id)
                )
            """)
            
            # Analytics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (agent_id) REFERENCES agents (id)
                )
            """)
            
            conn.commit()
    
    def _init_postgresql(self):
        """Initialize PostgreSQL database"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Agents table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS agents (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        category TEXT,
                        version TEXT,
                        author TEXT,
                        metadata JSONB,
                        endpoint_url TEXT,
                        status TEXT DEFAULT 'active',
                        reliability_score REAL DEFAULT 100.0,
                        total_tasks INTEGER DEFAULT 0,
                        success_rate REAL DEFAULT 1.0,
                        average_response_time REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tasks table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        endpoint TEXT NOT NULL,
                        parameters JSONB,
                        result JSONB,
                        status TEXT DEFAULT 'pending',
                        error TEXT,
                        execution_time REAL,
                        cost REAL,
                        user_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        FOREIGN KEY (agent_id) REFERENCES agents (id)
                    )
                """)
                
                # Users table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        api_key TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE,
                        name TEXT,
                        credits REAL DEFAULT 100.0,
                        total_spent REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Agent capabilities table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS agent_capabilities (
                        id SERIAL PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        parameters JSONB,
                        FOREIGN KEY (agent_id) REFERENCES agents (id)
                    )
                """)
                
                # Agent endpoints table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS agent_endpoints (
                        id SERIAL PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        path TEXT NOT NULL,
                        method TEXT DEFAULT 'POST',
                        description TEXT,
                        parameters JSONB,
                        response_schema JSONB,
                        FOREIGN KEY (agent_id) REFERENCES agents (id)
                    )
                """)
                
                # Analytics table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS analytics (
                        id SERIAL PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (agent_id) REFERENCES agents (id)
                    )
                """)
                
                conn.commit()
    
    def register_agent(self, agent_metadata: AgentMetadata, endpoint_url: str = None) -> str:
        """
        Register a new agent in the database
        
        Args:
            agent_metadata: Agent metadata
            endpoint_url: Agent endpoint URL
            
        Returns:
            Agent ID
        """
        agent_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            if self.db_type == "sqlite":
                conn.execute("""
                    INSERT INTO agents (
                        id, name, description, category, version, author,
                        metadata, endpoint_url, created_at, updated_at, last_seen
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent_id,
                    agent_metadata.name,
                    agent_metadata.description,
                    agent_metadata.category,
                    agent_metadata.version,
                    agent_metadata.author,
                    json.dumps(agent_metadata.dict()),
                    endpoint_url,
                    datetime.now(),
                    datetime.now(),
                    datetime.now()
                ))
            else:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO agents (
                            id, name, description, category, version, author,
                            metadata, endpoint_url
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        agent_id,
                        agent_metadata.name,
                        agent_metadata.description,
                        agent_metadata.category,
                        agent_metadata.version,
                        agent_metadata.author,
                        json.dumps(agent_metadata.dict()),
                        endpoint_url
                    ))
            
            # Register capabilities
            for capability in agent_metadata.capabilities:
                self._register_capability(conn, agent_id, capability)
            
            # Register endpoints
            for endpoint in agent_metadata.endpoints:
                self._register_endpoint(conn, agent_id, endpoint)
            
            conn.commit()
        
        logger.info(f"Registered agent {agent_id}: {agent_metadata.name}")
        return agent_id
    
    def _register_capability(self, conn, agent_id: str, capability):
        """Register agent capability"""
        if self.db_type == "sqlite":
            conn.execute("""
                INSERT INTO agent_capabilities (agent_id, name, description, parameters)
                VALUES (?, ?, ?, ?)
            """, (
                agent_id,
                capability.name,
                capability.description,
                json.dumps(capability.parameters)
            ))
        else:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO agent_capabilities (agent_id, name, description, parameters)
                    VALUES (%s, %s, %s, %s)
                """, (
                    agent_id,
                    capability.name,
                    capability.description,
                    json.dumps(capability.parameters)
                ))
    
    def _register_endpoint(self, conn, agent_id: str, endpoint):
        """Register agent endpoint"""
        if self.db_type == "sqlite":
            conn.execute("""
                INSERT INTO agent_endpoints (agent_id, path, method, description, parameters, response_schema)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                agent_id,
                endpoint.path,
                endpoint.method,
                endpoint.description,
                json.dumps(endpoint.parameters),
                json.dumps(endpoint.response_schema) if endpoint.response_schema else None
            ))
        else:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO agent_endpoints (agent_id, path, method, description, parameters, response_schema)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    agent_id,
                    endpoint.path,
                    endpoint.method,
                    endpoint.description,
                    json.dumps(endpoint.parameters),
                    json.dumps(endpoint.response_schema) if endpoint.response_schema else None
                ))
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent by ID"""
        with self.get_connection() as conn:
            if self.db_type == "sqlite":
                result = conn.execute(
                    "SELECT * FROM agents WHERE id = ?", (agent_id,)
                ).fetchone()
            else:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM agents WHERE id = %s", (agent_id,))
                    result = cur.fetchone()
            
            if result:
                agent_dict = dict(result)
                agent_dict['metadata'] = json.loads(agent_dict['metadata']) if agent_dict['metadata'] else {}
                return agent_dict
            return None
    
    def search_agents(
        self, 
        category: Optional[str] = None,
        name_pattern: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search agents with filters"""
        query = "SELECT * FROM agents WHERE status = 'active'"
        params = []
        
        if category:
            query += f" AND category = {'?' if self.db_type == 'sqlite' else '%s'}"
            params.append(category)
        
        if name_pattern:
            query += f" AND name LIKE {'?' if self.db_type == 'sqlite' else '%s'}"
            params.append(f"%{name_pattern}%")
        
        query += f" ORDER BY reliability_score DESC LIMIT {'?' if self.db_type == 'sqlite' else '%s'} OFFSET {'?' if self.db_type == 'sqlite' else '%s'}"
        params.extend([limit, offset])
        
        with self.get_connection() as conn:
            if self.db_type == "sqlite":
                results = conn.execute(query, params).fetchall()
            else:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    results = cur.fetchall()
            
            agents = []
            for result in results:
                agent_dict = dict(result)
                agent_dict['metadata'] = json.loads(agent_dict['metadata']) if agent_dict['metadata'] else {}
                agents.append(agent_dict)
            
            return agents
    
    def create_task(
        self, 
        agent_id: str, 
        endpoint: str, 
        parameters: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            if self.db_type == "sqlite":
                conn.execute("""
                    INSERT INTO tasks (id, agent_id, endpoint, parameters, user_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    task_id,
                    agent_id,
                    endpoint,
                    json.dumps(parameters),
                    user_id,
                    datetime.now()
                ))
            else:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO tasks (id, agent_id, endpoint, parameters, user_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        task_id,
                        agent_id,
                        endpoint,
                        json.dumps(parameters),
                        user_id
                    ))
            
            conn.commit()
        
        return task_id
    
    def update_task(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        execution_time: Optional[float] = None,
        cost: Optional[float] = None
    ):
        """Update task with results"""
        with self.get_connection() as conn:
            if self.db_type == "sqlite":
                conn.execute("""
                    UPDATE tasks SET 
                        status = ?, result = ?, error = ?, 
                        execution_time = ?, cost = ?, completed_at = ?
                    WHERE id = ?
                """, (
                    status,
                    json.dumps(result) if result else None,
                    error,
                    execution_time,
                    cost,
                    datetime.now() if status in ['completed', 'failed'] else None,
                    task_id
                ))
            else:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE tasks SET 
                            status = %s, result = %s, error = %s, 
                            execution_time = %s, cost = %s, 
                            completed_at = CASE WHEN %s IN ('completed', 'failed') THEN CURRENT_TIMESTAMP ELSE completed_at END
                        WHERE id = %s
                    """, (
                        status,
                        json.dumps(result) if result else None,
                        error,
                        execution_time,
                        cost,
                        status,
                        task_id
                    ))
            
            conn.commit()
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        with self.get_connection() as conn:
            if self.db_type == "sqlite":
                result = conn.execute(
                    "SELECT * FROM tasks WHERE id = ?", (task_id,)
                ).fetchone()
            else:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
                    result = cur.fetchone()
            
            if result:
                task_dict = dict(result)
                task_dict['parameters'] = json.loads(task_dict['parameters']) if task_dict['parameters'] else {}
                task_dict['result'] = json.loads(task_dict['result']) if task_dict['result'] else None
                return task_dict
            return None
    
    def create_user(self, api_key: str, email: str = None, name: str = None) -> str:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            if self.db_type == "sqlite":
                conn.execute("""
                    INSERT INTO users (id, api_key, email, name, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, api_key, email, name, datetime.now(), datetime.now()))
            else:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO users (id, api_key, email, name)
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, api_key, email, name))
            
            conn.commit()
        
        return user_id
    
    def get_user_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get user by API key"""
        with self.get_connection() as conn:
            if self.db_type == "sqlite":
                result = conn.execute(
                    "SELECT * FROM users WHERE api_key = ?", (api_key,)
                ).fetchone()
            else:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE api_key = %s", (api_key,))
                    result = cur.fetchone()
            
            return dict(result) if result else None
    
    def update_agent_stats(self, agent_id: str, success: bool, execution_time: float):
        """Update agent statistics"""
        with self.get_connection() as conn:
            if self.db_type == "sqlite":
                # Get current stats
                result = conn.execute("""
                    SELECT total_tasks, success_rate, average_response_time
                    FROM agents WHERE id = ?
                """, (agent_id,)).fetchone()
                
                if result:
                    total_tasks, success_rate, avg_response_time = result
                    
                    # Calculate new stats
                    new_total = total_tasks + 1
                    new_success_rate = ((success_rate * total_tasks) + (1 if success else 0)) / new_total
                    new_avg_response = ((avg_response_time * total_tasks) + execution_time) / new_total
                    
                    # Update
                    conn.execute("""
                        UPDATE agents SET 
                            total_tasks = ?, success_rate = ?, 
                            average_response_time = ?, last_seen = ?
                        WHERE id = ?
                    """, (new_total, new_success_rate, new_avg_response, datetime.now(), agent_id))
            else:
                with conn.cursor() as cur:
                    # PostgreSQL can do this more efficiently with a single query
                    cur.execute("""
                        UPDATE agents SET 
                            total_tasks = total_tasks + 1,
                            success_rate = (success_rate * total_tasks + %s) / (total_tasks + 1),
                            average_response_time = (average_response_time * total_tasks + %s) / (total_tasks + 1),
                            last_seen = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (1 if success else 0, execution_time, agent_id))
            
            conn.commit()
    
    def get_agent_analytics(self, agent_id: str, days: int = 30) -> Dict[str, Any]:
        """Get agent analytics for the last N days"""
        start_date = datetime.now() - timedelta(days=days)
        
        with self.get_connection() as conn:
            if self.db_type == "sqlite":
                # Task stats
                task_stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_tasks,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                        AVG(execution_time) as avg_execution_time,
                        SUM(cost) as total_cost
                    FROM tasks 
                    WHERE agent_id = ? AND created_at >= ?
                """, (agent_id, start_date)).fetchone()
                
                # Daily stats
                daily_stats = conn.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as tasks,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                    FROM tasks 
                    WHERE agent_id = ? AND created_at >= ?
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """, (agent_id, start_date)).fetchall()
            else:
                with conn.cursor() as cur:
                    # Task stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_tasks,
                            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                            AVG(execution_time) as avg_execution_time,
                            SUM(cost) as total_cost
                        FROM tasks 
                        WHERE agent_id = %s AND created_at >= %s
                    """, (agent_id, start_date))
                    task_stats = cur.fetchone()
                    
                    # Daily stats
                    cur.execute("""
                        SELECT 
                            DATE(created_at) as date,
                            COUNT(*) as tasks,
                            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                        FROM tasks 
                        WHERE agent_id = %s AND created_at >= %s
                        GROUP BY DATE(created_at)
                        ORDER BY date
                    """, (agent_id, start_date))
                    daily_stats = cur.fetchall()
        
        return {
            "agent_id": agent_id,
            "period_days": days,
            "total_tasks": task_stats[0] or 0,
            "completed_tasks": task_stats[1] or 0,
            "success_rate": (task_stats[1] or 0) / max(task_stats[0] or 1, 1),
            "average_execution_time": task_stats[2] or 0.0,
            "total_revenue": task_stats[3] or 0.0,
            "daily_stats": [dict(row) for row in daily_stats]
        }


# Global database instance
_db_manager: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get the global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database(database_url: str = "sqlite:///agenthub.db"):
    """Initialize the global database manager"""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    return _db_manager