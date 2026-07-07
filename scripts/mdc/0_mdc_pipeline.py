# =======================================================================================
# m3DinAI - MDC original pipeline (with CLI + resume/skip-if-exists)
# File: scripts/0_mdc_pipeline.py
# =======================================================================================

import os
import re
import random
import argparse

import cv2
import numpy as np
import pandas as pd
import mahotas as mh
import matplotlib.pyplot as plt
from tqdm import tqdm

from skimage.feature import local_binary_pattern, graycomatrix, graycoprops
import SimpleITK as sitk
from radiomics import featureextractor

import umap
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

# --- Silence PyRadiomics warnings/logging ---
import logging
import warnings

warnings.filterwarnings("ignore", message="Shape features are only available 3D input.*")
warnings.filterwarnings("ignore", message="GLCM is symmetrical.*")

logging.getLogger("radiomics").setLevel(logging.ERROR)
for name in [
    "radiomics.featureextractor",
    "radiomics.glcm",
    "radiomics.shape",
    "radiomics.firstorder",
    "radiomics.imageoperations",
]:
    logging.getLogger(name).setLevel(logging.ERROR)


# =======================================================================================
# CLI
# =======================================================================================

def parse_steps(s: str) -> set[int]:
    out = set()
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def parse_args():
    p = argparse.ArgumentParser(description="m3DinAI - MDC original pipeline")
    p.add_argument(
        "--z-stack-dir",
        required=True,
        help=r"Path to Images folder containing z-stacks (e.g. ...\Measurement 1 - Copy\Images)",
    )
    p.add_argument(
        "--plate-map",
        default="",
        help="Optional path to plate_map.csv. If empty, uses <experiment_dir>/plate_map.csv",
    )

    p.add_argument("--skip-if-exists", action="store_true", help="Skip steps if outputs already exist")
    p.add_argument("--rebuild-mip", action="store_true", help="Force rebuild projections/contours/spheroids")
    p.add_argument("--rebuild-features", action="store_true", help="Force rebuild feature Excel")
    p.add_argument("--rebuild-clustering", action="store_true", help="Force rebuild clustering + heatmap + MDC")

    p.add_argument("--steps", default="1-10", help="Steps to run (default 1-10). Examples: 7, 8-10, 9-10")
    p.add_argument("--seed", type=int, default=42, help="Random seed (UMAP/KMeans + sampling)")

    # Clustering parameters (defaults reproduce the manuscript analysis).
    #  --pca-components 20 : PCA denoises/decorrelates the ~hundreds of radiomics features
    #                        and speeds up UMAP; 20 PCs retain the dominant morphological
    #                        variance while discarding noise.
    #  --umap-neighbors 15 / --umap-min-dist 0.1 : standard UMAP settings balancing local
    #                        vs global structure (same values used across the study).
    #  --kmeans-k 2        : the MDC assay only needs two morphological states -
    #                        "unaffected" vs "affected"; k=2 partitions the embedding into
    #                        those two groups (anchored to DMSO in step 10).
    #  --seed 42           : fixes UMAP/KMeans/sampling for reproducibility.
    p.add_argument("--pca-components", type=int, default=20)
    p.add_argument("--umap-neighbors", type=int, default=15)
    p.add_argument("--umap-min-dist", type=float, default=0.1)
    p.add_argument("--kmeans-k", type=int, default=2)

    return p.parse_args()


args = parse_args()
RUN = parse_steps(args.steps)

random.seed(args.seed)
np.random.seed(args.seed)

SKIP_IF_EXISTS = bool(args.skip_if_exists)
REBUILD_MIP = bool(args.rebuild_mip)
REBUILD_FEATURES = bool(args.rebuild_features)
REBUILD_CLUSTERING = bool(args.rebuild_clustering)

z_stack_dir = args.z_stack_dir
if not os.path.isdir(z_stack_dir):
    raise FileNotFoundError(f"z_stack_dir not found or not a directory: {z_stack_dir}")

# experiment_dir = parent of Images
base_dir = os.path.dirname(z_stack_dir)

# plate_map default: <experiment_dir>/plate_map.csv
plate_map_path = args.plate_map.strip() if args.plate_map.strip() else os.path.join(base_dir, "plate_map.csv")

# Outputs (same structure you used)
output_dir_mip16 = os.path.join(base_dir, "1. projections")
output_dir_mip8 = os.path.join(base_dir, "2. projections_8bit")
contours_dir = os.path.join(base_dir, "3. contours")
spheroids_dir = os.path.join(base_dir, "4. spheroids_contour")

os.makedirs(output_dir_mip16, exist_ok=True)
os.makedirs(output_dir_mip8, exist_ok=True)
os.makedirs(contours_dir, exist_ok=True)
os.makedirs(spheroids_dir, exist_ok=True)

output_excel_path = os.path.join(base_dir, "spheroid_features_full.xlsx")
output_excel_clusters = os.path.join(base_dir, "features_with_kmeans_clusters_full.xlsx")

umap_png_path = os.path.join(base_dir, "umap_kmeans_k2.png")
umap_csv_path = os.path.join(base_dir, "umap_embedding_kmeans_k2.csv")

heatmap_path = os.path.join(base_dir, "heatmap_cluster_plate_with_doses.png")

mdc_out_xlsx = os.path.join(base_dir, "MDC_table.xlsx")
mdc_out_csv = os.path.join(base_dir, "MDC_table.csv")


# =======================================================================================
# Helpers
# =======================================================================================

def any_tiffs_in_dir(d: str) -> bool:
    return os.path.isdir(d) and any(f.lower().endswith(".tiff") for f in os.listdir(d))


def extract_position_from_filename(filename: str):
    m = re.search(r"r(\d{2})c(\d{2})", str(filename), re.IGNORECASE)
    if not m:
        return None, None
    return int(m.group(1)) - 1, int(m.group(2)) - 1  # 0-based


def rc_to_pos(rc: str):
    m = re.search(r"r(\d{2})c(\d{2})", str(rc), re.IGNORECASE)
    if not m:
        return None, None
    return int(m.group(1)) - 1, int(m.group(2)) - 1  # 0-based


def filename_to_rc(fn: str) -> str:
    m = re.search(r"r(\d{2})c(\d{2})", str(fn), re.IGNORECASE)
    if not m:
        return ""
    return f"r{int(m.group(1)):02d}c{int(m.group(2)):02d}".lower()


def fmt_dose_3dp(x):
    """
    Requested: round to 3 decimals for heatmap labels.
    Keep it readable: strip trailing zeros and dot.
    """
    try:
        xf = float(x)
    except Exception:
        return str(x).strip()

    s = f"{xf:.3f}".rstrip("0").rstrip(".")
    # avoid "-0"
    if s in ("-0", "-0.0", "-0.00", "-0.000"):
        s = "0"
    return s


def show_random_grid(image_dir: str, max_images: int = 20, cols: int = 5, title_prefix: str = ""):
    files = [f for f in os.listdir(image_dir) if f.lower().endswith(".tiff")]
    n = min(max_images, len(files))
    sel = random.sample(files, n) if n > 0 else []

    if n == 0:
        return

    rows = (n // cols) + (1 if n % cols else 0)
    fig, axes = plt.subplots(rows, cols, figsize=(15, 3 * rows))
    axes = np.array(axes).reshape(rows, cols)

    def normalize_image(img):
        mn = np.min(img)
        mx = np.max(img)
        if mx > mn:
            out = (img - mn) / (mx - mn) * 255.0
        else:
            out = np.zeros_like(img)
        return out.astype(np.uint8)

    for ax, fn in zip(axes.flat, sel):
        p = os.path.join(image_dir, fn)
        img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        if img is None:
            ax.axis("off")
            continue

        if len(img.shape) == 2:
            ax.imshow(normalize_image(img), cmap="gray")
        else:
            ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        ax.set_title(f"{title_prefix}{fn}", fontsize=7)
        ax.axis("off")

    for ax in axes.flat[len(sel):]:
        ax.axis("off")

    plt.tight_layout()
    plt.show()


# =======================================================================================
# 1) MIP (16-bit)
# =======================================================================================

pattern = re.compile(
    r"(r\d{2}c\d{2}f\d{2})p(01|02|03|04)-ch\d+sk\d+fk\d+fl\d+\.tiff$",
    re.IGNORECASE,
)

if 1 in RUN:
    mip16_existing = any_tiffs_in_dir(output_dir_mip16)

    if SKIP_IF_EXISTS and mip16_existing and not REBUILD_MIP:
        print(f"[1] Skipping MIP (16-bit): already exists in {output_dir_mip16}")
    else:
        image_groups = {}
        for file in os.listdir(z_stack_dir):
            m = pattern.match(file)
            if m:
                base_name = m.group(1)
                image_groups.setdefault(base_name, []).append(os.path.join(z_stack_dir, file))

        total_images = len(image_groups)
        print(f" [1] Generating maximum intensity projections for {total_images} image stacks...")

        with tqdm(total=total_images, desc="Generating MIP", unit="img") as pbar:
            for base_name, file_list in image_groups.items():
                file_list.sort()
                stack_images = []
                for fp in file_list:
                    img = cv2.imread(fp, cv2.IMREAD_UNCHANGED)
                    if img is None:
                        print(f" Failed to read: {fp}")
                        continue
                    stack_images.append(img)

                if len(stack_images) == 0:
                    print(f" No valid planes found for {base_name}.")
                    pbar.update(1)
                    continue

                stack_images = np.array(stack_images, dtype=np.uint16)
                mip_image = np.max(stack_images, axis=0)
                outp = os.path.join(output_dir_mip16, f"{base_name}_MIP.tiff")
                cv2.imwrite(outp, mip_image)
                pbar.update(1)

        print(f"[1] MIP generation completed. Files saved in: {output_dir_mip16}")


# =======================================================================================
# 2) Convert MIP to 8-bit
# =======================================================================================

if 2 in RUN:
    mip8_existing = any_tiffs_in_dir(output_dir_mip8)

    if SKIP_IF_EXISTS and mip8_existing and not REBUILD_MIP:
        print(f"[2] Skipping MIP (8-bit): already exists in {output_dir_mip8}")
    else:
        image_files = [f for f in os.listdir(output_dir_mip16) if f.lower().endswith(".tiff")]
        print(f" [2] Converting {len(image_files)} MIP images to 8-bit...")

        for image_file in tqdm(image_files, desc="Converting to 8-bit", unit="img"):
            image_path = os.path.join(output_dir_mip16, image_file)
            img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                print(f" Could not read {image_file}, skipping.")
                continue

            p1, p99 = np.percentile(img, (1, 99))
            img_clipped = np.clip(img, p1, p99)
            img_8bit = cv2.normalize(img_clipped, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

            outp = os.path.join(output_dir_mip8, image_file)
            cv2.imwrite(outp, img_8bit)

        print(f"[2] All 8-bit MIP images saved in: {output_dir_mip8}")


# =======================================================================================
# 3) Detect contours on 8-bit
# =======================================================================================

if 3 in RUN:
    contours_existing = any_tiffs_in_dir(contours_dir)

    if SKIP_IF_EXISTS and contours_existing and not REBUILD_MIP:
        print(f"[3] Skipping contours: already exists in {contours_dir}")
    else:
        image_files = [f for f in os.listdir(output_dir_mip8) if f.lower().endswith(".tiff")]
        print(f" [3] Processing {len(image_files)} images to detect spheroid contours...")

        for image_file in tqdm(image_files, desc="Detecting contours", unit="img"):
            image_path = os.path.join(output_dir_mip8, image_file)
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            blurred = cv2.GaussianBlur(img, (5, 5), 0)
            _, binary_otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            kernel = np.ones((3, 3), np.uint8)
            binary_clean = cv2.morphologyEx(binary_otsu, cv2.MORPH_OPEN, kernel, iterations=2)

            contours, _ = cv2.findContours(binary_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            img_contours = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            cv2.drawContours(img_contours, contours, -1, (0, 255, 0), 2)

            outp = os.path.join(contours_dir, image_file)
            cv2.imwrite(outp, img_contours)

        print(f"[3] Contour detection completed. Files saved in: {contours_dir}")


# =======================================================================================
# 4) Show sample of contours
# =======================================================================================

if 4 in RUN:
    if any_tiffs_in_dir(contours_dir):
        show_random_grid(contours_dir, max_images=20, cols=5, title_prefix="")
    else:
        print(" [4] No contour images found to display.")


# =======================================================================================
# 5) Keep only largest object + draw contour
# =======================================================================================

if 5 in RUN:
    spheroids_existing = any_tiffs_in_dir(spheroids_dir)

    if SKIP_IF_EXISTS and spheroids_existing and not REBUILD_MIP:
        print(f"[5] Skipping largest-contour images: already exists in {spheroids_dir}")
    else:
        image_files = [f for f in os.listdir(contours_dir) if f.lower().endswith(".tiff")]
        print(f" [5] Processing {len(image_files)} images to extract the largest spheroid...")

        for image_file in tqdm(image_files, desc="Drawing largest spheroid", unit="img"):
            image_path = os.path.join(contours_dir, image_file)

            img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img_gray is None:
                continue

            img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

            blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)
            _, binary_otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            kernel = np.ones((3, 3), np.uint8)
            binary_clean = cv2.morphologyEx(binary_otsu, cv2.MORPH_OPEN, kernel, iterations=2)

            contours, _ = cv2.findContours(binary_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                largest = max(contours, key=cv2.contourArea)
                cv2.drawContours(img_color, [largest], -1, (0, 255, 0), thickness=2)

                outp = os.path.join(spheroids_dir, image_file)
                cv2.imwrite(outp, img_color)

        print(f"[5] Largest spheroid contours saved in: {spheroids_dir}")


# =======================================================================================
# 6) Show sample of spheroids
# =======================================================================================

if 6 in RUN:
    if any_tiffs_in_dir(spheroids_dir):
        show_random_grid(spheroids_dir, max_images=20, cols=5, title_prefix="")
    else:
        print(" [6] No spheroid images found to display.")


# =======================================================================================
# 7) Feature extraction (Radiomics)
# =======================================================================================

df_features = None

if 7 in RUN:
    if SKIP_IF_EXISTS and os.path.exists(output_excel_path) and not REBUILD_FEATURES:
        print(f"[7] Skipping feature extraction: Excel already exists: {output_excel_path}")
        df_features = pd.read_excel(output_excel_path, engine="openpyxl")
    else:
        extractor = featureextractor.RadiomicsFeatureExtractor()
        extractor.enableAllFeatures()

        image_files = [f for f in os.listdir(spheroids_dir) if f.lower().endswith(".tiff")]
        features_list = []

        print(f" [7] Extracting features from {len(image_files)} images...")
        with tqdm(total=len(image_files), desc="Extracting features", unit="img") as pbar:
            for image_file in image_files:
                image_path = os.path.join(spheroids_dir, image_file)

                img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if img_gray is None:
                    pbar.update(1)
                    continue

                _, binary = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not contours:
                    pbar.update(1)
                    continue

                largest_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(largest_contour)
                perimeter = cv2.arcLength(largest_contour, True)

                circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0
                hull = cv2.convexHull(largest_contour)
                hull_area = cv2.contourArea(hull)
                solidity = area / hull_area if hull_area > 0 else 0

                x, y, w, h = cv2.boundingRect(largest_contour)
                bounding_box_area = w * h
                extent = area / bounding_box_area if bounding_box_area > 0 else 0

                if len(largest_contour) >= 5:
                    ellipse = cv2.fitEllipse(largest_contour)
                    major_axis = max(ellipse[1])
                    minor_axis = min(ellipse[1])
                    aspect_ratio = major_axis / minor_axis if minor_axis > 0 else 0
                else:
                    major_axis = minor_axis = aspect_ratio = 0

                moments = cv2.moments(largest_contour)
                hu_moments = cv2.HuMoments(moments).flatten()

                glcm = graycomatrix(img_gray, [1], [0], 256, symmetric=True, normed=True)
                contrast = graycoprops(glcm, "contrast")[0, 0]
                correlation = graycoprops(glcm, "correlation")[0, 0]
                energy = graycoprops(glcm, "energy")[0, 0]
                homogeneity = graycoprops(glcm, "homogeneity")[0, 0]

                lbp = local_binary_pattern(img_gray, P=8, R=1, method="uniform")
                lbp_hist, _ = np.histogram(lbp.ravel(), bins=np.arange(0, 11), density=True)

                haralick_features = mh.features.haralick(img_gray).mean(axis=0)

                mask = np.zeros_like(img_gray)
                cv2.drawContours(mask, [largest_contour], -1, 1, thickness=cv2.FILLED)

                mask_sitk = sitk.GetImageFromArray(mask.astype(np.uint8))
                img_sitk = sitk.GetImageFromArray(img_gray.astype(np.uint8))

                pyradiomics_features = extractor.execute(img_sitk, mask_sitk)
                pyradiomics_values = list(pyradiomics_features.values())[1:]  # skip first

                features_list.append([
                    image_file, area, perimeter, circularity, solidity, extent,
                    major_axis, minor_axis, aspect_ratio, *hu_moments,
                    contrast, correlation, energy, homogeneity,
                    *lbp_hist, *haralick_features, *pyradiomics_values
                ])

                pbar.update(1)

        # Column names (same as your cleaned script)
        column_names = [
            "Filename", "Area", "Perimeter", "Circularity", "Solidity", "Extent",
            "MajorAxis", "MinorAxis", "AspectRatio",
            "Hu1", "Hu2", "Hu3", "Hu4", "Hu5", "Hu6", "Hu7",
            "GLCM_Contrast", "GLCM_Correlation", "GLCM_Energy", "GLCM_Homogeneity",
            "LBP_0", "LBP_1", "LBP_2", "LBP_3", "LBP_4", "LBP_5", "LBP_6", "LBP_7", "LBP_8", "LBP_9",
            "Haralick_1", "Haralick_2", "Haralick_3", "Haralick_4", "Haralick_5", "Haralick_6",
            "Haralick_7", "Haralick_8", "Haralick_9", "Haralick_10", "Haralick_11", "Haralick_12", "Haralick_13",
        ]
        pyradiomics_column_names = list(pyradiomics_features.keys())[1:]
        column_names.extend(pyradiomics_column_names)

        df_features = pd.DataFrame(features_list, columns=column_names)
        df_features.to_excel(output_excel_path, index=False, engine="openpyxl")
        print(f"[7] Feature table saved to: {output_excel_path}")


# =======================================================================================
# 8) Clustering (PCA + UMAP + KMeans) + save UMAP
# =======================================================================================

df = None

if 8 in RUN:
    clustering_existing = (
        os.path.exists(output_excel_clusters)
        and os.path.exists(umap_png_path)
        and os.path.exists(umap_csv_path)
    )

    if SKIP_IF_EXISTS and clustering_existing and not REBUILD_CLUSTERING:
        print("[8] Skipping clustering: outputs already exist:")
        print(f"   - {output_excel_clusters}")
        print(f"   - {umap_png_path}")
        print(f"   - {umap_csv_path}")
        df = pd.read_excel(output_excel_clusters, engine="openpyxl")
    else:
        # Always cluster from features excel
        df = pd.read_excel(output_excel_path, engine="openpyxl")

        # Drop PyRadiomics 'diagnostics_*' columns: these are metadata (versions, image
        # hash, settings), NOT morphological features, and must not drive the clustering.
        columns_to_exclude = [c for c in df.columns if str(c).startswith("diagnostics_")]
        df_filtered = df.drop(columns=columns_to_exclude, errors="ignore")

        df_numeric = df_filtered.select_dtypes(include=[np.number])
        if df_numeric.shape[1] == 0:
            raise RuntimeError("No numeric columns available for clustering after filtering diagnostics_.")

        # z-score every feature so that features with large numeric ranges (e.g. Area) do
        # not dominate the distance metric over small-range shape descriptors.
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(df_numeric)

        # PCA (20 comps) -> UMAP (2D) -> KMeans: PCA removes correlated noise before the
        # non-linear UMAP embedding; KMeans then splits the embedding into k groups.
        pca = PCA(n_components=args.pca_components)
        data_pca = pca.fit_transform(data_scaled)

        umap_reducer = umap.UMAP(
            n_components=2,
            min_dist=args.umap_min_dist,
            n_neighbors=args.umap_neighbors,
            random_state=args.seed,
        )
        embedding = umap_reducer.fit_transform(data_pca)

        kmeans = KMeans(n_clusters=args.kmeans_k, random_state=args.seed)
        clusters = kmeans.fit_predict(embedding)

        df["UMAP1"] = embedding[:, 0]
        df["UMAP2"] = embedding[:, 1]
        df["cluster"] = clusters

        plt.figure(figsize=(10, 6))
        sc = plt.scatter(df["UMAP1"], df["UMAP2"], c=df["cluster"], cmap="tab10", s=10, alpha=0.7)
        plt.colorbar(sc, label="Cluster")
        plt.xlabel("UMAP 1")
        plt.ylabel("UMAP 2")
        plt.title(f"Clustering PCA + UMAP + KMeans (k={args.kmeans_k})")
        plt.tight_layout()
        plt.savefig(umap_png_path, dpi=300, bbox_inches="tight")
        plt.show()
        print(f"[8] UMAP plot saved to: {umap_png_path}")

        df.to_excel(output_excel_clusters, index=False, engine="openpyxl")
        print(f"[8] Clustering results saved to: {output_excel_clusters}")

        df[["Filename", "UMAP1", "UMAP2", "cluster"]].to_csv(umap_csv_path, index=False)
        print(f"[8] UMAP embedding saved to: {umap_csv_path}")


# =======================================================================================
# 9) Heatmap plate (16x24) + plate map labels
# =======================================================================================

if 9 in RUN:
    # Heatmap skipping depends only on heatmap file existence (NOT on clustering)
    if SKIP_IF_EXISTS and os.path.exists(heatmap_path) and not REBUILD_CLUSTERING:
        print(f"[9] Skipping heatmap: already exists: {heatmap_path}")
    else:
        # ensure df loaded
        if df is None:
            if os.path.exists(output_excel_clusters):
                df = pd.read_excel(output_excel_clusters, engine="openpyxl")
            else:
                raise RuntimeError("Heatmap requires clustering output. Run step 8 first (or include it in --steps).")

        # positions from filename
        df["row"], df["column"] = zip(*df["Filename"].apply(extract_position_from_filename))

        plate_matrix = np.full((16, 24), np.nan)
        for _, r in df.iterrows():
            if r["row"] is None or r["column"] is None:
                continue
            if not (np.isnan(r["row"]) or np.isnan(r["column"])):
                plate_matrix[int(r["row"]), int(r["column"])] = r["cluster"]

        # labels from plate_map.csv
        label_matrix = np.full((16, 24), "", dtype=object)

        if os.path.exists(plate_map_path):
            pm = pd.read_csv(plate_map_path)
            pm["rc"] = pm["rc"].astype(str).str.lower()

            for _, rr in pm.iterrows():
                prow, pcol = rc_to_pos(rr.get("rc", ""))
                if prow is None:
                    continue

                compound = str(rr.get("compound", "")).strip()
                dose = rr.get("dose", "")
                unit = str(rr.get("dose_unit", "")).strip()

                if pd.isna(dose) or dose == "":
                    dose_str = ""
                else:
                    dose_str = fmt_dose_3dp(dose)

                if dose_str and unit:
                    label = f"{compound}\n{dose_str} {unit}"
                elif dose_str:
                    label = f"{compound}\n{dose_str}"
                else:
                    label = f"{compound}"

                label_matrix[prow, pcol] = label
        else:
            print(f" [9] plate_map.csv not found at: {plate_map_path}. Heatmap will be unlabeled.")

        plt.figure(figsize=(16, 10))
        plt.imshow(plate_matrix, cmap="bwr", interpolation="nearest")
        plt.colorbar(label="Cluster")

        plt.xticks(np.arange(24), labels=[f"{c+1}" for c in range(24)], rotation=0)
        plt.yticks(np.arange(16), labels=list("ABCDEFGHIJKLMNOP"))
        plt.title("Cluster Map on the Plate (compound + dose)")
        plt.xlabel("Column")
        plt.ylabel("Row")

        for r in range(16):
            for c in range(24):
                lab = label_matrix[r, c]
                if lab:
                    plt.text(c, r, lab, ha="center", va="center", fontsize=5)

        plt.tight_layout()
        plt.savefig(heatmap_path, dpi=300, bbox_inches="tight")
        plt.show()
        print(f"[9] Heatmap saved to: {heatmap_path}")


# =======================================================================================
# 10) MDC table (per compound) - Morphological Disruption Concentration
#
# RATIONALE / DEFINITION:
#   KMeans (step 8) splits spheroids into two morphological states but does not know which
#   is which. We ANCHOR them biologically: the cluster containing most DMSO (vehicle) wells
#   is the "unaffected" state; the other cluster is the "affected" (disrupted) state.
#   The MDC for a compound is then the LOWEST dose at which ALL 3 within-plate replicate
#   wells fall in the affected cluster - i.e. the lowest concentration that reproducibly
#   disrupts spheroid morphology. Requiring all 3 replicates avoids calling an MDC from a
#   single noisy well.
# =======================================================================================

if 10 in RUN:
    if SKIP_IF_EXISTS and os.path.exists(mdc_out_xlsx) and os.path.exists(mdc_out_csv) and not REBUILD_CLUSTERING:
        print(f"[10] Skipping MDC table: already exists:\n  {mdc_out_xlsx}\n  {mdc_out_csv}")
    else:
        if df is None:
            if os.path.exists(output_excel_clusters):
                df = pd.read_excel(output_excel_clusters, engine="openpyxl")
            else:
                raise RuntimeError("MDC requires clustering output. Run step 8 first (or include it in --steps).")

        if not os.path.exists(plate_map_path):
            print(f"[ERROR] [10] Cannot compute MDC: plate_map.csv not found at: {plate_map_path}")
        else:
            pm = pd.read_csv(plate_map_path)
            pm["rc"] = pm["rc"].astype(str).str.lower()

            df_m = df.copy()
            df_m["rc"] = df_m["Filename"].apply(filename_to_rc)

            merged = df_m.merge(pm, on="rc", how="inner")
            if merged.empty:
                print("[ERROR] [10] MDC: merge produced 0 rows. Check rc mapping between filenames and plate_map.csv")
            else:
                # 1) Anchor: the cluster where most DMSO (vehicle) wells sit = "unaffected".
                #    This gives the otherwise label-free KMeans clusters a biological meaning.
                dmso = merged[merged["compound"].astype(str).str.upper() == "DMSO"]
                if dmso.empty:
                    print("[ERROR] [10] MDC: no DMSO wells found after merge. Check plate_map.csv DMSO entries.")
                else:
                    dmso_counts = dmso["cluster"].value_counts()
                    unaffected_cluster = int(dmso_counts.idxmax())

                    uniq_clusters = sorted({int(x) for x in merged["cluster"].dropna().unique().tolist()})
                    affected_cluster = None
                    for c in uniq_clusters:
                        if c != unaffected_cluster:
                            affected_cluster = c
                            break

                    if affected_cluster is None:
                        print("[ERROR] [10] MDC: only one cluster present; cannot define affected/unaffected.")
                    else:
                        print(f"[10] MDC anchor: unaffected_cluster={unaffected_cluster} (most DMSO), affected_cluster={affected_cluster}")

                        drug_df = merged[merged["control_type"].astype(str).str.lower() == "drug"].copy()
                        drug_df["plate_rep"] = pd.to_numeric(drug_df.get("plate_rep", ""), errors="coerce")
                        drug_df = drug_df[drug_df["plate_rep"].isin([1, 2, 3])]

                        results = []
                        for compound, g in drug_df.groupby("compound"):
                            g = g.copy()
                            g["dose_num"] = pd.to_numeric(g["dose"], errors="coerce")
                            g = g.dropna(subset=["dose_num"])
                            # requested: lowest dose that satisfies condition
                            g = g.sort_values("dose_num", ascending=True)

                            mdc_dose = None
                            mdc_unit = ""

                            # Walk doses from LOW to HIGH; the first dose meeting the
                            # "all 3 replicates affected" criterion is the MDC for that compound.
                            for dose_val, gd in g.groupby("dose_num", sort=False):
                                reps_present = set(gd["plate_rep"].dropna().astype(int).tolist())
                                if reps_present == {1, 2, 3}:
                                    # require all 3 within-plate reps in the affected cluster
                                    byrep = gd.groupby("plate_rep")["cluster"].first()
                                    if (byrep == affected_cluster).all():
                                        mdc_dose = float(dose_val)
                                        mdc_unit = str(gd["dose_unit"].iloc[0]) if "dose_unit" in gd.columns else ""
                                        break

                            results.append({
                                "compound": compound,
                                "MDC_dose": mdc_dose,
                                "dose_unit": mdc_unit,
                                "unaffected_cluster": unaffected_cluster,
                                "affected_cluster": affected_cluster,
                            })

                        mdc_table = pd.DataFrame(results).sort_values(["compound"])
                        mdc_table.to_excel(mdc_out_xlsx, index=False, engine="openpyxl")
                        mdc_table.to_csv(mdc_out_csv, index=False)
                        print(f"[10] MDC table saved to:\n  {mdc_out_xlsx}\n  {mdc_out_csv}")


print("\nPipeline finished.")
print(f"Experiment folder: {base_dir}")
print(f"Plate map used: {plate_map_path}")