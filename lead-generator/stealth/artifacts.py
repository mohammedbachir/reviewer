"""
#57 GitHub Artifacts
Save data.duckdb between runs via GitHub Artifacts.
"""

import os
from typing import Dict


ARTIFACT_CONFIG = """
      - name: Download previous database
        uses: actions/download-artifact@v4
        with:
          name: findleads-data
          path: lead-generator/
        continue-on-error: true

      - name: Upload database after run
        uses: actions/upload-artifact@v4
        with:
          name: findleads-data
          path: lead-generator/data.duckdb
          retention-days: 90
          overwrite: true
"""


class ArtifactManager:
    """Manages GitHub Artifacts for data persistence."""

    def __init__(self, project_root: str):
        self.project_root = project_root

    def get_download_step(self) -> str:
        """Get the YAML step for downloading artifacts."""
        return ARTIFACT_CONFIG.strip()

    def get_artifact_info(self) -> Dict:
        """Get artifact configuration info."""
        return {
            "name": "findleads-data",
            "path": "lead-generator/data.duckdb",
            "retention_days": 90,
            "overwrite": True,
            "description": "DuckDB database persisted between GitHub Actions runs",
        }

    def estimate_size(self, businesses: int = 1000) -> Dict:
        """Estimate artifact size."""
        bytes_per_business = 500
        total_bytes = businesses * bytes_per_business
        return {
            "estimated_bytes": total_bytes,
            "estimated_mb": round(total_bytes / 1024 / 1024, 2),
            "retention_days": 90,
            "within_free_limit": total_bytes < 500 * 1024 * 1024,
        }


if __name__ == "__main__":
    am = ArtifactManager("F:\\reviewer")
    info = am.get_artifact_info()
    print(f"Artifact info: {info}")
    size = am.estimate_size(5000)
    print(f"Estimated size for 5000 businesses: {size}")
