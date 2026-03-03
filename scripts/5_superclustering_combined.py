"""
Combined-replicate UMAPs
------------------------
For every cell line and time-point, read the three replicate Excel files that
already contain the ‘tratamiento’ column, concatenate them, run a joint
standardisation + UMAP, and save a single figure:

    <cellLine>_<timepoint>_UMAP_combined.png

•  Colour  → Treatment   (fixed colour map, same as before)
•  Marker → Replicate   (R1 · R2 · R3)
•  Text    → Treatment label at the centroid
"""

# UMAP NORMALIZADO Y FILTRADO OUTLIERS POR TRATAMIENTO agrupado por linea celular

import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import umap
from scipy.cluster.hierarchy import linkage, fcluster
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings("ignore", message="n_jobs value.*by setting random_state")

# --- COLOR MAP ---
color_map = {
    'DMSO': '#1f77b4',
    'Anthracyclines': '#ff7f0e',
    'Topoisomerase inhibitor': '#2ca02c',
    'Taxane': '#d62728',
    'MMS': '#9467bd'
}

# --- CONFIGURATION ---
excel_folder = r"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D\Excels etiquetados"
results_folder = os.path.join(excel_folder, "RESULTADOS_GRAFICAS_COMBINED_LINE")
os.makedirs(results_folder, exist_ok=True)

# --- LIST OF CELL LINES ---
valid_lines = ['BT549', 'HCC1806', 'MDA468']

# --- PROCESS EACH LINEA ---
for linea in valid_lines:
    print(f"\nProcessing ALL data for {linea}")

    try:
        # recoger todos los ficheros de esa línea
        files = [f for f in os.listdir(excel_folder)
                 if f.endswith(".xlsx") and f.startswith(linea)]

        dfs = []
        for f in files:
            path = os.path.join(excel_folder, f)
            df = pd.read_excel(path)
            df["source_file"] = f
            dfs.append(df)

        # concatenar los 9 excel
        df_group = pd.concat(dfs, ignore_index=True)

        # filtrado de outliers por tratamiento
        non_numeric_cols = df_group.select_dtypes(exclude=['number']).columns

        filtered_groups = []
        for treatment in df_group['Treatment'].unique():
            df_treat = df_group[df_group['Treatment'] == treatment]
            df_treat_numeric = df_treat.drop(columns=non_numeric_cols)

            medians = df_treat_numeric.median()
            stds = df_treat_numeric.std()
            lower = medians - 3 * stds
            upper = medians + 3 * stds
            mask = ((df_treat_numeric >= lower) & (df_treat_numeric <= upper)).all(axis=1)

            df_clean = df_treat.loc[mask]
            filtered_groups.append(df_clean)

        df_filtered = pd.concat(filtered_groups).reset_index(drop=True)
        df_numeric_filtered = df_filtered.drop(columns=df_filtered.select_dtypes(exclude=['number']).columns)

        # normalization
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df_numeric_filtered)

        reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, random_state=42)
        X_umap = reducer.fit_transform(X_scaled)

        # clustering
        linked = linkage(X_umap, method='ward')
        cluster_labels = fcluster(linked, t=5, criterion='maxclust')

        # plot
        df_plot = pd.DataFrame(X_umap, columns=['UMAP1', 'UMAP2'])
        df_plot['Treatment'] = df_filtered['Treatment']
        df_plot['Replica'] = df_filtered['source_file']
        df_plot['Cluster'] = cluster_labels

        plt.figure(figsize=(12, 8))
        scatter = sns.scatterplot(
            data=df_plot,
            x='UMAP1',
            y='UMAP2',
            hue='Treatment',
            style='Replica',
            palette=color_map,
            s=60
        )

        # añadir etiquetas de texto en el centro de cada grupo
        for trat, g in df_plot.groupby('Treatment', group_keys=False):
            plt.text(
                g['UMAP1'].mean(),
                g['UMAP2'].mean(),
                trat,
                ha='center',
                va='center',
                fontsize=14,
                weight='bold'
            )

        plt.title(f"UMAP combined for {linea}")
        plt.xlabel('UMAP 1')
        plt.ylabel('UMAP 2')
        plt.grid(False)

        # --- PERSONALIZAR LEYENDA ---
        handles, labels = scatter.get_legend_handles_labels()
        custom_labels = []
        for label in labels:
            if label.endswith(".xlsx"):
                label_clean = label.replace("_spheroid_features_trat.xlsx", "")
                custom_labels.append(label_clean)
            else:
                custom_labels.append(label)

        plt.legend(
            handles=handles,
            labels=custom_labels,
            fontsize=8,  # tamaño texto leyenda
            loc='lower left',  # posición leyenda
            title_fontsize=14
        )

        plt.tight_layout()
        fname = f"{linea}_combined_all_UMAP.png"
        plt.savefig(os.path.join(results_folder, fname), dpi=300)
        plt.close()

        print(f"✅ Saved: {fname}")

    except Exception as e:
        print(f"❌ Error in {linea}: {e}")

