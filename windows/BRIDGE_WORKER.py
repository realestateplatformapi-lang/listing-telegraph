"""Outbound Railway -> Windows GPU bridge for KYIV ESTATE."""
import json
import mimetypes
import time
from pathlib import Path

import requests
import truststore

truststore.inject_into_ssl()

ROOT = Path(__file__).parent
RAILWAY = "https://listing-telegraph-production.up.railway.app"
LOCAL = "http://127.0.0.1:8793"
PACKAGES = ROOT / "data" / "packages"


def token():
    for line in (ROOT / ".env.block3").read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("BLOCK3_API_TOKEN="):
            value = line.split("=", 1)[1].strip()
            if value:
                return value
    raise RuntimeError("BLOCK3_API_TOKEN is not configured")


def process(remote_job, headers):
    bridge_id, payload = remote_job["job_id"], remote_job["payload"]
    try:
        response = requests.post(LOCAL + "/api/v1/jobs", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        local_job = response.json()
        while True:
            status = requests.get(LOCAL + "/api/v1/jobs/" + local_job["job_id"], headers=headers, timeout=30)
            status.raise_for_status()
            local_job = status.json()
            if local_job.get("status") in {"ready", "published"}:
                break
            if local_job.get("status") == "failed":
                raise RuntimeError(str(local_job.get("error") or "Local AI job failed"))
            time.sleep(2)
        photo_root = PACKAGES / str(local_job["internal_id"]) / "photos"
        photos = sorted(path for path in photo_root.iterdir() if path.is_file())
        if not photos:
            raise RuntimeError("Local AI returned no certified photos")
        for index, photo in enumerate(photos, 1):
            suffix = photo.suffix.lower().lstrip(".")
            if suffix not in {"jpg", "jpeg", "png", "webp"}:
                suffix = "jpg"
            with photo.open("rb") as stream:
                uploaded = requests.post(
                    f"{RAILWAY}/api/bridge/jobs/{bridge_id}/photos/{index:02d}.{suffix}",
                    data=stream, headers={**headers, "Content-Type": mimetypes.guess_type(photo.name)[0] or "image/jpeg"}, timeout=180,
                )
            uploaded.raise_for_status()
        done = requests.post(f"{RAILWAY}/api/bridge/jobs/{bridge_id}/complete", json={"count": len(photos)}, headers=headers, timeout=30)
        done.raise_for_status()
    except Exception as exc:
        requests.post(f"{RAILWAY}/api/bridge/jobs/{bridge_id}/fail", json={"error": str(exc)[:1800]}, headers=headers, timeout=30)


def main():
    headers = {"X-Block3-Token": token()}
    while True:
        try:
            response = requests.get(RAILWAY + "/api/bridge/jobs/next", headers=headers, timeout=40)
            response.raise_for_status()
            job = response.json()
            if job.get("job_id"):
                process(job, headers)
            else:
                time.sleep(2)
        except requests.RequestException:
            time.sleep(5)


if __name__ == "__main__":
    main()
