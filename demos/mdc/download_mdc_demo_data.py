# demos/mdc/download_mdc_demo_data.py
"""
m3DinAI - Download the MDC demo dataset (Zenodo).

Fetches the published MDC demo dataset from Zenodo, verifies the download, and unzips it
into the demo folder so that `run_mdc_demo.py` can process it end to end. Use this to
reproduce the MDC (dose-response -> Morphological Disruption Concentration) workflow on the
example data without needing the original acquisition.

Usage:
    python demos/mdc/download_mdc_demo_data.py
"""
import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

# =========================
# Zenodo record (published)
# DOI: https://doi.org/10.5281/zenodo.18876611
# =========================
ZENODO_RECORD_ID = "18876611"


REPO_ROOT = Path(__file__).resolve().parents[2]  # .../m3DinAI
DEFAULT_CFG = REPO_ROOT / "demos" / "mdc" / "config_mdc_demo.yaml"
DOWNLOADS_DIR = REPO_ROOT / "demos" / "mdc" / "_downloads"
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
        # pick the largest zip (most common case)
        zips.sort(key=lambda f: f.get("size", 0), reverse=True)
        return zips[0]

    # fallback: if there is only one file, accept it (even if not .zip)
    if len(files) == 1:
        return files[0]

    raise SystemExit("ERROR: Multiple files found but none are .zip. Please adjust the picker.")


def _is_probable_experiment_folder(p: Path) -> bool:
    # "Experiment folder" = contains plate_map.csv and Images/ (or projections dirs)
    if not p.is_dir():
        return False
    if (p / "plate_map.csv").exists():
        if (p / "Images").exists():
            return True
        if (p / "1. projections").exists() or (p / "2. projections_8bit").exists():
            return True
    return False


def ensure_expected_layout(data_dir: Path, experiment_dir: str) -> Path:
    """
    Target layout:
      data_dir/<experiment_dir>/
        - plate_map.csv
        - Images/
        - 1. projections/ (optional)
        - 2. projections_8bit/ (optional)

    Fix common ZIP layouts:
    - ZIP extracts as data_dir/<experiment_dir>/...  (OK)
    - ZIP extracts with a single extra top-level folder (move contents up)
    - ZIP extracts "Images/" + "plate_map.csv" directly under data_dir (wrap into <experiment_dir>/)
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / experiment_dir

    # Case 1: already correct
    if _is_probable_experiment_folder(target):
        return target

    # Case 2: ZIP produced a single top-level folder
    children = [p for p in data_dir.iterdir() if p.is_dir()]
    if len(children) == 1 and not _is_probable_experiment_folder(target):
        # if that child is already the experiment folder, just rename/move
        only = children[0]
        if _is_probable_experiment_folder(only):
            if target.exists():
                # avoid clobbering
                raise SystemExit(f"ERROR: Target experiment_dir already exists: {target}")
            print(f"Fixing layout: moving {only.name} → {experiment_dir}")
            only.rename(target)
            return target

        # if the child contains the experiment folder inside it, lift it up
        nested = only / experiment_dir
        if _is_probable_experiment_folder(nested):
            if target.exists():
                raise SystemExit(f"ERROR: Target experiment_dir already exists: {target}")
            print(f"Fixing layout: moving {nested} → {target}")
            shutil.move(str(nested), str(target))
            # cleanup empty parent folder if possible
            try:
                if not any(only.iterdir()):
                    only.rmdir()
            except Exception:
                pass
            return target

    # Case 3: extracted directly as data_dir/Images + data_dir/plate_map.csv
    images = data_dir / "Images"
    plate_map = data_dir / "plate_map.csv"
    if plate_map.exists() and images.exists():
        target.mkdir(parents=True, exist_ok=True)
        print(f"Fixing layout: wrapping Images/ and plate_map.csv into {target}")
        shutil.move(str(images), str(target / "Images"))
        shutil.move(str(plate_map), str(target / "plate_map.csv"))

        # also move projections dirs if present
        for dname in ["1. projections", "2. projections_8bit", "3. contours", "4. spheroids_contour"]:
            d = data_dir / dname
            if d.exists() and d.is_dir():
                shutil.move(str(d), str(target / dname))

        return target

    # Case 4: maybe the ZIP already extracted as some folder containing plate_map.csv + Images, but name differs
    for p in data_dir.iterdir():
        if _is_probable_experiment_folder(p):
            if target.exists():
                raise SystemExit(f"ERROR: Target experiment_dir already exists: {target}")
            print(f"Fixing layout: renaming {p.name} → {experiment_dir}")
            p.rename(target)
            return target

    raise SystemExit(
        "ERROR: Could not find expected MDC dataset layout after extraction.\n"
        f"Expected either:\n"
        f"  - {data_dir}/{experiment_dir}/plate_map.csv + Images/\n"
        f"or\n"
        f"  - {data_dir}/plate_map.csv + {data_dir}/Images/\n"
    )


def main():

    # Load config (YAML) like the profiling demo
    try:
        import yaml  # noqa
    except Exception:
        raise SystemExit("ERROR: Missing dependency 'pyyaml'. Install with: pip install pyyaml")

    cfg_path = DEFAULT_CFG
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        # optional: allow passing a custom config path as first arg
        candidate = Path(sys.argv[1]).expanduser()
        if candidate.exists():
            cfg_path = candidate

    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    data_dir = (REPO_ROOT / cfg.get("data_dir", "demos/mdc/demo_mdc_data")).resolve()
    experiment_dir = str(cfg.get("experiment_dir", "BT549_MDC")).strip() or "BT549_MDC"

    print("Starting MDC demo download (Zenodo record: 18876611).")
    print("This is a lightweight demo dataset (~648 MB; precomputed projections, not full z-stacks).")
    print("Download time depends on your connection.")
    print(f"Download cache: {DOWNLOADS_DIR}")
    print(f"Extracting to:  {data_dir}")
    print(f"Experiment dir: {experiment_dir}\n")

    # 1) Query Zenodo API
    api_url = f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}"
    print(f"Fetching Zenodo record:\n  {api_url}")
    record = http_get_json(api_url)

    # 2) Pick zip and download
    zfile = pick_zip_file(record)
    file_key = zfile.get("key")
    file_url = zfile.get("links", {}).get("self")
    if not file_url or not file_key:
        raise SystemExit("ERROR: Zenodo record file metadata missing 'links.self' or 'key'.")

    zip_path = (DOWNLOADS_DIR / file_key).resolve()
    download(file_url, zip_path)

    # 3) Unzip to data_dir
    unzip(zip_path, data_dir)

    # 4) Fix layout so run script can be deterministic
    exp_path = ensure_expected_layout(data_dir, experiment_dir)

    # 5) Print summary
    print("\nMDC demo dataset ready.")
    print(f"Dataset folder:\n  {exp_path}")
    print("Key paths:")
    print(f"  - plate_map.csv: {exp_path / 'plate_map.csv'}")
    print(f"  - Images/:       {exp_path / 'Images'}")

    # optional: checksum display (useful for debugging)
    try:
        h = sha256_file(zip_path)
        print(f"\nDownloaded ZIP SHA256:\n  {h}")
    except Exception:
        pass


if __name__ == "__main__":
    main()