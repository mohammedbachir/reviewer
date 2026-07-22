"""
Batch OSINT Runner v2 — Parallel tools, safe PATCH.
Only updates firebase/archive/api_keys/crtsh/sherlock. Never touches other data.
"""
import os
import sys
import json
import time
import logging
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
load_dotenv()

try:
    import dns.resolver
    _resolver = dns.resolver.Resolver()
    _resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
    dns.resolver.default_resolver = _resolver
except Exception:
    pass

from curl_cffi import requests as cffi_requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("batch_osint")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SB_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

from scraper.osint_engine import (
    check_firebase_exposure,
    check_archive_wraith,
    extract_api_keys,
    check_subdomains_emails,
    sherlock_lite,
    _extract_username_from_email,
)

DELAY_BETWEEN_BATCHES = 1.5
BIZ_WORKERS = 3


def _sb_get(table, params):
    resp = cffi_requests.get(f"{SUPABASE_URL}/rest/v1/{table}?{params}", headers=SB_HEADERS, timeout=15)
    return resp.json()


def _sb_patch(table, row_id, data):
    resp = cffi_requests.patch(
        f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{row_id}",
        json=data, headers=SB_HEADERS, timeout=10,
    )
    return resp.status_code


def _extract_domain(website):
    if not website:
        return ""
    try:
        parsed = urlparse(website if "://" in website else f"https://{website}")
        domain = parsed.netloc or parsed.path
        return domain.replace("www.", "").strip("/")
    except Exception:
        return ""


def _fetch_html(domain):
    try:
        s = cffi_requests.Session(impersonate="chrome120")
        resp = s.get(f"https://{domain}", timeout=5, allow_redirects=True)
        return resp.text
    except Exception:
        return ""


def _run_one_tool(tool_fn, *args, **kwargs):
    try:
        return tool_fn(*args, **kwargs)
    except Exception:
        return {}


def run_osint_on_business(biz):
    """Run 5 OSINT tools in parallel on one business."""
    website = biz.get("website", "")
    domain = _extract_domain(website)
    if not domain:
        return None

    biz_id = biz["id"]
    name = biz.get("name", "?")

    html = _fetch_html(domain)

    tools = [
        ("firebase", lambda: check_firebase_exposure(domain, html)),
        ("archive", lambda: check_archive_wraith(domain)),
        ("api_keys", lambda: extract_api_keys(html, domain)),
    ]

    results = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(fn): key for key, fn in tools}
        for f in as_completed(futures):
            results[futures[f]] = f.result()

    crt_data = _run_one_tool(check_subdomains_emails, domain)
    results["crtsh"] = crt_data

    emails = crt_data.get("emails_found", []) if isinstance(crt_data, dict) else []
    username = _extract_username_from_email(emails[0]) if emails else domain.split(".")[0]
    results["sherlock"] = _run_one_tool(sherlock_lite, email=emails[0] if emails else "", username=username)

    return {
        "id": biz_id,
        "name": name,
        "firebase": results.get("firebase", {}),
        "archive": results.get("archive", {}),
        "api_keys": results.get("api_keys", {}),
        "crtsh": results.get("crtsh", {}),
        "sherlock": results.get("sherlock", {}),
    }


def main():
    logger.info("=" * 60)
    logger.info("BATCH OSINT v2 — Parallel tools, safe PATCH")
    logger.info("=" * 60)

    all_bizs = []
    offset = 0
    while True:
        data = _sb_get("businesses", f"select=id,name,website,firebase&offset={offset}&limit=1000")
        if not data:
            break
        for b in data:
            if b.get("website"):
                fb = b.get("firebase")
                if not fb or fb == {} or fb == "{}" or fb == "":
                    all_bizs.append(b)
        if len(data) < 1000:
            break
        offset += 1000

    total_to_process = len(all_bizs)
    logger.info(f"To process: {total_to_process} businesses")
    logger.info(f"Workers: {BIZ_WORKERS}")
    logger.info("")

    total_done = 0
    total_ok = 0
    total_err = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=BIZ_WORKERS) as ex:
        futures = {ex.submit(run_osint_on_business, b): b for b in all_bizs}

        for future in as_completed(futures):
            biz = futures[future]
            total_done += 1

            try:
                res = future.result()
                if not res:
                    total_err += 1
                    continue

                patch_data = {
                    "firebase": res["firebase"],
                    "archive": res["archive"],
                    "api_keys": res["api_keys"],
                    "crtsh": res["crtsh"],
                    "sherlock": res["sherlock"],
                }

                status = _sb_patch("businesses", res["id"], patch_data)
                if status in (200, 204):
                    total_ok += 1
                    fb_r = res["firebase"].get("firebase_risk", "N") if isinstance(res["firebase"], dict) else "N"
                    ak_n = len(res["api_keys"].get("api_keys_found", [])) if isinstance(res["api_keys"], dict) else 0
                    cr_n = res["crtsh"].get("subdomain_count", 0) if isinstance(res["crtsh"], dict) else 0
                    sh_n = res["sherlock"].get("profile_count", 0) if isinstance(res["sherlock"], dict) else 0
                    logger.info(
                        f"  [{total_done}/{total_to_process}] OK {res['name'][:30]:30s} | "
                        f"FB:{fb_r} API:{ak_n} CRT:{cr_n} SH:{sh_n}"
                    )
                else:
                    total_err += 1
                    logger.error(f"  [{total_done}/{total_to_process}] FAIL id={res['id']} status={status}")

            except Exception as e:
                total_err += 1
                logger.error(f"  [{total_done}/{total_to_process}] ERROR {biz.get('name','?')}: {e}")

            if total_done % 25 == 0:
                elapsed = time.time() - start
                rate = total_done / elapsed if elapsed > 0 else 1
                eta = (total_to_process - total_done) / rate
                pct = total_done * 100 // total_to_process
                logger.info(f"  --- {pct}% done | OK:{total_ok} ERR:{total_err} | ETA:{int(eta//60)}m{int(eta%60)}s ---")

    elapsed = time.time() - start
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"DONE in {int(elapsed//60)}m {int(elapsed%60)}s")
    logger.info(f"Total: {total_to_process} | OK: {total_ok} | Errors: {total_err}")
    logger.info("=" * 60)


if __name__ == "__main__":
    while True:
        try:
            main()
            break
        except Exception as e:
            logger.error(f"FATAL: {e}")
            logger.info("Retrying in 60 seconds (DNS/network issue)...")
            time.sleep(60)
