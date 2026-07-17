"""
#66 Oracle Cloud VM Setup
Provision 4 ARM VMs on Oracle Cloud Free Tier (always free, 24GB RAM total).
"""

import json
import os
from typing import Dict, List


class OracleSetup:
    """Manages Oracle Cloud Free Tier VM setup."""

    FREE_TIER = {
        "provider": "Oracle Cloud",
        "plan": "Always Free",
        "vms": 4,
        "cpu_per_vm": 4,
        "ram_per_vm_gb": 24,
        "storage_gb": 200,
        "total_ram_gb": 24,
        "total_cpu": 16,
        "cost": 0,
        "os_images": ["Ubuntu 22.04", "Oracle Linux 8", "CentOS 8"],
        "arm_architecture": "Ampere A1",
    }

    VM_CONFIGS = [
        {"name": "findleads-1", "role": "scraper", "city": "dubai", "tasks": ["google_maps", "contact_scraping"]},
        {"name": "findleads-2", "role": "scraper", "city": "riyadh", "tasks": ["google_maps", "contact_scraping"]},
        {"name": "findleads-3", "role": "osint", "city": "all", "tasks": ["whois", "dns", "ssl", "tech_stack"]},
        {"name": "findleads-4", "role": "scheduler", "city": "all", "tasks": ["task_distribution", "health_monitor", "data_merge"]},
    ]

    def get_free_tier_info(self) -> Dict:
        """Get Oracle Cloud Free Tier specifications."""
        return self.FREE_TIER.copy()

    def get_vm_configs(self) -> List[Dict]:
        """Get the 4 VM configuration plans."""
        return self.VM_CONFIGS.copy()

    def generate_setup_script(self) -> str:
        """Generate bash script for setting up a VM."""
        script = """#!/bin/bash
# FindLeads Oracle Cloud VM Setup
set -e

echo "[1/5] Updating system..."
sudo apt update && sudo apt upgrade -y

echo "[2/5] Installing Python 3.12..."
sudo apt install -y python3.12 python3.12-venv python3-pip

echo "[3/5] Installing Playwright + Chromium..."
pip3 install playwright duckdb networkx
playwright install chromium

echo "[4/5] Installing project dependencies..."
pip3 install requests beautifulsoup4 aiohttp imap-tools

echo "[5/5] Setting up FindLeads..."
mkdir -p /opt/findleads
cd /opt/findleads
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "[DONE] VM ready!"
"""
        return script

    def get_ssh_config(self) -> str:
        """Generate SSH config for the 4 VMs."""
        lines = []
        for vm in self.VM_CONFIGS:
            lines.append(f"Host {vm['name']}")
            lines.append(f"  HostName <PUBLIC_IP_{vm['name'].upper()}>")
            lines.append(f"  User ubuntu")
            lines.append(f"  IdentityFile ~/.ssh/oracle_cloud_key")
            lines.append(f"  StrictHostKeyChecking no")
            lines.append("")
        return "\n".join(lines)

    def estimate_monthly_cost(self) -> Dict:
        """Estimate monthly cost — should be $0."""
        return {
            "vm_cost": 0,
            "storage_cost": 0,
            "bandwidth_cost": 0,
            "total": 0,
            "currency": "USD",
            "note": "Always Free tier — no charges ever",
        }

    def get_deployment_checklist(self) -> List[Dict]:
        """Get step-by-step deployment checklist."""
        return [
            {"step": 1, "task": "Create Oracle Cloud account", "time": "10 min", "done": False},
            {"step": 2, "task": "Create SSH key pair", "time": "2 min", "done": False},
            {"step": 3, "task": "Provision 4 ARM VMs (Ampere A1)", "time": "15 min", "done": False},
            {"step": 4, "task": "Open ports 22, 80, 443 in security list", "time": "5 min", "done": False},
            {"step": 5, "task": "SSH into each VM and run setup script", "time": "20 min", "done": False},
            {"step": 6, "task": "Clone FindLeads repo on each VM", "time": "5 min", "done": False},
            {"step": 7, "task": "Configure DuckDB sync between VMs", "time": "10 min", "done": False},
            {"step": 8, "task": "Set up cron jobs for scheduled runs", "time": "5 min", "done": False},
            {"step": 9, "task": "Test: run one scrape on each VM", "time": "10 min", "done": False},
            {"step": 10, "task": "Monitor first 24 hours", "time": "24 hr", "done": False},
        ]


if __name__ == "__main__":
    os_setup = OracleSetup()
    info = os_setup.get_free_tier_info()
    print(f"Free Tier: {info}")
    vms = os_setup.get_vm_configs()
    for vm in vms:
        print(f"  VM: {vm['name']} — Role: {vm['role']} — Tasks: {vm['tasks']}")
    cost = os_setup.estimate_monthly_cost()
    print(f"Monthly cost: ${cost['total']}")
    script = os_setup.generate_setup_script()
    print(f"Setup script: {len(script)} lines")
