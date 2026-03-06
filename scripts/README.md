# Scripts (m3DinAI)

This folder contains the core analysis scripts used by m3DinAI. Scripts are organized into two workflows:

* `scripts/mdc/` — **MDC workflow** (dose–response plates → MDC table)
* `scripts/profiling/` — **Profiling workflow** (feature extraction → labeling → embedding/clustering)

For installation and runnable examples, see the repository root `README.md` and the demo folders under `demos/`.

---

## A) MDC workflow (`scripts/mdc/`)

### Purpose

The MDC workflow is designed for dose–response plates where each compound is tested as an **in-plate triplicate dose series** (three identical curves on the same plate). It produces a plate heatmap and computes **MDC (Minimum Disruptive Concentration)** per compound.

### Main scripts

* `0_mdc_pipeline.py` — runs the full MDC workflow (features → PCA/UMAP → KMeans(k=2) → plate heatmap → MDC table)
* `01_platemap.py` — helper to generate `plate_map.csv` for a given plate layout

### Required inputs (minimum)

* An experiment folder containing:

  * `Images/` (raw z-stacks; can be empty if you provide precomputed projections)
  * `plate_map.csv` (at the same level as `Images/`)

### Typical run

```bash id="1c3m9c"
python scripts/mdc/0_mdc_pipeline.py --z-stack-dir "PATH/TO/EXPERIMENT/Images"
```

---

## B) Profiling workflow (`scripts/profiling/`)

### Purpose

The profiling workflow is used for morphological profiling across experiments (timepoints, replicates, cell lines), producing per-experiment feature tables and downstream UMAP/clustering outputs.

### Main scripts (typical order)

1. `1_feature_extraction.py`

   * builds projections (if needed), converts to 8-bit, segments spheroids, extracts morphology/texture/**radiomics** features
   * writes `spheroid_features.xlsx` per experiment folder

2. `2_copy_excels.py`

   * collects per-experiment `spheroid_features.xlsx` files into a single directory

3. `3_label_treatments.py`

   * adds a `Treatment` column using a plate-specific mapping (you may need to adapt the mapping to your design)

4. `4_superclustering_individuals.py`

   * runs UMAP/clustering per file (per experiment/replicate) and writes plots/tables

Additional downstream scripts:

* `5_superclustering_combined.py` — combined analysis across multiple experiments
* `6_violin_plots.py` — feature distributions per group/treatment
* `7_variability_replicates.py` — replicate variability checks
* `8_welch_bonferroni.py` — statistical testing

### Typical run (from repo root)

```bash id="xwq5m5"
python scripts/profiling/1_feature_extraction.py --root-dir <ROOT_DATA> --timepoints 72H --replicates R1
python scripts/profiling/2_copy_excels.py --root-dir <ROOT_DATA> --out-excels-dir <OUT_DIR>/excels
python scripts/profiling/3_label_treatments.py --excels-dir <OUT_DIR>/excels --out-labeled-dir <OUT_DIR>/excels_labeled
python scripts/profiling/4_superclustering_individuals.py --labeled-dir <OUT_DIR>/excels_labeled --results-dir <OUT_DIR>/results
```

---

## Notes

* Radiomics feature extraction requires **PyRadiomics + SimpleITK**; on Windows, Conda installation is recommended.
* If you modify plate layouts or treatments, ensure `plate_map.csv` (MDC) and treatment mapping (profiling step 3) reflect your experimental design.
