"""
#67 Docker Containerization
Package FindLeads as Docker container for deployment on any platform.
"""

import os
from typing import Dict


class DockerBuilder:
    """Builds Docker configuration for FindLeads."""

    DOCKERFILE = """FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    libffi-dev \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium
RUN playwright install chromium

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FINDLEADS_ENV=production

# Expose port for monitoring (optional)
EXPOSE 8080

# Default command
CMD ["python", "main.py"]
"""

    DOCKER_COMPOSE = """version: "3.8"

services:
  findleads-scraper:
    build: .
    container_name: findleads-scraper
    restart: unless-stopped
    environment:
      - FINDLEADS_ROLE=scraper
      - FINDLEADS_CITY=dubai
    volumes:
      - ./data:/app/data
    networks:
      - findleads-net

  findleads-osint:
    build: .
    container_name: findleads-osint
    restart: unless-stopped
    environment:
      - FINDLEADS_ROLE=osint
    volumes:
      - ./data:/app/data
    networks:
      - findleads-net

  findleads-monitor:
    build: .
    container_name: findleads-monitor
    restart: unless-stopped
    environment:
      - FINDLEADS_ROLE=monitor
    volumes:
      - ./data:/app/data
    networks:
      - findleads-net

networks:
  findleads-net:
    driver: bridge
"""

    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.dirname(__file__)

    def generate_dockerfile(self) -> str:
        """Generate Dockerfile content."""
        return self.DOCKERFILE

    def generate_docker_compose(self) -> str:
        """Generate docker-compose.yml content."""
        return self.DOCKER_COMPOSE

    def get_build_instructions(self) -> Dict:
        """Get build and run commands."""
        return {
            "build": "docker build -t findleads:latest .",
            "run_scraper": "docker run -d --name findleads-scraper -v ./data:/app/data findleads:latest python main.py",
            "run_osint": "docker run -d --name findleads-osint -v ./data:/app/data findleads:latest python main.py",
            "stop": "docker stop findleads-scraper findleads-osint findleads-monitor",
            "logs": "docker logs -f findleads-scraper",
            "compose_up": "docker-compose up -d",
            "compose_down": "docker-compose down",
        }

    def estimate_image_size(self) -> Dict:
        """Estimate Docker image size."""
        return {
            "base_image": "python:3.12-slim (~150 MB)",
            "system_deps": "~50 MB",
            "python_deps": "~200 MB",
            "playwright_chromium": "~400 MB",
            "application": "~50 MB",
            "total_estimated": "~850 MB",
            "with_layer_caching": "~200 MB (on rebuild)",
        }

    def get_env_variables(self) -> Dict:
        """Get environment variables for Docker."""
        return {
            "FINDLEADS_ROLE": "scraper | osint | monitor | scheduler",
            "FINDLEADS_CITY": "dubai | riyadh | all",
            "FINDLEADS_ENV": "production | development",
            "FINDLEADS_DB_PATH": "/app/data/data.duckdb",
            "FINDLEADS_LOG_LEVEL": "INFO | DEBUG | WARNING",
        }


if __name__ == "__main__":
    builder = DockerBuilder("F:\\reviewer")
    print("=== Dockerfile ===")
    print(builder.generate_dockerfile()[:200] + "...")
    print()
    print("=== Build Instructions ===")
    for k, v in builder.get_build_instructions().items():
        print(f"  {k}: {v}")
    print()
    size = builder.estimate_image_size()
    print(f"Estimated image size: {size['total_estimated']}")
