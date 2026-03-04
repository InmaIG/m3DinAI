# demo/run_demo.py
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

def run(cmd):
    print("\n=== Running ===")
    print(" ".join(cmd))
    p = subprocess.run(cmd)
    if p.returncode != 0:
        raise SystemExit(f"ERROR: command failed with exit code {p.returncode}")

def main():
    cfg_path = REPO_ROOT / "demo" / "config_demo.yaml"
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    demo = cfg["demo"]
    pipeline = cfg["pipeline"]

    data_dir = (REPO_ROOT / demo["data_dir"]).resolve()
    out_dir = (REPO_ROOT / demo["out_dir"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Standard output dirs (English)
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

    # Resolve script paths
    s1 = (REPO_ROOT / pipeline["feature_extraction"]).resolve()
    s2 = (REPO_ROOT / pipeline["copy_excels"]).resolve()
    s3 = (REPO_ROOT / pipeline["label_treatments"]).resolve()
    s4 = (REPO_ROOT / pipeline["umap_clustering"]).resolve()

    py = sys.executable

    # Run pipeline (1→2→3→4) using CLI args (no env vars)
    cmd1 = [py, str(s1), "--root-dir", str(data_dir)]
    if tp_arg:
        cmd1 += ["--timepoints", tp_arg]
    if rep_arg:
        cmd1 += ["--replicates", rep_arg]
    if exp_contains_arg:
        cmd1 += ["--exp-contains", exp_contains_arg]
    run(cmd1)

    cmd2 = [py, str(s2), "--root-dir", str(data_dir), "--out-excels-dir", str(excels_dir)]
    if tp_arg:
        cmd2 += ["--timepoints", tp_arg]
    if rep_arg:
        cmd2 += ["--replicates", rep_arg]
    run(cmd2)

    cmd3 = [py, str(s3), "--excels-dir", str(excels_dir), "--out-labeled-dir", str(labeled_dir)]
    run(cmd3)

    cmd4 = [py, str(s4), "--labeled-dir", str(labeled_dir), "--results-dir", str(results_dir)]
    if keep_arg:
        cmd4 += ["--keep-treatments", keep_arg]
    run(cmd4)

    print("\n✅ Demo complete.")
    print(f"Outputs written to:\n  {out_dir}")
    print("Key folders:")
    print(f"  - {results_dir}")

if __name__ == "__main__":
    try:
        import yaml  # noqa
    except Exception:
        raise SystemExit("ERROR: Missing dependency 'pyyaml'. Install with: pip install pyyaml")
    main()