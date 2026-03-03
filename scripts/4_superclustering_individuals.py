import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import umap
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
import matplotlib.pyplot as plt
import seaborn as sns

import warnings
warnings.filterwarnings("ignore", message="n_jobs value.*by setting random_state")

# --- FIXED COLOR MAP BY TREATMENT ---
color_map = {
    'DMSO': '#1f77b4',
    'Anthracyclines': '#ff7f0e',
    'Topoisomerase inhibitor': '#2ca02c',
    'Taxane': '#d62728',
    'MMS': '#9467bd'
}

"""
========================================================================
  MORPHOLOGICAL DATA ANALYSIS WITH UMAP & HIERARCHICAL CLUSTERING
========================================================================

This script automates the processing of multiple Excel files containing 
cell morphology data to perform the following steps:

1. Normalize numerical features.
2. Reduce dimensionality using UMAP.
3. Cluster samples using hierarchical clustering (Ward method).
4. Generate visualizations:
   - UMAP scatter plots colored by treatment
   - Dendrograms (optional, currently commented out)

---------------------------------------------------
INPUT:
- A folder containing `.xlsx` files, each with:
    - Numerical feature columns.
    - A 'tratamiento' column indicating the treatment type.
    - Optional: an 'Imagen' column with image names.

OUTPUT:
- A "RESULTADOS_GRAFICAS" subfolder containing:
    - UMAP plots with clusters (PNG format).
    - Dendrogram images (optional, saving is currently disabled).

---------------------------------------------------
REQUIREMENTS:
- Libraries: pandas, numpy, sklearn, umap-learn, scipy, matplotlib, seaborn
- Ensure column names are standardized.

---------------------------------------------------
NOTES:
- The number of clusters is fixed at 5 (can be adjusted).
- A fixed color map is used for consistent treatment coloring.
- Non-numerical columns are automatically excluded.

Author: [Your Name or Team]
Date: [Creation or Last Update Date]
"""

# UMAP NORMALIZADO Y FILTRADO OUTLIERS POR TRATAMIENTO

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

# --- FIXED COLOR MAP BY TREATMENT ---
color_map = {
    'DMSO': '#1f77b4',
    'Anthracyclines': '#ff7f0e',
    'Topoisomerase inhibitor': '#2ca02c',
    'Taxane': '#d62728',
    'MMS': '#9467bd'
}

# --- CONFIGURATION ---
excel_folder = r"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D\Excels etiquetados"
results_folder = os.path.join(excel_folder, "RESULTADOS_GRAFICAS")
os.makedirs(results_folder, exist_ok=True)

# --- PROCESS EACH EXCEL FILE ---
for file in os.listdir(excel_folder):
    if file.endswith(".xlsx"):
        excel_path = os.path.join(excel_folder, file)
        base_name = os.path.splitext(file)[0]

        print(f"Processing: {file}")

        try:
            # --- DATA LOADING ---
            df = pd.read_excel(excel_path)

            # --- CLEANING ---
            non_numeric_cols = df.select_dtypes(exclude=['number']).columns

            # filtrado outliers POR tratamiento
            filtered_groups = []
            for treatment in df['Treatment'].unique():
                df_treat = df[df['Treatment'] == treatment]
                df_treat_numeric = df_treat.drop(columns=non_numeric_cols)

                # outlier threshold
                medians = df_treat_numeric.median()
                stds = df_treat_numeric.std()
                lower = medians - 3 * stds
                upper = medians + 3 * stds
                mask = ((df_treat_numeric >= lower) & (df_treat_numeric <= upper)).all(axis=1)

                df_clean = df_treat.loc[mask]
                filtered_groups.append(df_clean)

            # recombinar todo
            df_filtered = pd.concat(filtered_groups).reset_index(drop=True)
            df_numeric_filtered = df_filtered.drop(columns=non_numeric_cols)

            # --- NORMALIZATION + UMAP ---
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(df_numeric_filtered)

            reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, random_state=42)
            X_umap = reducer.fit_transform(X_scaled)

            # --- CLUSTERING (labels) ---
            linked = linkage(X_umap, method='ward')
            cluster_labels = fcluster(linked, t=5, criterion='maxclust')

            # --- UMAP PLOT ---
            df_plot = pd.DataFrame(X_umap, columns=['UMAP1', 'UMAP2'])
            df_plot['Treatment'] = df_filtered['Treatment']
            df_plot['Cluster'] = cluster_labels

            if 'Filename' in df_filtered.columns:
                df_plot['Filename'] = df_filtered['Filename']

            plt.figure(figsize=(10, 7))
            sns.scatterplot(data=df_plot, x='UMAP1', y='UMAP2',
                            hue='Treatment', palette=color_map, s=60)
            for trat, g in df_plot.groupby('Treatment', group_keys=False):
                plt.text(g['UMAP1'].mean(), g['UMAP2'].mean(), trat,
                         ha='center', va='center', fontsize=16, weight='bold')
            plt.title(f'UMAP with clusters (filtered by treatment)')
            plt.xlabel('UMAP 1');
            plt.ylabel('UMAP 2');
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(os.path.join(results_folder, f"{base_name}_umap_filtered.png"))
            plt.close()

        except Exception as e:
            print(f"❌ Error processing {file}: {e}")
