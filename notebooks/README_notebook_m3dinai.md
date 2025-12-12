# m3DinAI

m3DinAI is a Python workflow for morphometric/phenotypic analysis of 3D spheroid images (segmentation, feature extraction, and downstream analysis).

> This repository includes a small synthetic-data notebook to quickly verify the environment and illustrate the analysis flow without requiring real images.

---

## Installation

### 1) Create and activate an environment (recommended)

```bash
python -m venv .venv
# Linux/Mac:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate
```

### 2) Install dependencies

From the repository root:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Tip (Windows): if you run into installation issues with compiled packages, using a conda environment can be easier.

---

## Repository structure

- `src/` — main code
- `notebooks/` — demo notebook(s)
- `requirements.txt` — Python dependencies

---

## Demo notebooks

This folder contains a minimal **demo** for **m3DinAI** that can be run **without real images**.  
Its purpose is to **verify the environment and imports** and to provide a small, self-contained example workflow.

### Files
- **m3DinAI_demo.ipynb** — Self-contained notebook that generates a small synthetic feature table, runs 2D UMAP, and performs a simple Welch’s t-test vs DMSO.

### Prerequisites
- Python (recommended: 3.10–3.11)
- Install dependencies from the project root:
  ```bash
  pip install -r requirements.txt
  ```
- Jupyter:
  ```bash
  python -m pip install jupyter
  ```

### How to run
From the repository root:
```bash
# (optional) create & activate a virtual environment
python -m venv .venv
# Linux/Mac:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

pip install -r requirements.txt
python -m pip install jupyter

# open the demo
jupyter notebook notebooks/m3DinAI_demo.ipynb
```

### What the demo does
- Loads the main scientific stack and m3DinAI dependencies.
- Generates synthetic data to illustrate the workflow.
- Runs dimensionality reduction (UMAP) and a basic statistical comparison (Welch’s t-test).

### Notes
- The notebook may display plots and may write files depending on the execution context (e.g., running from Jupyter vs. nbconvert).
- If you want fully reproducible, fixed output paths, run the notebook from the repository root.

### Troubleshooting
- **`ModuleNotFoundError`** → ensure the environment is active and `pip install -r requirements.txt` completed successfully.
- **Jupyter not found** → `python -m pip install jupyter`
- **UMAP import issues** → `pip install umap-learn==0.5.3`

---

## Citation

If you use this code in academic work, please cite the accompanying publication (add your citation here) and/or the Zenodo record (if available).

---

## License

Add your license information here (e.g., MIT, Apache-2.0), or keep the existing `LICENSE` file as the source of truth.

---

## Contact

Add contact information (name/email) or a link to the Issues page for support.
