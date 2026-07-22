"""Quick test: multi-source finder + enrichment pipeline"""
import sys
sys.path.insert(0, r"F:\reviewer")
import os, time
os.chdir(r"F:\reviewer")

from dotenv import load_dotenv
load_dotenv()

from local_daemon import run_once

# Run a single cycle
run_once()
