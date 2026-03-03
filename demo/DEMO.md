# m3DinAI – Reviewer Demo (UMAP + clustering)

This demo runs an end-to-end m3DinAI pipeline on a small dataset:
feature extraction → table assembly → treatment labeling → UMAP + clustering.
Download is ~5 GB and may take several minutes depending on network.

Demo dataset (Zenodo):
https://doi.org/10.5281/zenodo.18847934

## Requirements
- Python 3.9 recommended (PyRadiomics compatibility)
- Install dependencies from this repository

## 1) Install
From the repository root:

```bash
pip install -r requirements.txt
pip install pyyaml