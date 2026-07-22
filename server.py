"""
Crisora — GhostBot Server v2
Flask web app + background daemon thread + watchdog.
"""

import os
import sys
import threading
import time
import logging
from datetime import datetime, timezone

from flask import Flask, jsonify

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("crisora-server")

app = Flask(__name__)

_daemon = None
_lock = threading.Lock()


@app.route("/")
def index():
    return jsonify({
        "service": "Crisora Engine",
        "version": "2.0",
        "status": "running",
        "features": ["self-healing", "watchdog", "parallel-enrichment", "graph-cache"],
    })


@app.route("/health")
def health():
    daemon = _get_daemon()
    status = daemon.get_status()
    status["ok"] = True
    status["timestamp"] = datetime.now(timezone.utc).isoformat()
    return jsonify(status)


@app.route("/status")
def status():
    return jsonify(_get_daemon().get_status())


@app.route("/diagnostics")
def diagnostics():
    diag = _get_daemon().run_diagnostics()
    return jsonify(diag)


def _get_daemon():
    global _daemon
    if _daemon is None:
        import local_daemon
        _daemon = local_daemon._get_daemon()
    return _daemon


def _daemon_loop():
    """Background thread: runs the daemon continuous loop (zero-sleep)."""
    log.info("Daemon v2 thread starting (zero-sleep mode)...")
    daemon = _get_daemon()

    while True:
        try:
            daemon.run_once()
        except Exception as e:
            log.error(f"Daemon run failed: {e}")

        # Minimal delay — 1 second
        time.sleep(1)


def main():
    port = int(os.environ.get("PORT", 8080))

    daemon_thread = threading.Thread(target=_daemon_loop, daemon=True)
    daemon_thread.start()

    log.info(f"Starting Crisora server v2 on port {port}...")
    app.run(host="0.0.0.0", port=port, threaded=True)


if __name__ == "__main__":
    main()
