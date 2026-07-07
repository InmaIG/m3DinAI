# m3DinAI — MDC demo (BT549)

This folder contains a runnable demo for the **MDC (Morphological Disruption Concentration)** workflow on a BT-549 3D spheroid dose–response plate.

For installation (Conda environment) and general usage, see the repository root `README.md`.

Dataset (Zenodo): `10.5281/zenodo.18876611` (~648.3 MB)
Iáñez García, I., Ramos, M. C., Martínez García, M., & Fernandez Godino, R. (2026). *m3DinAI MDC demo dataset (BT549; 3D spheroids; dose–response plate; DMSO/MMS + drugs)* [Data set]. Zenodo.

## Run the demo (from repo root)

1. Download + extract the dataset:

```bash
python demos/mdc/download_mdc_demo_data.py
```

2. Run the MDC pipeline:

```bash
python demos/mdc/run_mdc_demo.py
```

The demo uses precomputed projections (no full raw Z-stacks), and the pipeline is configured to **skip steps if outputs already exist**.

## Outputs

Outputs are written into the experiment folder (by default):

* `demos/mdc/demo_mdc_data/BT549_MDC/`

Key expected files:

* `heatmap_cluster_plate_with_doses.png`
* `MDC_table.csv` (or `.xlsx`)
* `umap_kmeans_k2.png` and/or `umap_embedding_kmeans_k2.csv`
* `features_with_kmeans_clusters_full.xlsx`

## Configuration

* `config_mdc_demo.yaml` controls dataset paths and demo settings.
* If your extraction produced a different top-level folder name, adjust `experiment_dir` in `config_mdc_demo.yaml` and rerun the downloader.
