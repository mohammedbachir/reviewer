"""
#56 GitHub Actions Workflow
Generates the YAML workflow file for automated runs.
"""

import os
import yaml
from typing import Dict


WORKFLOW_YAML = """
name: FindLeads Automated Run

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:
    inputs:
      city:
        description: 'City to search'
        required: false
        default: 'Dubai'
      sector:
        description: 'Business sector'
        required: false
        default: 'beauty salons'

permissions:
  contents: write

jobs:
  findleads:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run FindLeads
        env:
          FINDLEADS_CITY: ${{ github.event.inputs.city || 'Dubai' }}
          FINDLEADS_SECTOR: ${{ github.event.inputs.sector || 'beauty salons' }}
        run: |
          python -m lead-generator.main --city "$FINDLEADS_CITY" --sector "$FINDLEADS_SECTOR" --headless

      - name: Upload DuckDB database
        uses: actions/upload-artifact@v4
        with:
          name: findleads-data-${{ github.run_number }}
          path: lead-generator/data.duckdb
          retention-days: 90
"""


class GitHubActionsGenerator:
    """Generates GitHub Actions workflow files."""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.workflows_dir = os.path.join(project_root, ".github", "workflows")

    def generate_workflow(self) -> Dict:
        """Generate the main workflow file."""
        os.makedirs(self.workflows_dir, exist_ok=True)
        filepath = os.path.join(self.workflows_dir, "findleads.yml")

        with open(filepath, "w") as f:
            f.write(WORKFLOW_YAML.strip())

        return {"status": "generated", "filepath": filepath}

    def get_workflow_config(self) -> Dict:
        """Get the workflow configuration details."""
        return {
            "schedule": "Every 6 hours",
            "timeout": "10 minutes",
            "runner": "ubuntu-latest",
            "python": "3.12",
            "artifacts_retention": "90 days",
            "free_tier_usage": "~2000 min/month (GitHub Actions free tier)",
            "ip_rotation": "Microsoft Azure IPs (new IP every 6 hours)",
        }

    def estimate_monthly_usage(self, runs_per_day: int = 4) -> Dict:
        """Estimate monthly GitHub Actions usage."""
        minutes_per_run = 10
        total_minutes = runs_per_day * 30 * minutes_per_run
        return {
            "runs_per_day": runs_per_day,
            "minutes_per_run": minutes_per_run,
            "total_minutes_monthly": total_minutes,
            "free_tier_limit": 2000,
            "remaining": 2000 - total_minutes,
            "cost": "$0 (within free tier)" if total_minutes <= 2000 else f"${(total_minutes - 2000) * 0.008:.2f}",
        }


if __name__ == "__main__":
    gen = GitHubActionsGenerator("F:\\reviewer")
    config = gen.get_workflow_config()
    print(f"Workflow config: {config}")
    usage = gen.estimate_monthly_usage()
    print(f"Monthly usage: {usage}")
