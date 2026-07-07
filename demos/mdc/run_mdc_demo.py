# demos/mdc/run_mdc_demo.py
"""
m3DinAI - Run the MDC demo pipeline.

Reads demos/mdc/config_mdc_demo.yaml (paths + parameters), locates the demo experiment
folder downloaded by download_mdc_demo_data.py, and invokes scripts/mdc/0_mdc_pipeline.py
on it to produce the MDC table and figures. This is a thin, reproducible wrapper around the
main pipeline for the example dataset.

Usage:
    python demos/mdc/download_mdc_demo_data.py   # once, to fetch the data
    python demos/mdc/run_mdc_demo.py
"""
import os
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # .../m3DinAI
DEFAULT_CFG = REPO_ROOT / "demos" / "mdc" / "config_mdc_demo.yaml"


def _load_cfg(cfg_path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except Exception:
        raise SystemExit("ERROR: Missing dependency 'pyyaml'. Install with: pip install pyyaml")

    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return cfg


def _bool_flag(flag_name: str, value: bool) -> list[str]:
    return [flag_name] if value else []


def main():
    cfg_path = DEFAULT_CFG
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        candidate = Path(sys.argv[1]).expanduser()
        if candidate.exists():
            cfg_path = candidate

    cfg = _load_cfg(cfg_path)

    # Paths from config
    data_dir = (REPO_ROOT / cfg.get("data_dir", "demos/mdc/demo_mdc_data")).resolve()
    experiment_dir = str(cfg.get("experiment_dir", "BT549_MDC")).strip() or "BT549_MDC"

    exp_dir = (data_dir / experiment_dir).resolve()
    images_dir = exp_dir / "Images"

    if not exp_dir.exists():
        raise SystemExit(
            f"ERROR: Experiment directory not found:\n  {exp_dir}\n"
            "Run the downloader first:\n"
            "  python demos/mdc/download_mdc_demo_data.py"
        )

    # Resolve pipeline script
    pipeline_script = (REPO_ROOT / cfg.get("mdc_pipeline_script", "scripts/mdc/0_mdc_pipeline.py")).resolve()
    if not pipeline_script.exists():
        raise SystemExit(f"ERROR: MDC pipeline script not found:\n  {pipeline_script}")

    # plate_map handling
    plate_map_cfg = str(cfg.get("plate_map", "")).strip()
    plate_map_path = (REPO_ROOT / plate_map_cfg).resolve() if plate_map_cfg else (exp_dir / "plate_map.csv")
    if not plate_map_path.exists():
        raise SystemExit(
            "ERROR: plate_map.csv not found.\n"
            f"Expected:\n  {plate_map_path}\n"
            "If your plate map is elsewhere, set 'plate_map' in config_mdc_demo.yaml."
        )

    # Build command
    cmd: list[str] = [sys.executable, str(pipeline_script), "--z-stack-dir", str(images_dir)]

    # optional args
    skip_if_exists = bool(cfg.get("skip_if_exists", True))
    if skip_if_exists:
        cmd.append("--skip-if-exists")

    steps = str(cfg.get("steps", "")).strip()
    if steps:
        cmd.extend(["--steps", steps])

    # rebuild toggles (only append if present in config)
    cmd.extend(_bool_flag("--rebuild-mip", bool(cfg.get("rebuild_mip", False))))
    cmd.extend(_bool_flag("--rebuild-features", bool(cfg.get("rebuild_features", False))))
    cmd.extend(_bool_flag("--rebuild-clustering", bool(cfg.get("rebuild_clustering", False))))

    # explicit plate map override (pipeline supports --plate-map)
    # Note: If your pipeline does NOT accept --plate-map, remove these two lines.
    cmd.extend(["--plate-map", str(plate_map_path)])

    # Print and run
    print("Running MDC demo with command:\n")
    print("  " + " ".join(shlex.quote(c) for c in cmd))
    print("\nWorking directory:")
    print(f"  {REPO_ROOT}\n")

    env = os.environ.copy()

    # Run from repo root so relative paths inside the pipeline behave predictably
    try:
        subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"ERROR: MDC demo failed with exit code {e.returncode}")

    print("\nMDC demo completed.")
    print("Outputs should be in:")
    print(f"  {exp_dir}")
    print("\nKey expected files (names may vary by pipeline version):")
    print("  - heatmap_cluster_plate_with_doses.png")
    print("  - MDC_table.csv (or .xlsx)")
    print("  - umap_kmeans_k2.png and/or umap_embedding_kmeans_k2.csv")
    print("  - features_with_kmeans_clusters_full.xlsx")


if __name__ == "__main__":
    main()