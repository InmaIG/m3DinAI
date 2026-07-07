# demos/profiling/run_profiling_demo.py
"""
m3DinAI - Run the profiling demo pipeline.

Reads demos/profiling/config_profiling_demo.yaml and runs the profiling scripts
(feature extraction, treatment labelling, embedding/plots) on the demo dataset downloaded by
download_profiling_demo_data.py. Reproducible wrapper around the main profiling workflow.

Usage:
    python demos/profiling/download_profiling_demo_data.py   # once, to fetch the data
    python demos/profiling/run_profiling_demo.py
"""
import argparse
import subprocess
import sys
from pathlib import Path

import yaml

DEMO_DIR = Path(__file__).resolve().parent          # .../m3DinAI/demos/profiling
REPO_ROOT = Path(__file__).resolve().parents[2]     # .../m3DinAI


def run(cmd):
    print("\n=== Running ===")
    print(" ".join(cmd))
    p = subprocess.run(cmd)
    if p.returncode != 0:
        raise SystemExit(f"ERROR: command failed with exit code {p.returncode}")


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"ERROR: {label} not found:\n  {path}")


def _has_any_files(dir_path: Path, patterns: list[str]) -> bool:
    if not dir_path.exists():
        return False
    for pat in patterns:
        if any(dir_path.glob(pat)):
            return True
    return False


def main():
    ap = argparse.ArgumentParser(description="Run m3DinAI profiling demo (scripts 1→4).")
    ap.add_argument(
        "--config",
        default=str(DEMO_DIR / "config_profiling_demo.yaml"),
        help="Path to config YAML (default: demos/profiling/config_profiling_demo.yaml).",
    )
    ap.add_argument(
        "--skip-if-exists",
        action="store_true",
        help="Skip steps whose outputs already exist (default behavior).",
    )
    ap.add_argument(
        "--rebuild",
        action="store_true",
        help="Force re-running all steps (ignore existing outputs).",
    )
    args = ap.parse_args()

    skip_if_exists = bool(args.skip_if_exists) and not bool(args.rebuild)

    cfg_path = Path(args.config).expanduser().resolve()
    _require_file(cfg_path, "Config file")

    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    demo = cfg.get("demo", {})
    pipeline = cfg.get("pipeline", {})

    data_dir = (DEMO_DIR / demo.get("data_dir", "demo_data")).resolve()
    out_dir = (DEMO_DIR / demo.get("out_dir", "demo_out")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    excels_dir = (out_dir / "excels_demo").resolve()
    labeled_dir = (out_dir / "excels_demo_labeled").resolve()
    results_dir = (out_dir / "results_demo").resolve()
    excels_dir.mkdir(parents=True, exist_ok=True)
    labeled_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    timepoints = demo.get("timepoints", [])
    replicates = demo.get("replicates", [])
    keep_treatments = demo.get("keep_treatments", [])
    exp_contains = demo.get("include_experiment_name_contains", [])

    tp_arg = ",".join(timepoints)
    rep_arg = ",".join(replicates)
    keep_arg = ",".join(keep_treatments)
    exp_contains_arg = ",".join(exp_contains)

    s1 = (REPO_ROOT / pipeline.get("feature_extraction", "")).resolve()
    s2 = (REPO_ROOT / pipeline.get("copy_excels", "")).resolve()
    s3 = (REPO_ROOT / pipeline.get("label_treatments", "")).resolve()
    s4 = (REPO_ROOT / pipeline.get("umap_clustering", "")).resolve()

    _require_file(s1, "Feature extraction script")
    _require_file(s2, "Copy excels script")
    _require_file(s3, "Label treatments script")
    _require_file(s4, "UMAP/clustering script")

    py = sys.executable

    # Step 1: feature extraction
    # Heuristic: if we already have copied excels in excels_dir, we assume step 1+2 were done.
    step1_done = _has_any_files(excels_dir, ["*.xlsx"])
    if skip_if_exists and step1_done:
        print("\n=== Skipping step 1 (feature extraction): outputs already present in excels_demo/ ===")
    else:
        cmd1 = [py, str(s1), "--root-dir", str(data_dir)]
        if tp_arg:
            cmd1 += ["--timepoints", tp_arg]
        if rep_arg:
            cmd1 += ["--replicates", rep_arg]
        if exp_contains_arg:
            cmd1 += ["--exp-contains", exp_contains_arg]
        run(cmd1)

    # Step 2: copy excels
    step2_done = _has_any_files(excels_dir, ["*.xlsx"])
    if skip_if_exists and step2_done:
        print("\n=== Skipping step 2 (copy excels): excels already present in excels_demo/ ===")
    else:
        cmd2 = [py, str(s2), "--root-dir", str(data_dir), "--out-excels-dir", str(excels_dir)]
        if tp_arg:
            cmd2 += ["--timepoints", tp_arg]
        if rep_arg:
            cmd2 += ["--replicates", rep_arg]
        run(cmd2)

    # Step 3: label treatments
    step3_done = _has_any_files(labeled_dir, ["*.xlsx"])
    if skip_if_exists and step3_done:
        print("\n=== Skipping step 3 (label treatments): labeled excels already present ===")
    else:
        cmd3 = [py, str(s3), "--excels-dir", str(excels_dir), "--out-labeled-dir", str(labeled_dir)]
        run(cmd3)

    # Step 4: UMAP + clustering
    step4_done = _has_any_files(results_dir, ["*.png", "*.csv"])
    if skip_if_exists and step4_done:
        print("\n=== Skipping step 4 (UMAP/clustering): results already present ===")
    else:
        cmd4 = [py, str(s4), "--labeled-dir", str(labeled_dir), "--results-dir", str(results_dir)]
        if keep_arg:
            cmd4 += ["--keep-treatments", keep_arg]
        run(cmd4)

    print("\nDemo complete.")
    print(f"Outputs written to:\n  {out_dir}")
    print("Key folders:")
    print(f"  - {results_dir}")


if __name__ == "__main__":
    try:
        import yaml  # noqa
    except Exception:
        raise SystemExit("ERROR: Missing dependency 'pyyaml'. Install with: pip install pyyaml")

    main()