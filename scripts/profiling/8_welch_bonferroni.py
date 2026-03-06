# WELCH Y BONFERRONI

import re
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import ttest_ind

# ------------------------------------------------------------------
# 1. Directorios
# ------------------------------------------------------------------
base_dir = Path(r"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D\Excels etiquetados\RESULTADOS_HEATMAPS")
out_dir  = base_dir / "RESULTADOS_VARIACION_GRUPADA"
out_dir.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# 2. Cargar todos los *_variation_summary.csv
# ------------------------------------------------------------------
csv_files = list(base_dir.glob("*_variation_summary.csv"))
if not csv_files:
    raise FileNotFoundError("No *_variation_summary.csv files found.")

pat = re.compile(r"(BT549|HCC1806|MDA468)_R(\d)_(\d{2,3}H)", flags=re.IGNORECASE)

records = []
for csv_path in csv_files:
    m = pat.search(csv_path.name)
    if m:
        line, rep, time = m.groups()
        df = pd.read_csv(csv_path)
        df["CellLine"]  = line.upper()
        df["Replicate"] = f"R{rep}"
        df["Time"]      = time.upper()
        records.append(df)

if not records:
    raise ValueError("CSV names do not match expected pattern <Line>_R<rep>_<Time>_...")

df_all = pd.concat(records, ignore_index=True)

# ------------------------------------------------------------------
# 3. Fijar orden de tratamientos
# ------------------------------------------------------------------
order = ["MMS", "Anthracyclines", "Topoisomerase inhibitor", "Taxane", "DMSO"]

# ------------------------------------------------------------------
# 4. Dibujar una figura por (línea, tiempo)
# ------------------------------------------------------------------
for (line, time), g in df_all.groupby(["CellLine", "Time"]):

    # Re-castear Treatment como categoría ordenada
    g["Treatment"] = pd.Categorical(g["Treatment"], categories=order, ordered=True)

    # Resumen por tratamiento
    agg = (
        g.groupby("Treatment", observed=True)
          .agg(mean_ratio=("MeanRatio", "mean"),
               sd_ratio  =("MeanRatio", "std"))
          .reset_index()
    )
    agg["Treatment"] = pd.Categorical(agg["Treatment"], categories=order, ordered=True)

    # Figura
    plt.figure(figsize=(10, 5))

    # Barras de media
    ax = sns.barplot(
        data=agg, x="Treatment", y="mean_ratio",
        hue="Treatment", palette="pastel",
        edgecolor="black", errorbar=None, legend=False
    )

    # Barras de error ±SD
    for i, row in agg.iterrows():
        if not np.isnan(row["sd_ratio"]):
            ax.errorbar(i, row["mean_ratio"],
                        yerr=row["sd_ratio"],
                        fmt='none', c='black', capsize=4, lw=1.2)

    # Puntos individuales (réplicas)
    sns.stripplot(
        data=g, x="Treatment", y="MeanRatio",
        hue="Replicate", dodge=True,
        palette="dark:#33333330", linewidth=0.5,
        edgecolor="black", size=6, ax=ax
    )
    ax.legend(title="Replicate", loc="upper right")

    # ---------- t-test vs DMSO con Bonferroni ----------
    dmso_vals = g.loc[g["Treatment"] == "DMSO", "MeanRatio"].values
    n_comp = len(order) - 1  # comparaciones con DMSO

    def p_to_star(p):
        return ("****" if p < 1e-4 else
                "***"  if p < 1e-3 else
                "**"   if p < 1e-2 else
                "*"    if p < 0.05 else
                "ns")

    for i, treat in enumerate(order):
        if treat == "DMSO":
            continue
        vals = g.loc[g["Treatment"] == treat, "MeanRatio"].values
        if len(vals) == 0:
            continue
        t, p_raw = ttest_ind(vals, dmso_vals, equal_var=False)
        p_adj = p_raw * n_comp           # Bonferroni
        star  = p_to_star(p_adj)

        y_bar = agg.loc[agg["Treatment"] == treat, "mean_ratio"].values[0]
        y_sd  = agg.loc[agg["Treatment"] == treat, "sd_ratio" ].values[0]
        ax.text(i, y_bar + y_sd + 4, star,
                ha="center", va="bottom", fontsize=9, weight="bold")

    # Ajustes finales
    ax.set_ylim(0, 100)
    ax.set_ylabel("Mean Activity Ratio (± SD)")
    ax.set_xlabel("Treatment")
    ax.set_title(f"{line} – {time}  (all replicates)\nWelch t-test vs DMSO • Bonferroni corrected")
    for tick in ax.get_xticklabels():
        tick.set_rotation(45)

    plt.tight_layout()
    out_path = out_dir / f"{line}_{time}_variation_grouped.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print("✓ Saved", out_path)
