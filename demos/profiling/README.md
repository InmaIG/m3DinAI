# m3DinAI — Profiling demo (BT549)

This folder contains a runnable demo for the **profiling pipeline** (feature extraction → collection → labeling → UMAP/clustering) on a BT-549 3D spheroid dataset.

For installation (Conda environment) and general usage, see the repository root `README.md`.

Dataset (Zenodo): `10.5281/zenodo.18847934` (~5 GB)
Iáñez García, I., Ramos, M. C., Martínez García, M., & Fernandez Godino, R. (2026). *m3DinAI profiling demo dataset (BT549 72H R1; DMSO/MMS/Taxane)* [Data set]. Zenodo.

## Run the demo (from repo root)

1. Download + extract the dataset:

```bash id="q3mzue"
python demos/profiling/download_profiling_demo_data.py
```

2. Run the profiling demo pipeline:

```bash id="u8k6j8"
python demos/profiling/run_profiling_demo.py --skip-if-exists
```

To force recomputation of all steps:

```bash id="tt0k8e"
python demos/profiling/run_profiling_demo.py --rebuild
```

## Outputs

Outputs are written under:

* `demos/profiling/demo_out/`

Key folders:

* `demos/profiling/demo_out/excels_demo/` (collected feature tables)
* `demos/profiling/demo_out/excels_demo_labeled/` (feature tables with treatment labels)
* `demos/profiling/demo_out/results_demo/` (UMAP/clustering figures and tables)

## Configuration

* `config_profiling_demo.yaml` controls dataset paths, filters, and treatment selection for plots.

Typical settings for this demo:

* timepoint: `72H`
* replicate: `R1`
* experiment name contains: `BT549`
* keep treatments: `DMSO`, `MMS`, `Taxane`

## Notes

* The profiling workflow depends on **PyRadiomics/SimpleITK** for radiomics features; Conda installation is recommended on Windows.
* The runner supports **skip/resume**: steps are skipped if outputs already exist when using `--skip-if-exists`.
