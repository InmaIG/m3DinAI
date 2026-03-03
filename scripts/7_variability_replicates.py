import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
import os

# Definir líneas celulares
cell_lines = ["BT549", "HCC1806", "MDA468"]

# Features a graficar (usa los nombres exactamente como están en los excels)
features = ["Area", "Perimeter", "Circularity", "Solidity", "Extent",
            "MajorAxis", "MinorAxis", "AspectRatio"]

# Carpeta de salida
output_dir = r"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D\Variability across replicates\Histograms"
os.makedirs(output_dir, exist_ok=True)

# Iterar por línea celular
for line in cell_lines:
    dfs = []
    for rep in ["R1", "R2", "R3"]:
        file_path = fr"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D\Excels etiquetados\{line}_{rep}_72H_spheroid_features_trat.xlsx"
        df = pd.read_excel(file_path)
        df["Replicate"] = rep
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)

    # Normalizar para comparar entre réplicas
    scaler = MinMaxScaler()
    for feature in features:
        combined[feature] = scaler.fit_transform(combined[[feature]])

    # Graficar histogramas por feature
    for feature in features:
        plt.figure(figsize=(10, 6))
        for rep in ["R1", "R2", "R3"]:
            subset = combined[combined["Replicate"] == rep]
            plt.hist(subset[feature], bins=30, alpha=0.5, label=rep)
        plt.title(f"{feature} distribution across replicates ({line})", fontsize=16)
        plt.xlabel(feature, fontsize=14)
        plt.ylabel("Frequency", fontsize=14)
        plt.legend(fontsize=12)
        plt.tight_layout()

        output_path = os.path.join(output_dir, f"{line}_{feature}_variability_histogram.png")
        plt.savefig(output_path, dpi=300)
        plt.close()
        print(f"✅ Saved: {output_path}")
