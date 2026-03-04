# demo/download_demo_data.py
import hashlib
import json
import shutil
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
    if dest.exists() and dest.stat().st_size > 0:
        print(f"ZIP already present, skipping download:\n  {dest}")
        return

    print(f"Downloading:\n  {url}\n→ {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)

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

    zips = [f for f in files if str(f.get("key", "")).lower().endswith(".zip")]
    if len(zips) == 1:
        return zips[0]
    if len(zips) > 1:
        zips.sort(key=lambda f: f.get("size", 0), reverse=True)
        return zips[0]

    if len(files) == 1:
        return files[0]

    raise SystemExit("ERROR: Multiple files found but none are .zip. Please adjust the picker.")

def ensure_expected_layout(data_dir: Path) -> None:
    """
    Expect: data_dir/72H/R1/...
    If the ZIP created an extra top-level folder, try to fix it.
    """
    expected = data_dir / "72H" / "R1"
    if expected.exists():
        return

    # Common case: ZIP has a single top-level folder (e.g., "72H/" or "<something>/72H/")
    children = [p for p in data_dir.iterdir() if p.is_dir()]
    if len(children) == 1:
        top = children[0]
        # If top already contains 72H, move its contents up one level
        if (top / "72H").exists():
            tmp = data_dir / "__tmp_move__"
            tmp.mkdir(exist_ok=True)
            for item in top.iterdir():
                shutil.move(str(item), str(tmp / item.name))
            # remove now-empty top folder
            try:
                top.rmdir()
            except OSError:
                pass
            # move tmp contents back to data_dir
            for item in tmp.iterdir():
                shutil.move(str(item), str(data_dir / item.name))
            tmp.rmdir()

    # Re-check
    if not expected.exists():
        print(f"WARNING: Expected folder not found: {expected}")
        print("Your ZIP may have a different top-level structure.")
        print(f"Data directory contents: {[p.name for p in data_dir.iterdir()]}")
    else:
        print(f"✅ Data present under: {expected}")

def main():
    # Optional: allow passing a custom data dir as first argument
    data_dir = DEFAULT_DATA_DIR
    if len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
        data_dir = (REPO_ROOT / sys.argv[1]).resolve()

    api_url = f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}"
    record = http_get_json(api_url)

    f = pick_zip_file(record)
    filename = f.get("key", f"zenodo_{ZENODO_RECORD_ID}.zip")
    download_url = f.get("links", {}).get("self") or f.get("links", {}).get("download")
    if not download_url:
        raise SystemExit("ERROR: Could not find a download URL in Zenodo response.")

    zip_path = DOWNLOADS_DIR / filename
    download(download_url, zip_path)

    # Unzip (overwrite-friendly: we simply extract; existing files will be overwritten by ZipFile)
    unzip(zip_path, data_dir)

    # Layout sanity check (and best-effort fix)
    ensure_expected_layout(data_dir)

    print("\nDone.")
    print(f"Data directory: {data_dir}")

if __name__ == "__main__":
    main()