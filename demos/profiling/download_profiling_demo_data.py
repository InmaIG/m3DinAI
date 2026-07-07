# demos/profiling/download_profiling_demo_data.py
"""
m3DinAI - Download the profiling demo dataset (Zenodo).

Fetches the published profiling demo dataset from Zenodo, verifies it, and unzips it into
the demo folder so that `run_profiling_demo.py` can reproduce the morphological profiling
workflow (feature extraction -> labelling -> embedding) on the example data.

Usage:
    python demos/profiling/download_profiling_demo_data.py
"""
import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

# Zenodo record for the profiling demo dataset
# DOI: https://doi.org/10.5281/zenodo.18847934
ZENODO_RECORD_ID = "18847934"

DEMO_DIR = Path(__file__).resolve().parent          # .../m3DinAI/demos/profiling
REPO_ROOT = Path(__file__).resolve().parents[2]     # .../m3DinAI
DEFAULT_DATA_DIR = DEMO_DIR / "demo_data"
DOWNLOADS_DIR = DEMO_DIR / "_downloads"
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
        print(f"Data present under: {expected}")
        return

    # Common case: ZIP has a single top-level folder (e.g., "<something>/72H/R1/...")
    children = [p for p in data_dir.iterdir() if p.is_dir()]
    if len(children) == 1:
        top = children[0]
        if (top / "72H").exists():
            print(f"Fixing layout: lifting contents of {top.name} into {data_dir.name}")
            tmp = data_dir / "__tmp_move__"
            tmp.mkdir(exist_ok=True)

            for item in top.iterdir():
                shutil.move(str(item), str(tmp / item.name))

            try:
                top.rmdir()
            except OSError:
                pass

            for item in tmp.iterdir():
                shutil.move(str(item), str(data_dir / item.name))

            tmp.rmdir()

    if expected.exists():
        print(f"Data present under: {expected}")
        return

    print(f"WARNING: Expected folder not found: {expected}")
    print("Your ZIP may have a different top-level structure.")
    try:
        print(f"Data directory contents: {[p.name for p in data_dir.iterdir()]}")
    except Exception:
        pass


def main():
    # Optional: allow passing a custom data dir as first argument (relative to demos/profiling/)
    data_dir = DEFAULT_DATA_DIR
    if len(sys.argv) >= 2 and sys.argv[1] and not sys.argv[1].startswith("-"):
        data_dir = (DEMO_DIR / sys.argv[1]).resolve()

    print("Starting profiling demo download (Zenodo record: 18847934).")
    print("Dataset size is approximately 5 GB; download time depends on your connection (often several minutes).")
    print(f"Download cache: {DOWNLOADS_DIR}")
    print(f"Extracting to:  {data_dir}\n")

    api_url = f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}"
    print(f"Fetching Zenodo record:\n  {api_url}")
    record = http_get_json(api_url)

    f = pick_zip_file(record)
    filename = f.get("key", f"zenodo_{ZENODO_RECORD_ID}.zip")
    download_url = f.get("links", {}).get("self") or f.get("links", {}).get("download")
    if not download_url:
        raise SystemExit("ERROR: Could not find a download URL in Zenodo response.")

    zip_path = DOWNLOADS_DIR / filename
    download(download_url, zip_path)

    unzip(zip_path, data_dir)
    ensure_expected_layout(data_dir)

    print("\nDone.")
    print(f"Data directory: {data_dir}")

    try:
        print(f"Downloaded ZIP SHA256:\n  {sha256_file(zip_path)}")
    except Exception:
        pass


if __name__ == "__main__":
    main()