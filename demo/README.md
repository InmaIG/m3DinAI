# m3DinAI – Reviewer Demo 

This demo runs an end-to-end m3DinAI pipeline on a small dataset:
feature extraction → table assembly → treatment labeling → UMAP + clustering.

Demo dataset (Zenodo): https://doi.org/10.5281/zenodo.18847934
Download size: ~5 GB (download time depends on network speed).

Note: The demo dataset contains a single cell line (BT549), timepoint 72H, replicate R1.

## Repository layout

* `demo/` : demo scripts and this README
* `demo_data/` : demo dataset will be downloaded here
* `demo_out/` : demo outputs will be written here

## Recommended installation (Conda/Mamba)

From the repository root:

```bash
# optional but recommended (faster solver)
conda install -n base -c conda-forge mamba -y

mamba env create -f environment.yml
conda activate m3dinai_demo
```

## Alternative installation (pip)

Minimal install (no PyRadiomics/SimpleITK):

```bash
python -m pip install -U pip
pip install -r requirements.txt
```

Full install (includes PyRadiomics/SimpleITK; may fail on Windows depending on wheels/compilers):

```bash
pip install -r requirements-full.txt
```

If pip fails installing PyRadiomics/SimpleITK on Windows, use the Conda/Mamba method above.

## 1) Download the demo dataset

This will download and unzip into `./demo_data`:

```bash
python demo/download_demo_data.py
```

Expected dataset structure after unzipping:
`demo_data/72H/R1/<EXPERIMENT>/Images/*.tiff`

## 2) Run the demo

```bash
python demo/run_demo.py
```

## 3) Outputs

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
* If pip install fails for PyRadiomics/SimpleITK on Windows: use Conda/Mamba (`environment.yml`).

## Citation

If you use the demo dataset, please cite:

Iáñez García, I., Ramos, M. C., MARTÍNEZ GARCÍA, M., & FERNANDEZ GODINO, R. (2026).
m3DinAI demo dataset (72H R1; DMSO/MMS/Taxane) [Data set]. Zenodo.
https://doi.org/10.5281/zenodo.18847934

