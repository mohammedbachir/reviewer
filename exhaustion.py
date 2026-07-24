"""
Exhaustion Detection & Smart Rotation for city/sector combos.

Monitors discovery freshness per target combination and automatically
skips exhausted targets, rotating to active ones.
"""
import os, sys, json, time, random, logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple, Set

log = logging.getLogger("exhaustion")

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    import requests as cffi_requests

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

TABLE = "combo_exhaustion_status"


def _sb_get(path, params=""):
    try:
        r = cffi_requests.get(f"{SUPABASE_URL}/rest/v1/{path}?{params}", headers=_HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.debug(f"SB GET failed: {e}")
    return []


def _sb_upsert(data):
    try:
        r = cffi_requests.post(
            f"{SUPABASE_URL}/rest/v1/{TABLE}",
            json=data,
            headers={**_HEADERS, "Prefer": "resolution=merge-duplicates"},
            timeout=15,
        )
        return r.status_code in (200, 201, 204)
    except Exception as e:
        log.debug(f"SB UPSERT failed: {e}")
        return False


def _sb_patch(table, data, filters):
    try:
        r = cffi_requests.patch(
            f"{SUPABASE_URL}/rest/v1/{table}?{filters}",
            json=data,
            headers={**_HEADERS, "Prefer": "return=minimal"},
            timeout=15,
        )
        return r.status_code in (200, 204)
    except Exception as e:
        log.debug(f"SB PATCH failed: {e}")
        return False


# ── Exhaustion Detector ────────────────────────────────────────
class ExhaustionDetector:
    """
    Classifies city/sector combos by freshness.
    
    Reads scan_runs to compute freshness rate, then classifies:
      - insufficient_data: <20 runs, too early to judge
      - temporary: freshness > 30%, will recover
      - deep: freshness 5-30%, needs longer cooldown
      - long_cooldown: freshness < 5%, rarely recovers
    """

    MIN_RUNS_FOR_JUDGMENT = 20
    COOLDOWNS = {
        "insufficient_data": timedelta(hours=6),
        "temporary": timedelta(days=5),
        "deep": timedelta(days=30),
        "long_cooldown": timedelta(days=90),
    }

    def __init__(self, window_runs=10, temp_threshold=0.30, deep_threshold=0.05):
        self.window_runs = window_runs
        self.temp_threshold = temp_threshold
        self.deep_threshold = deep_threshold

    def get_freshness(self, city: str, sector: str) -> Optional[float]:
        runs = _sb_get(
            "scan_runs",
            f"select=businesses_found,status&city=eq.{city}&sector=eq.{sector}&order=id.desc&limit={self.window_runs}"
        )
        if not runs or len(runs) < 3:
            return None

        completed = [r for r in runs if r.get("status") == "completed"]
        if not completed:
            return 0.0

        total_found = sum(r.get("businesses_found", 0) for r in completed)
        avg_per_run = total_found / len(completed)

        if avg_per_run >= 3:
            return 1.0
        elif avg_per_run >= 1:
            return 0.5
        else:
            return max(0.0, total_found / max(len(completed), 1) / 3)

    def classify(self, city: str, sector: str) -> Tuple[str, Optional[timedelta]]:
        total_runs = _sb_get(
            "scan_runs",
            f"select=id&city=eq.{city}&sector=eq.{sector}"
        )
        count = len(total_runs) if total_runs else 0

        if count < self.MIN_RUNS_FOR_JUDGMENT:
            return "insufficient_data", self.COOLDOWNS["insufficient_data"]

        freshness = self.get_freshness(city, sector)
        if freshness is None:
            return "insufficient_data", self.COOLDOWNS["insufficient_data"]

        if freshness > self.temp_threshold:
            return "temporary", self.COOLDOWNS["temporary"]
        elif freshness > self.deep_threshold:
            return "deep", self.COOLDOWNS["deep"]
        else:
            return "long_cooldown", self.COOLDOWNS["long_cooldown"]

    def update_status(self, city: str, sector: str):
        classification, cooldown = self.classify(city, sector)
        freshness = self.get_freshness(city, sector)

        total_runs = _sb_get(
            "scan_runs",
            f"select=id&city=eq.{city}&sector=eq.{sector}"
        )
        count = len(total_runs) if total_runs else 0

        if freshness is None and count < 3:
            status = "active"
        elif classification == "insufficient_data":
            status = "active"
        elif classification == "temporary":
            status = "active"
        elif classification == "deep":
            status = "cooling_down"
        else:
            status = "exhausted"

        now_iso = datetime.now(timezone.utc).isoformat()
        cooldown_seconds = int(cooldown.total_seconds()) if cooldown else 0

        _sb_upsert({
            "city": city,
            "sector": sector,
            "freshness_rate": freshness if freshness is not None else 1.0,
            "total_discovered": count,
            "classification": classification,
            "cooldown_seconds": cooldown_seconds,
            "last_checked_at": now_iso,
            "cooldown_expires_at": (
                datetime.now(timezone.utc) + cooldown
            ).isoformat() if cooldown else None,
            "status": status,
        })

        return classification, status


# ── Smart Rotator ──────────────────────────────────────────────
class SmartRotator:
    """
    Rotates through targets.json, skipping exhausted combos.
    """

    def __init__(self, targets_path: str = None):
        if targets_path is None:
            targets_path = os.path.join(os.path.dirname(__file__), "targets.json")
        with open(targets_path) as f:
            raw = json.load(f)
        self.targets = raw if isinstance(raw, list) else raw.get("targets", [])
        for t in self.targets:
            if "sector" not in t and "category" in t:
                t["sector"] = t["category"]
        self.detector = ExhaustionDetector()

    def get_next(self, current_index: int = -1) -> Tuple[Dict, int]:
        now = datetime.now(timezone.utc)
        n = len(self.targets)

        candidates = []
        for i in range(n):
            idx = (current_index + 1 + i) % n
            target = self.targets[idx]
            city, sector = target["city"], target.get("sector", target.get("category", ""))

            combo_status = _sb_get(
                TABLE,
                f"select=status,cooldown_expires_at&city=eq.{city}&sector=eq.{sector}"
            )

            if not combo_status:
                candidates.append((idx, target, 0))
                continue

            cs = combo_status[0]
            status = cs.get("status", "active")

            if status == "active":
                candidates.append((idx, target, 0))
                continue

            expires = cs.get("cooldown_expires_at")
            if expires:
                try:
                    expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                    if now > expires_dt:
                        candidates.append((idx, target, 0))
                        continue
                except Exception:
                    pass

            continue

        if candidates:
            best = candidates[0]
            return best[1], best[0]

        log.warning("All targets exhausted! Falling back to oldest expired.")
        all_combos = _sb_get(
            TABLE,
            "select=city,sector,cooldown_expires_at&status=eq.exhausted&order=cooldown_expires_at.asc&limit=1"
        )
        if all_combos:
            oldest = all_combos[0]
            for i, t in enumerate(self.targets):
                tc = t.get("sector", t.get("category", ""))
                if t["city"] == oldest["city"] and tc == oldest["sector"]:
                    return t, i

        idx = (current_index + 1) % n
        return self.targets[idx], idx

    def update_after_run(self, city: str, sector: str, businesses_found: int):
        self.detector.update_status(city, sector)

        if businesses_found == 0:
            log.info(f"EXHAUSTED: {city}/{sector} — 0 new businesses found")
        else:
            log.info(f"ACTIVE: {city}/{sector} — {businesses_found} new businesses found")


# ── Create table migration ─────────────────────────────────────
def create_exhaustion_table():
    """Creates the combo_exhaustion_status table in Supabase via SQL."""
    sql = """
    CREATE TABLE IF NOT EXISTS combo_exhaustion_status (
        city TEXT NOT NULL,
        sector TEXT NOT NULL,
        freshness_rate FLOAT DEFAULT 1.0,
        total_discovered INT DEFAULT 0,
        classification TEXT DEFAULT 'insufficient_data',
        cooldown_seconds INT DEFAULT 21600,
        last_checked_at TIMESTAMPTZ,
        cooldown_expires_at TIMESTAMPTZ,
        status TEXT DEFAULT 'active',
        PRIMARY KEY (city, sector)
    );
    """
    try:
        r = cffi_requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            json={"query": sql},
            headers=_HEADERS,
            timeout=15,
        )
        if r.status_code == 200:
            log.info("combo_exhaustion_status table created via RPC")
            return True
    except Exception:
        pass

    try:
        r = cffi_requests.post(
            f"{SUPABASE_URL}/rest/v1/{TABLE}",
            json={
                "city": "__init__",
                "sector": "__init__",
                "freshness_rate": 1.0,
                "total_discovered": 0,
                "classification": "insufficient_data",
                "cooldown_seconds": 21600,
                "status": "active",
            },
            headers={**_HEADERS, "Prefer": "return=minimal"},
            timeout=15,
        )
        if r.status_code in (200, 201):
            log.info("combo_exhaustion_status table created via insert")
            _sb_patch(TABLE, {"city": "DELETE_ME"}, "city=eq.__init__&sector=eq.__init__")
            return True
    except Exception:
        pass

    log.warning("Could not create combo_exhaustion_status — run SQL manually")
    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Creating combo_exhaustion_status table...")
    create_exhaustion_table()
    print("Done.")
