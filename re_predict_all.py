"""
Re-predict crisis for ALL businesses with OSINT-aware model (FAST version).
Single model instance, batch PATCH, no graph (O(N) instead of O(N²)).
"""
import os
import sys
import json
import time
import logging
from dotenv import load_dotenv
from curl_cffi import requests as cffi_requests

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper.crisis_predictor import (
    CrisisModel, extract_features, calculate_cvss_risk_score,
    generate_recommendations, _enforce_crisis_floors
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    stream=sys.stdout, encoding="utf-8", errors="replace")
log = logging.getLogger("re-predict")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}


def fetch_all():
    all_biz = []
    offset = 0
    while True:
        r = cffi_requests.get(
            f"{SUPABASE_URL}/rest/v1/businesses?select=*&order=id.asc&limit=500&offset={offset}",
            headers=HEADERS, timeout=30
        )
        batch = r.json()
        if not batch:
            break
        all_biz.extend(batch)
        log.info(f"Fetched {len(batch)} (offset {offset}, total {len(all_biz)})")
        if len(batch) < 500:
            break
        offset += 500
    return all_biz


def patch_batch(patches):
    """Batch PATCH up to 50 businesses at once."""
    if not patches:
        return
    for p in patches:
        try:
            cffi_requests.patch(
                f"{SUPABASE_URL}/rest/v1/businesses?id=eq.{p['id']}",
                json=p["data"], headers=HEADERS, timeout=10
            )
        except Exception as e:
            log.error(f"PATCH failed for {p['id']}: {e}")


def main():
    log.info("Fetching all businesses...")
    businesses = fetch_all()
    log.info(f"Total: {len(businesses)}")

    model = CrisisModel()
    updated = 0
    errors = 0
    pending_patches = []

    for i, biz in enumerate(businesses):
        biz_id = biz.get("id")
        name = (biz.get("name") or "")[:35]

        try:
            features = extract_features(biz)
            hybrid_result = model.predict(features)
            prob = _enforce_crisis_floors(biz, hybrid_result["crisis_probability"])
            risk_level = CrisisModel._prob_to_level(prob)
            cvss = calculate_cvss_risk_score(biz.get("vulnerabilities", []))
            recs = generate_recommendations(features, {"crisis_probability": prob, "risk_level": risk_level}, cvss, [])

            patch = {
                "crisis_probability": round(prob, 4),
                "crisis_risk_level": risk_level,
                "cvss_severity": cvss["severity"],
                "cvss_max": cvss["cvss_max"],
                "crisis_recommendations": json.dumps(recs),
            }

            pending_patches.append({"id": biz_id, "data": patch})

            if len(pending_patches) >= 50:
                patch_batch(pending_patches)
                pending_patches = []

            prob_pct = prob * 100
            if (i + 1) % 100 == 0 or prob_pct >= 50:
                log.info(f"[{i+1}/{len(businesses)}] {name:<35} | {prob_pct:5.1f}% {risk_level}")
            updated += 1

        except Exception as e:
            log.error(f"[{i+1}] {name}: {e}")
            errors += 1

    if pending_patches:
        patch_batch(pending_patches)

    log.info(f"\n{'='*60}")
    log.info(f"DONE: {updated} updated, {errors} errors")
    log.info(f"{'='*60}")


if __name__ == "__main__":
    main()
