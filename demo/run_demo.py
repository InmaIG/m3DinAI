# demo/run_demo.py
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

def run(cmd, env=None):
    print("\n=== Running ===")
    print(" ".join(cmd))
    p = subprocess.run(cmd, env=env)
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

    env = os.environ.copy()
    env["M3DINAI_ROOT_DIR"] = str(data_dir)
    env["M3DINAI_OUT_DIR"] = str(out_dir)

    # Standardize where scripts 2–4 will write/read (ENGLISH FOLDER NAMES)
    env["M3DINAI_EXCELS_DIR"] = str(out_dir / "excels_demo")
    env["M3DINAI_LABELED_DIR"] = str(out_dir / "excels_demo_labeled")
    env["M3DINAI_RESULTS_DIR"] = str(out_dir / "results_demo")
    env["M3DINAI_KEEP_TREATMENTS"] = ",".join(demo.get("keep_treatments", []))

    # Optional selection parameters
    env["M3DINAI_TIMEPOINTS"] = ",".join(demo.get("timepoints", []))
    env["M3DINAI_REPLICATES"] = ",".join(demo.get("replicates", []))
    env["M3DINAI_EXPERIMENT_NAME_CONTAINS"] = ",".join(demo.get("include_experiment_name_contains", []))

    # Resolve script paths
    s1 = (REPO_ROOT / pipeline["feature_extraction"]).resolve()
    s2 = (REPO_ROOT / pipeline["copy_excels"]).resolve()
    s3 = (REPO_ROOT / pipeline["label_treatments"]).resolve()
    s4 = (REPO_ROOT / pipeline["umap_clustering"]).resolve()

    py = sys.executable

    # Run pipeline (1→2→3→4)
    run([py, str(s1)], env=env)
    run([py, str(s2)], env=env)
    run([py, str(s3)], env=env)
    run([py, str(s4)], env=env)

    print("\n✅ Demo complete.")
    print(f"Outputs written to:\n  {out_dir}")
    print("Key folders:")
    print(f"  - {Path(env['M3DINAI_RESULTS_DIR'])}")

if __name__ == "__main__":
    try:
        import yaml  # noqa
    except Exception:
        raise SystemExit("ERROR: Missing dependency 'pyyaml'. Install with: pip install pyyaml")
    main()