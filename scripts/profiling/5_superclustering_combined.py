# =======================================================================================
# m3DinAI - Combined-replicate UMAP per cell line
# File: scripts/profiling/5_superclustering_combined.py
#
# For every cell line, reads all labelled replicate/timepoint Excel files (which already
# contain the 'Treatment' column), concatenates them, applies per-treatment outlier
# filtering (median +/- 3 SD within each treatment), then runs a joint
# StandardScaler + UMAP (n_neighbors=15, min_dist=0.1, random_state=42) and Ward
# hierarchical clustering. Saves one combined UMAP figure per cell line:
#   * colour -> Treatment      (fixed colour map)
#   * marker -> source file    (replicate/timepoint)
#   * text   -> Treatment label at the group centroid
#
# Usage:
#   python 5_superclustering_combined.py --labeled-dir <LABELLED_DIR> --results-dir <OUT_DIR>
# =======================================================================================

import argparse
import os
import warnings

import pandas as pd
from sklearn.preprocessing import StandardScaler
import umap
from scipy.cluster.hierarchy import linkage, fcluster
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore", message="n_jobs value.*by setting random_state")

# Fixed colour map by treatment class
COLOR_MAP = {
    "DMSO": "#1f77b4",
    "Anthracyclines": "#ff7f0e",
    "Topoisomerase inhibitor": "#2ca02c",
    "Taxane": "#d62728",
    "MMS": "#9467bd",
}
VALID_LINES = ["BT549", "HCC1806", "MDA468"]


def process_line(line, excel_folder, results_folder):
    print(f"\nProcessing ALL data for {line}")
    # Collect every Excel file belonging to this cell line
    files = [f for f in os.listdir(excel_folder)
             if f.endswith(".xlsx") and f.startswith(line)]
    dfs = []
    for f in files:
        df = pd.read_excel(os.path.join(excel_folder, f))
        df["source_file"] = f
        dfs.append(df)
    df_group = pd.concat(dfs, ignore_index=True)  # concatenate the replicate/timepoint files

    # Per-treatment outlier filtering: outliers are defined WITHIN each treatment (so a
    # disrupted treatment isn't flagged relative to intact controls). A spheroid is kept
    # only if every feature is within median +/- 3 SD of its own treatment group.
    non_numeric_cols = df_group.select_dtypes(exclude=["number"]).columns
    filtered_groups = []
    for treatment in df_group["Treatment"].unique():
        df_treat = df_group[df_group["Treatment"] == treatment]
        df_treat_numeric = df_treat.drop(columns=non_numeric_cols)
        medians = df_treat_numeric.median()
        stds = df_treat_numeric.std()
        mask = ((df_treat_numeric >= medians - 3 * stds) &
                (df_treat_numeric <= medians + 3 * stds)).all(axis=1)
        filtered_groups.append(df_treat.loc[mask])
    df_filtered = pd.concat(filtered_groups).reset_index(drop=True)
    df_numeric_filtered = df_filtered.drop(columns=df_filtered.select_dtypes(exclude=["number"]).columns)

    # Standardisation + UMAP. z-scoring prevents large-range features from dominating;
    # n_neighbors=15 / min_dist=0.1 / random_state=42 are the study-wide UMAP settings
    # (fixed seed => reproducible embedding; UMAP is non-metric, distances are qualitative).
    X_scaled = StandardScaler().fit_transform(df_numeric_filtered)
    reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, random_state=42)
    X_umap = reducer.fit_transform(X_scaled)

    # Ward hierarchical clustering on the embedding, cut to at most 5 groups, used only to
    # annotate sub-structure in the combined plot.
    linked = linkage(X_umap, method="ward")
    cluster_labels = fcluster(linked, t=5, criterion="maxclust")

    # Plot
    df_plot = pd.DataFrame(X_umap, columns=["UMAP1", "UMAP2"])
    df_plot["Treatment"] = df_filtered["Treatment"]
    df_plot["Replica"] = df_filtered["source_file"]
    df_plot["Cluster"] = cluster_labels

    plt.figure(figsize=(12, 8))
    scatter = sns.scatterplot(data=df_plot, x="UMAP1", y="UMAP2", hue="Treatment",
                              style="Replica", palette=COLOR_MAP, s=60)

    # Add a text label at the centroid of each treatment group
    for treat, g in df_plot.groupby("Treatment", group_keys=False):
        plt.text(g["UMAP1"].mean(), g["UMAP2"].mean(), treat,
                 ha="center", va="center", fontsize=14, weight="bold")

    plt.title(f"UMAP combined for {line}")
    plt.xlabel("UMAP 1")
    plt.ylabel("UMAP 2")
    plt.grid(False)

    # Customise legend: strip the standard filename suffix from replicate labels
    handles, labels = scatter.get_legend_handles_labels()
    custom_labels = [lb.replace("_spheroid_features_trat.xlsx", "") if lb.endswith(".xlsx") else lb
                     for lb in labels]
    plt.legend(handles=handles, labels=custom_labels, fontsize=8, loc="lower left", title_fontsize=14)

    plt.tight_layout()
    fname = f"{line}_combined_all_UMAP.png"
    plt.savefig(os.path.join(results_folder, fname), dpi=300)
    plt.close()
    print(f"Saved: {fname}")


def main():
    ap = argparse.ArgumentParser(description="m3DinAI - combined-replicate UMAP per cell line")
    ap.add_argument("--labeled-dir", required=True, help="Directory with labelled Excel files")
    ap.add_argument("--results-dir", default=None, help="Output directory (default: <labeled-dir>/RESULTADOS_GRAFICAS_COMBINED_LINE)")
    args = ap.parse_args()

    excel_folder = args.labeled_dir
    results_folder = args.results_dir or os.path.join(excel_folder, "RESULTADOS_GRAFICAS_COMBINED_LINE")
    os.makedirs(results_folder, exist_ok=True)

    for line in VALID_LINES:
        try:
            process_line(line, excel_folder, results_folder)
        except Exception as e:
            print(f"Error in {line}: {e}")


if __name__ == "__main__":
    main()
