# m3DinAI

Custom Python scripts used in the paper **“Label-free morphological profiling of chemotherapy response in 3D breast cancer spheroids”**.
The pipeline implements brightfield HCI preprocessing, segmentation, feature extraction (morphology, texture, and radiomics), dimensionality reduction, clustering, and basic statistics for TNBC spheroids.

> **Python**: 3.9 recommended (especially on Windows, due to PyRadiomics installation constraints).
> **Key libs**: OpenCV, NumPy, scikit-image, Mahotas, PyRadiomics, SimpleITK, scikit-learn, UMAP, matplotlib.
> **Note**: you may see a harmless warning from `umap` about `pkg_resources` deprecation; it does not affect execution.

---

## Reviewer demo (recommended quickstart)

A reviewer-ready demo is provided with a public dataset on Zenodo:

* Demo dataset (Zenodo): https://doi.org/10.5281/zenodo.18847934
  (download size ~5 GB)

From the repository root:

```bash
# optional but recommended (faster solver)
conda install -n base -c conda-forge mamba -y

mamba env create -f environment.yml
conda activate m3dinai_demo

python demo/download_demo_data.py
python demo/run_demo.py
```

Outputs will be written to:

* `demo_out/results_demo/` (UMAP plot(s) and CSV(s))

See `demo/README.md` for details.

---

## Repository structure

```
m3DinAI/
├── scripts/
│   ├── 1_feature_extraction.py
│   ├── 2_copy_excels.py
│   ├── 3_label_treatments.py
│   ├── 4_superclustering_individuals.py
│   ├── 5_superclustering_combined.py
│   ├── 6_violin_plots.py
│   ├── 7_variability_replicates.py
│   └── 8_welch_bonferroni.py
├── demo/
│   ├── config_demo.yaml
│   ├── download_demo_data.py
│   ├── run_demo.py
│   └── README.md
├── environment.yml
├── requirements.txt
├── requirements-full.txt
├── LICENSE
└── CITATION.cff
```

---

## Installation

### Recommended (Windows/Mac/Linux): Conda/Mamba (full pipeline)

```bash
git clone https://github.com/InmaIG/m3DinAI.git
cd m3DinAI

conda install -n base -c conda-forge mamba -y
mamba env create -f environment.yml
conda activate m3dinai_demo
```

### Alternative: pip (best-effort)

Minimal install (no PyRadiomics/SimpleITK; suitable for running downstream steps if you already have feature tables):

```bash
python -m pip install -U pip
pip install -r requirements.txt
```

Full install (includes PyRadiomics/SimpleITK; may fail on Windows depending on wheels/compilers):

```bash
pip install -r requirements-full.txt
```

Note: On Windows, PyRadiomics/SimpleITK installation via pip may fail due to binary wheels/compilation. If that happens, use the Conda/Mamba method above (tested from a clean environment).

---

## Quick check (no data required)

Conda/Mamba environment:

```bash
python -c "import numpy, pandas, cv2, skimage, mahotas, SimpleITK, radiomics, sklearn, umap; print('OK imports')"
```

Pip minimal environment:

```bash
python -c "import numpy, pandas, cv2, skimage, mahotas, sklearn, umap; print('OK imports (minimal)')"
```

---

## Data layout

Raw images are **not** included in this repository. The scripts expect a directory tree per the Methods in the paper (72H/96H/120H × R1/R2/R3 × cell lines):

```
<ROOT_DATA>/
├── 72H/
│   ├── R1/
│   │   ├── BT549_.../
│   │   │   └── Images/            # TIFF Z-stacks
│   │   ├── HCC1806_.../
│   │   └── MDA468_.../
│   └── R2/ ...
├── 96H/ ...
└── 120H/ ...
```

---

## Pipeline (run in order)

All scripts support CLI arguments (portable execution; no hardcoded paths required). Run from the repository root.

1. **Feature extraction** — `scripts/1_feature_extraction.py`

   * Builds **maximum intensity projections** from 16-bit Z-stacks.
   * Converts projections to **8-bit** with percentile clipping.
   * Segments spheroids (Gaussian → Otsu → morphology) and draws contours.
   * Selects largest object per well and extracts:

     * geometric (area, perimeter, circularity, solidity, extent, axes, Hu moments),
     * texture (GLCM, LBP, Haralick),
     * **radiomics** (PyRadiomics on SimpleITK image+mask).
   * Saves `spheroid_features.xlsx` per experiment folder.

   Example:

   ```bash
   python scripts/1_feature_extraction.py --root-dir <ROOT_DATA> --timepoints 72H --replicates R1
   ```

2. **Collect Excel files** — `scripts/2_copy_excels.py`

   * Copies all `spheroid_features.xlsx` into a single output folder.

   Example:

   ```bash
   python scripts/2_copy_excels.py --root-dir <ROOT_DATA> --out-excels-dir <OUT_DIR>/excels
   ```

3. **Label treatments** — `scripts/3_label_treatments.py`

   * Adds a `Treatment` column based on the column number parsed from `Filename` (regex `c##`).
   * Writes labeled files to an output folder.

   Example:

   ```bash
   python scripts/3_label_treatments.py --excels-dir <OUT_DIR>/excels --out-labeled-dir <OUT_DIR>/excels_labeled
   ```

4. **UMAP per replicate** — `scripts/4_superclustering_individuals.py`

   * Per file: outlier filtering **within treatment**, z-score standardization, UMAP, and (optional) clustering.
   * Saves plots/CSVs to the results folder.

   Example:

   ```bash
   python scripts/4_superclustering_individuals.py --labeled-dir <OUT_DIR>/excels_labeled --results-dir <OUT_DIR>/results
   ```

5. **UMAP combined (per cell line)** — `scripts/5_superclustering_combined.py`

6. **Violin plots** — `scripts/6_violin_plots.py`

7. **Replicate variability** — `scripts/7_variability_replicates.py`

8. **Welch t-tests + Bonferroni** — `scripts/8_welch_bonferroni.py`

---

## Notes & tips

* **Reproducibility**: Radiomics can be sensitive to pre-processing; keep SimpleITK datatypes consistent.
* **Performance**: MIP and feature extraction can be I/O-bound; running on SSD reduces disk contention.
* **Quality control**: check contour overlays exported in `Images/4. Spheroids` for segmentation accuracy before downstream analysis.

---

## Citation

If you use this software, please cite the paper and the Zenodo software archive:

- Software (v1.1.0): https://doi.org/10.5281/zenodo.18860886
- Software (all versions / concept DOI): https://doi.org/10.5281/zenodo.17233459

If you use the demo dataset, please cite:
https://doi.org/10.5281/zenodo.18847934

---

## License

This repository is distributed under the terms of the **MIT License**. See the file `LICENSE` for details.

