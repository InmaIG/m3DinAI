# demo/download_demo_data.py
import hashlib
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

# =========================
# Zenodo record (published)
# DOI: https://doi.org/10.5281/zenodo.18847934
# =========================
ZENODO_RECORD_ID = "18847934"

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "demo_data"
DOWNLOADS_DIR = REPO_ROOT / "demo" / "_downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def http_get_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))

def download(url: str, dest: Path) -> None:
    print(f"Downloading:\n  {url}\n→ {dest}")
    with urllib.request.urlopen(url) as resp, dest.open("wb") as out:
        total = resp.headers.get("Content-Length")
        total = int(total) if total else None
        downloaded = 0
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded * 100 / total
                sys.stdout.write(f"\r  {pct:6.2f}%")
                sys.stdout.flush()
    print("\nDownload complete.")

def unzip(zip_path: Path, out_dir: Path) -> None:
    print(f"Unzipping:\n  {zip_path}\n→ {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(out_dir)
    print("Unzip complete.")

def pick_zip_file(record: dict) -> dict:
    files = record.get("files", [])
    if not files:
        raise SystemExit("ERROR: No files found in Zenodo record.")
    # Prefer a .zip if present
    zips = [f for f in files if str(f.get("key", "")).lower().endswith(".zip")]
    if len(zips) == 1:
        return zips[0]
    if len(zips) > 1:
        # If multiple zips exist, pick the largest (common)
        zips.sort(key=lambda f: f.get("size", 0), reverse=True)
        return zips[0]
    # Fallback: single file record
    if len(files) == 1:
        return files[0]
    raise SystemExit("ERROR: Multiple files found but none are .zip. Please adjust the picker.")

def main():
    data_dir = DEFAULT_DATA_DIR
    if len(sys.argv) >= 2:
        data_dir = REPO_ROOT / sys.argv[1]

    api_url = f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}"
    record = http_get_json(api_url)

    f = pick_zip_file(record)
    filename = f.get("key", f"zenodo_{ZENODO_RECORD_ID}.zip")
    download_url = f.get("links", {}).get("self") or f.get("links", {}).get("download")

    if not download_url:
        raise SystemExit("ERROR: Could not find a download URL in Zenodo response.")

    zip_path = DOWNLOADS_DIR / filename
    download(download_url, zip_path)

    # Optional integrity check if Zenodo provided a checksum
    checksum = f.get("checksum", "")
    if checksum.startswith("md5:"):
        # Zenodo often provides md5; we won't verify md5 here (sha256 is preferred).
        print("Note: Zenodo checksum is MD5; skipping integrity verification.")
    else:
        # If you want strict checking, set your own SHA256 in the future.
        pass

    unzip(zip_path, data_dir)

    # sanity check
    tp = data_dir / "72H" / "R1"
    if not tp.exists():
        print(f"WARNING: Expected folder not found: {tp}")
        print("Check whether your ZIP has an extra top-level folder.")
    else:
        print(f"✅ Data present under: {tp}")

    print("\nDone.")

if __name__ == "__main__":
    main()