# m3DinAI – Reviewer Demo (UMAP + clustering)

This demo runs an end-to-end m3DinAI pipeline on a small dataset:
feature extraction → table assembly → treatment labeling → UMAP + clustering.

Demo dataset (Zenodo):
https://doi.org/10.5281/zenodo.18847934

## Repository layout

* `demo/` : demo scripts and this README
* `demo_data/` : demo dataset will be downloaded here
* `demo_out/` : demo outputs will be written here

## Requirements

* Python 3.9 recommended (PyRadiomics compatibility)

## 1) Install dependencies

From the repository root:

```bash
pip install -r requirements.txt
pip install pyyaml
```

## 2) Download the demo dataset

This will download (~5 GB) and unzip into `./demo_data`:

```bash
python demo/download_demo_data.py
```

Expected dataset structure after unzipping:
`demo_data/72H/R1/<EXPERIMENT>/Images/*.tiff`

## 3) Run the demo

```bash
python demo/run_demo.py
```

## 4) Outputs

All outputs are written under:
`demo_out/`

Key results folder:
`demo_out/results_demo/`

You should obtain (per experiment/excel processed):

* `*_umap_demo.png`
* `*_umap_demo.csv`

## Troubleshooting

* If download is slow: the dataset is ~5 GB; download time depends on network speed.
* If the pipeline fails with a “path not found” error: run commands from the repository root (the folder containing `demo/`).
* If `pyyaml` is missing: `pip install pyyaml`.

## Citation

If you use the demo dataset, please cite:

Iáñez García, I., Ramos, M. C., MARTÍNEZ GARCÍA, M., & FERNANDEZ GODINO, R. (2026).
m3DinAI demo dataset (72H R1; DMSO/MMS/Taxane) [Data set]. Zenodo.
https://doi.org/10.5281/zenodo.18847934
