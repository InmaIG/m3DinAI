import os
import shutil
import argparse

# Root folder where we start searching
root_dir = r"DATA_ROOT"  # placeholder; pass the real path via --root-dir

# Destination folder for the collected Excel files
out_excels_dir = os.path.join(root_dir, "SPHEROIDS_EXCELS_FULL")
os.makedirs(out_excels_dir, exist_ok=True)

# Expected Excel filename
excel_name = "spheroid_features.xlsx"

# Default parameters (can be overridden by CLI)
timepoints = ["72H", "96H", "120H"]
replicates = ["R1", "R2", "R3"]
cell_lines = ["BT549", "MDA468", "HCC1806"]

# --- CLI ---
parser = argparse.ArgumentParser(description="m3DinAI - Collect per-experiment Excel outputs")
parser.add_argument("--root-dir", default=root_dir, help="Root directory containing experiments")
parser.add_argument("--out-excels-dir", default=out_excels_dir, help="Folder where collected excels will be copied")
parser.add_argument("--timepoints", default=",".join(timepoints), help="Comma-separated, e.g. 72H,96H")
parser.add_argument("--replicates", default=",".join(replicates), help="Comma-separated, e.g. R1,R2")
parser.add_argument("--cell-lines", default=",".join(cell_lines), help="Comma-separated, e.g. BT549,HCC1806")
args, _unknown = parser.parse_known_args()

root_dir = args.root_dir
out_excels_dir = args.out_excels_dir
os.makedirs(out_excels_dir, exist_ok=True)

timepoints = [x.strip() for x in args.timepoints.split(",") if x.strip()]
replicates = [x.strip() for x in args.replicates.split(",") if x.strip()]
cell_lines = [x.strip() for x in args.cell_lines.split(",") if x.strip()]

# Search and copy Excel files
for tp in timepoints:
    for rep in replicates:
        for cl in cell_lines:
            found = False

            tp_dir = os.path.join(root_dir, tp)
            rep_dir = os.path.join(tp_dir, rep)

            # Look inside folders whose name contains the cell line
            if os.path.isdir(rep_dir):
                for sub in os.listdir(rep_dir):
                    if cl in sub:
                        exp_dir = os.path.join(rep_dir, sub)
                        excel_path = os.path.join(exp_dir, excel_name)

                        if os.path.exists(excel_path):
                            new_name = f"{cl}_{rep}_{tp}_{excel_name}"
                            dst = os.path.join(out_excels_dir, new_name)
                            shutil.copy2(excel_path, dst)
                            print(f"Copied: {excel_path} -> {dst}")
                            found = True
                            break  # stop searching more folders for this (tp, rep, cl)

            if not found:
                print(f"[ERROR] Not found: {cl} - {rep} - {tp}")