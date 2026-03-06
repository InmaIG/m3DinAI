import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
import os

# Carga archivos
bt_file = r"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D\Excels etiquetados\BT549_R1_72H_spheroid_features_trat.xlsx"
bt = pd.read_excel(bt_file)

hcc_file = r"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D\Excels etiquetados\HCC1806_R1_72H_spheroid_features_trat.xlsx"
hcc = pd.read_excel(hcc_file)

mda_file = r"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D\Excels etiquetados\MDA468_R1_72H_spheroid_features_trat.xlsx"
mda = pd.read_excel(mda_file)

# Features a graficar
features = ["Area", "Perimeter", "Circularity", "Solidity", "Extent", "MajorAxis", "MinorAxis", "AspectRatio"]

# Normalizar
scaler = MinMaxScaler()
for feature in features:
    bt[feature] = scaler.fit_transform(bt[[feature]])
    hcc[feature] = scaler.fit_transform(hcc[[feature]])
    mda[feature] = scaler.fit_transform(mda[[feature]])

# Preparar datos combinados
bt["Cell Line"] = "BT-549"
hcc["Cell Line"] = "HCC1806"
mda["Cell Line"] = "MDA-MB-468"

combined = pd.concat([bt, hcc, mda], ignore_index=True)

# Colores
palette = {
    "BT-549": "#aec7e8",
    "HCC1806": "#ffbb78",
    "MDA-MB-468": "#98df8a"
}

# Asegura que el directorio de salida exista
plot_dir = r"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D\ViolinPlot por features"
os.makedirs(plot_dir, exist_ok=True)

# Violin plots
for feature in features:
    plt.figure(figsize=(10, 6))
    sns.violinplot(
        data=combined,
        x="Cell Line",
        y=feature,
        inner="box",
        palette=palette
    )
    plt.title(f"Violin plot of {feature}", fontsize=20)
    plt.xlabel("Cell Line", fontsize=18)
    plt.ylabel(feature, fontsize=18)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.tight_layout()

    # Guarda el gráfico
    plt.savefig(os.path.join(plot_dir, f"violin_{feature}_normalized.png"), dpi=300)
    plt.close()
    print(f"✅ Saved: violin_{feature}_normalized.png")
