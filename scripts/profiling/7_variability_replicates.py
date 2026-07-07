# =======================================================================================
# m3DinAI - Reproducibility across replicates (per-feature histograms)
# File: scripts/profiling/7_variability_replicates.py
#
# For each cell line, overlays the distribution of every morphological feature across the
# three biological replicates (R1/R2/R3) at one timepoint, to visually assess
# reproducibility. Min-max normalisation (per feature, across replicates) is kept behind
# --normalize as in the original; the revision figure (with CV and effect sizes) is in
# scripts/profiling/14_figure3_reproducibility.py.
#
# Input filenames: <LINE>_<REPLICATE>_<TIMEPOINT>_spheroid_features_trat.xlsx
#
# Usage:
#   python 7_variability_replicates.py --in-dir <LABELLED_DIR> --out-dir <OUT_DIR>
#       [--timepoint 72H] [--normalize]
# =======================================================================================

import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

CELL_LINES = ["BT549", "HCC1806", "MDA468"]
REPLICATES = ["R1", "R2", "R3"]
FEATURES = ["Area", "Perimeter", "Circularity", "Solidity", "Extent", "MajorAxis", "MinorAxis", "AspectRatio"]


def main():
    ap = argparse.ArgumentParser(description="m3DinAI - reproducibility histograms across replicates")
    ap.add_argument("--in-dir", required=True, help="Directory with labelled *_spheroid_features_trat.xlsx")
    ap.add_argument("--out-dir", required=True, help="Directory to write histograms")
    ap.add_argument("--timepoint", default="72H")
    ap.add_argument("--normalize", action="store_true", help="Min-max normalise each feature before plotting")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    for line in CELL_LINES:
        dfs = []
        for rep in REPLICATES:
            fname = f"{line}_{rep}_{args.timepoint}_spheroid_features_trat.xlsx"
            df = pd.read_excel(os.path.join(args.in_dir, fname))
            df["Replicate"] = rep
            dfs.append(df)
        combined = pd.concat(dfs, ignore_index=True)

        if args.normalize:
            scaler = MinMaxScaler()
            for feature in FEATURES:
                combined[feature] = scaler.fit_transform(combined[[feature]])

        for feature in FEATURES:
            plt.figure(figsize=(10, 6))
            for rep in REPLICATES:
                subset = combined[combined["Replicate"] == rep]
                plt.hist(subset[feature], bins=30, alpha=0.5, label=rep)
            plt.title(f"{feature} distribution across replicates ({line})", fontsize=16)
            plt.xlabel(feature, fontsize=14)
            plt.ylabel("Frequency", fontsize=14)
            plt.legend(fontsize=12)
            plt.tight_layout()
            out_path = os.path.join(args.out_dir, f"{line}_{feature}_variability_histogram.png")
            plt.savefig(out_path, dpi=300)
            plt.close()
            print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
