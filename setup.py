"""
Setup script for AgentHub Server - Marketplace server for AI agents
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()

# Read version
version = "1.0.0"

setup(
    name="agenthub-server",
    version=version,
    author="AgentHub Team",
    author_email="team@agenthub.ai",
    description="Marketplace server for AI agents with database persistence and task management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/agenthub/agenthub-server",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn[standard]>=0.15.0",
        "httpx>=0.24.0",
        "click>=8.0.0",
        "pydantic>=1.8.0",
        "pyyaml>=5.4.0",
    ],
    extras_require={
        "postgresql": ["psycopg2-binary>=2.9.0"],
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.18.0",
            "black>=21.0.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
        ],
        "full": [
            "psycopg2-binary>=2.9.0",
            "pytest>=6.0.0",
            "pytest-asyncio>=0.18.0",
            "black>=21.0.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
        ],
    },
    entry_points={
        "console_scripts": [
            "agenthub-server=agenthub_server.cli:hub_cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="ai, agents, marketplace, server, fastapi, database",
    project_urls={
        "Bug Reports": "https://github.com/agenthub/agenthub-server/issues",
        "Source": "https://github.com/agenthub/agenthub-server",
        "Documentation": "https://docs.agenthub.ai/server",
    },
)