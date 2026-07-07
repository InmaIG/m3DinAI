# Changelog — code documentation & reproducibility

This update improves the documentation and reproducibility of the code without changing any
analytical logic: it adds inline documentation, exposes dataset-specific values as editable
configuration, removes hardcoded paths, and unifies the comments to English.

## 1. Removed hardcoded file paths
All scripts now take input/output locations as command-line arguments; no dataset-specific
absolute path (e.g. `Y:\...`) remains in the code. Scripts that previously had none were
given an `argparse` interface: `mdc/01_platemap.py`, `profiling/5_superclustering_combined.py`,
`profiling/6_violin_plots.py`, `profiling/7_variability_replicates.py`, and the Activity-Ratio
statistics script.

## 2. Generalised experiment-specific labels (USER CONFIGURATION blocks)
The values specific to this study are now collected in clearly marked, documented
`USER CONFIGURATION` blocks (and/or CLI flags):

- Cell-line tags, timepoints and replicates (`1_feature_extraction.py`, `2_copy_excels.py`).
- **Plate column → treatment mapping** (`3_label_treatments.py`): now a documented
  `COLUMN_TREATMENT_MAP` that a new user edits for their own plate.
- Dose series / compound blocks / controls (`mdc/01_platemap.py`).

A new section, *"Adapting m3DinAI to your own dataset"*, was added to `scripts/README.md`.

## 3. Documented the plate-map schema and added an example
`mdc/01_platemap.py` now documents the full output schema of `plate_map.csv` (including that
the `rc` = rXXcYY key must match the image filenames, which is how features are joined to
doses in step 10). An example file is provided at `demos/mdc/plate_map_example.csv`.

## 4. Added inline comments explaining the analytical logic
Rationale and parameter/threshold explanations were added throughout the scientific steps so
that the implementation can be checked against the manuscript:

- **Segmentation** (`1_feature_extraction.py`, `mdc/0_mdc_pipeline.py`): why 1–99th percentile
  clipping for 8-bit conversion; why Gaussian blur + Otsu `THRESH_BINARY_INV` (spheroids are
  darker than background) + morphological opening; why the largest external contour is kept
  (one-spheroid-per-well assumption).
- **Feature families** (`1_feature_extraction.py`): what the shape descriptors, GLCM/LBP/Haralick
  texture features and PyRadiomics set capture; note that `diagnostics_*` columns are metadata,
  not features, and are excluded downstream.
- **Embedding & clustering** (`0_mdc_pipeline.py`, `4_*`, `5_*`): why features are z-scored,
  the role of PCA before UMAP, the meaning of `n_neighbors`/`min_dist`/`random_state`, that
  UMAP is non-metric, and why Ward clustering / KMeans `k=2`.
- **MDC definition** (`0_mdc_pipeline.py`, step 10): how KMeans clusters are anchored to DMSO
  ("unaffected" = cluster with most DMSO wells), and that the MDC is the lowest dose at which
  all three within-plate replicates fall in the affected cluster.
- **Activity Ratio & statistics** (`8_activity_ratio.py`, `9_welch_bonferroni.py`): Eq. (1)
  and the rationale for Welch's t-test + Bonferroni.

## 5. Language consistency
All comments and console messages were reviewed and unified to English; non-ASCII emoji were
removed from print statements to avoid encoding issues on Windows consoles.

## 6. Added the missing Activity Ratio script and fixed script order
The per-spheroid Activity Ratio computation (manuscript Eq. 1), previously absent from the
repository, was added as `profiling/8_activity_ratio.py`. Because it produces the
`*_variation_summary.csv` consumed by the statistics script, the two were renumbered so that
execution order matches numbering: `8_activity_ratio.py` → `9_welch_bonferroni.py`.

## 7. Repository-wide consistency pass
Beyond `scripts/`, the rest of the repository was reviewed against the same criteria:

- **Demo scripts** (`demos/mdc/`, `demos/profiling/`): added module docstrings describing
  what each downloader/runner does and how to use it; removed emoji from console output.
- **Demo configs**: documented `config_profiling_demo.yaml` (was undocumented, with a stale
  header path) and aligned the documented PCA components in `config_mdc_demo.yaml` with the
  pipeline default.
- **Terminology**: unified the meaning of "MDC" to *Morphological Disruption Concentration*
  across all READMEs and code (previously mixed with "Minimum Disruptive Concentration").
- Confirmed there are no remaining hardcoded absolute paths, and no Spanish comments or
  emoji anywhere in the `.py`, `.md` or `.yaml` files.

