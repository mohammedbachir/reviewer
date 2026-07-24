"""
Upload files to Google Cloud VM via SSH in very small chunks.
Uses 4KB chunks to stay within Windows command line limits.
"""
import subprocess
import base64
import os
import math

GLOUD = r"C:\Users\mc\AppData\Local\Google Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
VM_ZONE = "us-west1-a"
VM_NAME = "crisora"

FILES_TO_UPLOAD = [
    (r"F:\reviewer\app.py", "/home/mc/crisora/app.py"),
    (r"F:\reviewer\server.py", "/home/mc/crisora/server.py"),
    (r"F:\reviewer\local_daemon.py", "/home/mc/crisora/local_daemon.py"),
    (r"F:\reviewer\dashboard_api.py", "/home/mc/crisora/dashboard_api.py"),
    (r"F:\reviewer\exhaustion.py", "/home/mc/crisora/exhaustion.py"),
    (r"F:\reviewer\scraper\finder.py", "/home/mc/crisora/scraper/finder.py"),
    (r"F:\reviewer\scraper\osint_engine.py", "/home/mc/crisora/scraper/osint_engine.py"),
    (r"F:\reviewer\scraper\review_engine.py", "/home/mc/crisora/scraper/review_engine.py"),
    (r"F:\reviewer\scraper\crisis_predictor.py", "/home/mc/crisora/scraper/crisis_predictor.py"),
    (r"F:\reviewer\scraper\sources\__init__.py", "/home/mc/crisora/scraper/sources/__init__.py"),
    (r"F:\reviewer\scraper\sources\google_places.py", "/home/mc/crisora/scraper/sources/google_places.py"),
    (r"F:\reviewer\scraper\sources\census_api.py", "/home/mc/crisora/scraper/sources/census_api.py"),
    (r"F:\reviewer\scraper\sources\state_sos.py", "/home/mc/crisora/scraper/sources/state_sos.py"),
    (r"F:\reviewer\scraper\sources\social_discovery.py", "/home/mc/crisora/scraper/sources/social_discovery.py"),
    (r"F:\reviewer\scraper\sources\bbb_api.py", "/home/mc/crisora/scraper/sources/bbb_api.py"),
    (r"F:\reviewer\requirements.txt", "/home/mc/crisora/requirements.txt"),
]


def ssh_cmd(command):
    result = subprocess.run(
        [GLOUD, "compute", "ssh", VM_NAME, "--zone=" + VM_ZONE, "--command=" + command],
        capture_output=True, timeout=90,
    )
    stdout = result.stdout.decode("utf-8", errors="replace").strip()
    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    return result.returncode == 0, stdout, stderr


def upload_file(local_path, remote_path):
    print(f"  Uploading: {os.path.basename(local_path)}")
    with open(local_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    total_chunks = math.ceil(len(b64) / 4000)
    print(f"    File: {len(content)} bytes -> {len(b64)} b64 chars -> {total_chunks} chunks")
    
    # Clear file on VM
    ok, _, err = ssh_cmd("rm -f /tmp/upload_b64.txt")
    if not ok:
        print(f"    FAIL init: {err}")
        return False
    
    # Send in 4KB chunks
    for i in range(total_chunks):
        chunk = b64[i*4000:(i+1)*4000]
        ok, _, err = ssh_cmd(f"printf '%s' '{chunk}' >> /tmp/upload_b64.txt")
        if not ok:
            print(f"    FAIL chunk {i+1}/{total_chunks}: {err[:100]}")
            return False
        if (i+1) % 5 == 0 or i == total_chunks - 1:
            print(f"    Chunk {i+1}/{total_chunks} done")
    
    # Decode and write
    ok, out, err = ssh_cmd(f"base64 -d /tmp/upload_b64.txt > {remote_path} && rm -f /tmp/upload_b64.txt && wc -c {remote_path}")
    if not ok:
        print(f"    FAIL decode: {err[:100]}")
        return False
    
    print(f"    OK! ({len(content)} bytes)")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("  Deploying to Google Cloud VM")
    print("=" * 60)
    
    success = 0
    for local, remote in FILES_TO_UPLOAD:
        if upload_file(local, remote):
            success += 1
    
    print(f"\n  Uploaded: {success}/{len(FILES_TO_UPLOAD)} files")
    
    if success == len(FILES_TO_UPLOAD):
        print("\n  Restarting service...")
        ok, out, err = ssh_cmd("sudo systemctl restart crisora && sleep 3 && sudo systemctl status crisora --no-pager -l")
        print(out)
        if not ok:
            print(f"  Error: {err}")
    else:
        print("\n  FAILED")
