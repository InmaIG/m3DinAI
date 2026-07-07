# =======================================================================================
# m3DinAI - Grouped Activity Ratio per (cell line, timepoint) with significance
# File: scripts/profiling/9_welch_bonferroni.py
#
# Loads the per-experiment *_variation_summary.csv files (per-spheroid MeanRatio produced
# by the Activity Ratio step), groups them by (cell line, timepoint), and draws one bar
# chart per group: mean Activity Ratio +/- SD by treatment, with individual replicate
# points overlaid. Significance vs DMSO is tested with a Welch t-test (Bonferroni
# corrected). NOTE: the revision uses non-parametric tests + effect sizes instead
# (see scripts/profiling/12_figure6_AR.py).
#
# Input: a directory of *_variation_summary.csv named <LINE>_R<n>_<TIME>_*.csv
#
# Usage:
#   python 9_welch_bonferroni.py --in-dir <SUMMARY_DIR> --out-dir <OUT_DIR>
# =======================================================================================

import argparse
import re
from pathlib import Path
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import ttest_ind

TREATMENT_ORDER = ["MMS", "Anthracyclines", "Topoisomerase inhibitor", "Taxane", "DMSO"]
NAME_PATTERN = re.compile(r"(BT549|HCC1806|MDA468)_R(\d)_(\d{2,3}H)", flags=re.IGNORECASE)


def p_to_star(p):
    return ("****" if p < 1e-4 else "***" if p < 1e-3 else
            "**" if p < 1e-2 else "*" if p < 0.05 else "ns")


def load_summaries(in_dir: Path) -> pd.DataFrame:
    csv_files = list(in_dir.glob("*_variation_summary.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No *_variation_summary.csv files found in {in_dir}.")
    records = []
    for csv_path in csv_files:
        m = NAME_PATTERN.search(csv_path.name)
        if not m:
            continue
        line, rep, time = m.groups()
        df = pd.read_csv(csv_path)
        df["CellLine"] = line.upper()
        df["Replicate"] = f"R{rep}"
        df["Time"] = time.upper()
        records.append(df)
    if not records:
        raise ValueError("CSV names do not match expected pattern <Line>_R<rep>_<Time>_...")
    return pd.concat(records, ignore_index=True)


def main():
    ap = argparse.ArgumentParser(description="m3DinAI - grouped Activity Ratio bar charts (Welch + Bonferroni)")
    ap.add_argument("--in-dir", required=True, help="Directory with *_variation_summary.csv files")
    ap.add_argument("--out-dir", required=True, help="Directory to write the figures")
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df_all = load_summaries(in_dir)

    # One figure per (cell line, timepoint)
    for (line, time), g in df_all.groupby(["CellLine", "Time"]):
        g = g.copy()
        g["Treatment"] = pd.Categorical(g["Treatment"], categories=TREATMENT_ORDER, ordered=True)

        # Per-treatment summary (mean +/- SD of MeanRatio)
        agg = (g.groupby("Treatment", observed=True)
                 .agg(mean_ratio=("MeanRatio", "mean"), sd_ratio=("MeanRatio", "std"))
                 .reset_index())
        agg["Treatment"] = pd.Categorical(agg["Treatment"], categories=TREATMENT_ORDER, ordered=True)

        plt.figure(figsize=(10, 5))
        ax = sns.barplot(data=agg, x="Treatment", y="mean_ratio", hue="Treatment",
                         palette="pastel", edgecolor="black", errorbar=None, legend=False)

        # Error bars (+/- SD)
        for i, row in agg.iterrows():
            if not np.isnan(row["sd_ratio"]):
                ax.errorbar(i, row["mean_ratio"], yerr=row["sd_ratio"],
                            fmt="none", c="black", capsize=4, lw=1.2)

        # Individual replicate points
        sns.stripplot(data=g, x="Treatment", y="MeanRatio", hue="Replicate", dodge=True,
                      palette="dark:#33333330", linewidth=0.5, edgecolor="black", size=6, ax=ax)
        ax.legend(title="Replicate", loc="upper right")

        # Significance vs DMSO: Welch's t-test (equal_var=False) does NOT assume equal
        # variances between a treatment and DMSO, which is safer than Student's t here.
        # Bonferroni multiplies each p-value by the number of treatment-vs-DMSO comparisons
        # (n_comp) to control the family-wise error rate across the 4 tests in the panel.
        # (The revision reports non-parametric tests + effect sizes instead - see
        #  scripts/profiling/12_figure6_AR.py in the revision materials.)
        dmso_vals = g.loc[g["Treatment"] == "DMSO", "MeanRatio"].values
        n_comp = len(TREATMENT_ORDER) - 1  # number of treatment-vs-DMSO comparisons
        for i, treat in enumerate(TREATMENT_ORDER):
            if treat == "DMSO":
                continue
            vals = g.loc[g["Treatment"] == treat, "MeanRatio"].values
            if len(vals) == 0:
                continue
            _, p_raw = ttest_ind(vals, dmso_vals, equal_var=False)
            star = p_to_star(p_raw * n_comp)  # Bonferroni
            y_bar = agg.loc[agg["Treatment"] == treat, "mean_ratio"].values[0]
            y_sd = agg.loc[agg["Treatment"] == treat, "sd_ratio"].values[0]
            ax.text(i, y_bar + y_sd + 4, star, ha="center", va="bottom", fontsize=9, weight="bold")

        ax.set_ylim(0, 100)
        ax.set_ylabel("Mean Activity Ratio (+/- SD)")
        ax.set_xlabel("Treatment")
        ax.set_title(f"{line} - {time}  (all replicates)\nWelch t-test vs DMSO - Bonferroni corrected")
        for tick in ax.get_xticklabels():
            tick.set_rotation(45)

        plt.tight_layout()
        out_path = out_dir / f"{line}_{time}_variation_grouped.png"
        plt.savefig(out_path, dpi=300)
        plt.close()
        print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
