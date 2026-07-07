# =======================================================================================
# m3DinAI - Figure 2: per-feature violin plots by cell line
# File: scripts/profiling/6_violin_plots.py
#
# Reads the labelled per-spheroid Excel files for the three cell lines (one replicate /
# timepoint) and draws one violin plot per morphological feature, comparing the cell
# lines. Historically features were min-max normalised before plotting; this is kept
# behind --normalize for reproducibility, but the revised figure uses raw values
# (see scripts/profiling/13_figure2_violins.py for the revision version with statistics).
#
# Input filenames follow: <LINE>_<REPLICATE>_<TIMEPOINT>_spheroid_features_trat.xlsx
#
# Usage:
#   python 6_violin_plots.py --in-dir <LABELLED_DIR> --out-dir <OUT_DIR>
#       [--replicate R1] [--timepoint 72H] [--normalize]
# =======================================================================================

import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler

LINE_TAGS = {"BT549": "BT-549", "HCC1806": "HCC1806", "MDA468": "MDA-MB-468"}
FEATURES = ["Area", "Perimeter", "Circularity", "Solidity", "Extent", "MajorAxis", "MinorAxis", "AspectRatio"]
PALETTE = {"BT-549": "#aec7e8", "HCC1806": "#ffbb78", "MDA-MB-468": "#98df8a"}


def main():
    ap = argparse.ArgumentParser(description="m3DinAI - Figure 2 violin plots by cell line")
    ap.add_argument("--in-dir", required=True, help="Directory with labelled *_spheroid_features_trat.xlsx")
    ap.add_argument("--out-dir", required=True, help="Directory to write violin plots")
    ap.add_argument("--replicate", default="R1")
    ap.add_argument("--timepoint", default="72H")
    ap.add_argument("--normalize", action="store_true", help="Min-max normalise each feature before plotting")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # Load one Excel per cell line
    frames = []
    for tag, pretty in LINE_TAGS.items():
        fname = f"{tag}_{args.replicate}_{args.timepoint}_spheroid_features_trat.xlsx"
        path = os.path.join(args.in_dir, fname)
        df = pd.read_excel(path)
        if args.normalize:
            scaler = MinMaxScaler()
            for feature in FEATURES:
                df[feature] = scaler.fit_transform(df[[feature]])
        df["Cell Line"] = pretty
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)

    suffix = "_normalized" if args.normalize else ""
    for feature in FEATURES:
        plt.figure(figsize=(10, 6))
        sns.violinplot(data=combined, x="Cell Line", y=feature, inner="box", palette=PALETTE)
        plt.title(f"Violin plot of {feature}", fontsize=20)
        plt.xlabel("Cell Line", fontsize=18)
        plt.ylabel(feature, fontsize=18)
        plt.xticks(fontsize=14)
        plt.yticks(fontsize=14)
        plt.tight_layout()
        out_path = os.path.join(args.out_dir, f"violin_{feature}{suffix}.png")
        plt.savefig(out_path, dpi=300)
        plt.close()
        print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
