# m3DinAI

m3DinAI is a Python workflow used in the paper **“Label-free morphometric profiling reveals early drug responses in 3D tumor spheroids”**. It preprocesses brightfield Z-stacks / projections, segments spheroids, extracts morphology + texture + **radiomics** features, and performs downstream dimensionality reduction (PCA/UMAP), clustering, and statistical analysis.

This repository contains two complementary workflows that are typically used in sequence:

1. **MDC pipeline (dose–response plates)**: estimates a **Morphological Disruption Concentration (MDC)** per compound from in-plate triplicate dose series. MDC is intended as an **upstream screening step** to select a practical working concentration (or concentration range) before running larger profiling experiments.

2. **Profiling pipeline (morphological profiling)**: runs feature extraction and downstream embedding/clustering across experiments (timepoints/replicates/cell lines), typically using the concentration(s) selected from the MDC screening step.


---

## Repository layout

```text
m3DinAI/
├── scripts/
│   ├── mdc/
│   │   ├── 0_mdc_pipeline.py
│   │   └── 01_platemap.py
│   ├── profiling/
│   │   ├── 1_feature_extraction.py
│   │   ├── 2_copy_excels.py
│   │   ├── 3_label_treatments.py
│   │   ├── 4_superclustering_individuals.py
│   │   ├── 5_superclustering_combined.py
│   │   ├── 6_violin_plots.py
│   │   ├── 7_variability_replicates.py
│   │   └── 8_welch_bonferroni.py
│   └── README.md
├── demos/
│   ├── mdc/
│   │   ├── config_mdc_demo.yaml
│   │   ├── download_mdc_demo_data.py
│   │   ├── run_mdc_demo.py
│   │   └── README.md
│   └── profiling/
│       ├── config_profiling_demo.yaml
│       ├── download_profiling_demo_data.py
│       ├── run_profiling_demo.py
│       └── README.md
├── environment.yml
├── requirements.txt
├── requirements-full.txt
├── LICENSE
├── CITATION.cff
└── README.md
```

---

## Installation (Windows-first, recommended)

This project is primarily tested on **Windows**. Linux/macOS may work but have not been systematically validated.

### 1) Clone the repository

```bash
git clone https://github.com/InmaIG/m3DinAI.git
cd m3DinAI
```



### 2) Create and activate the Conda environment (recommended)

m3DinAI depends on **PyRadiomics + SimpleITK**; installation via pip can fail on Windows due to binary wheels/compilation. Conda is the recommended method.

From the repository root:

```bash
conda env create -f environment.yml
conda activate m3dinai
```

If `conda activate` does not work in PowerShell, use **Anaconda Prompt** (recommended for Windows), or run:

```powershell
conda init powershell
```

then open a new terminal.

Optional (faster solver):

```bash
conda install -n base -c conda-forge mamba -y
mamba env create -f environment.yml
conda activate m3dinai
```

### Alternative: pip (best-effort)

Minimal install (no radiomics; suitable only if you already have feature tables):

```bash
python -m pip install -U pip
pip install -r requirements.txt
```



Full install (includes radiomics; **may fail on Windows**):

```bash
pip install -r requirements-full.txt
```



If pip fails installing PyRadiomics/SimpleITK on Windows, use the Conda method above. 

### Quick import check (no data required)

```bash
python -c "import numpy, pandas, cv2, skimage, mahotas, SimpleITK, radiomics, sklearn, umap, yaml; print('OK imports')"
```

---

## Quickstart: run the demos

Run commands from the repository root (`m3DinAI/`).

### A) Profiling demo (end-to-end profiling pipeline)

Dataset (Zenodo): `10.5281/zenodo.18847934` (~5 GB; download time depends on your connection).

1. Download:

```bash
python demos/profiling/download_profiling_demo_data.py
```

2. Run:

```bash
python demos/profiling/run_profiling_demo.py --skip-if-exists
```

To force recomputation:

```bash
python demos/profiling/run_profiling_demo.py --rebuild
```

Outputs are written under:

* `demos/profiling/demo_out/`
* Key folder: `demos/profiling/demo_out/results_demo/`

### B) MDC demo (dose–response plate → MDC table)

Dataset (Zenodo): `10.5281/zenodo.18876611` (~648.3 MB; download time depends on your connection).

The dataset includes `plate_map.csv` plus precomputed projection folders, so the MDC pipeline can skip generating projections when present.

1. Download:

```bash
python demos/mdc/download_mdc_demo_data.py
```

2. Run:

```bash
python demos/mdc/run_mdc_demo.py
```

Internally, the demo runs the MDC pipeline with `--skip-if-exists`.

Expected outputs are written into the experiment folder:

* `demos/mdc/demo_mdc_data/BT549_MDC/`

Key outputs to look for:

* `heatmap_cluster_plate_with_doses.png`
* `MDC_table.csv` (or `.xlsx`)
* `umap_kmeans_k2.png` and/or `umap_embedding_kmeans_k2.csv`
* `features_with_kmeans_clusters_full.xlsx`

---

## Data layout (for running on your own data)

Raw images are not included in this repository. For profiling scripts, the expected directory structure is: timepoint × replicate × experiment folder, where each experiment folder contains an `Images/` directory with TIFF Z-stacks. 

```text
<ROOT_DATA>/
  72H/
    R1/
      BT549_.../
        Images/    # TIFF Z-stacks
      HCC1806_.../
        Images/
    R2/ ...
  96H/ ...
  120H/ ...
```



---

## Using the scripts (beyond demos)

### Profiling pipeline (typical order)

```bash
python scripts/profiling/1_feature_extraction.py --root-dir <ROOT_DATA> --timepoints 72H --replicates R1
python scripts/profiling/2_copy_excels.py --root-dir <ROOT_DATA> --out-excels-dir <OUT_DIR>/excels
python scripts/profiling/3_label_treatments.py --excels-dir <OUT_DIR>/excels --out-labeled-dir <OUT_DIR>/excels_labeled
python scripts/profiling/4_superclustering_individuals.py --labeled-dir <OUT_DIR>/excels_labeled --results-dir <OUT_DIR>/results
```

### MDC pipeline (typical)

The MDC pipeline expects:

* `Images/` folder (may be empty for demos that ship projections)
* `plate_map.csv` at the same level as `Images/`

Run:

```bash
python scripts/mdc/0_mdc_pipeline.py --z-stack-dir "PATH/TO/EXPERIMENT/Images" --skip-if-exists
```

---

## Demo datasets and software DOIs (Zenodo)

* Software release (v1.2.0): `10.5281/zenodo.21256287`
* MDC demo dataset: `10.5281/zenodo.18876611`
* Profiling demo dataset: `10.5281/zenodo.18847934`

---

## License and citation

* License: see `LICENSE`.
* Citation: see `CITATION.cff`.
