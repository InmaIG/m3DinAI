# =======================================================================================
# m3DinAI - Activity Ratio (AR) computation
# File: scripts/profiling/8_activity_ratio.py
#
# PURPOSE
# -------
# Formalises the Activity Ratio (AR) metric described in the manuscript (Eq. 1).
# For each spheroid, all morphological features are z-score standardised (per
# experiment/plate). The DMSO and MMS control centroids are computed as the mean
# feature vector of their respective control wells. The AR of a spheroid is then
# defined from its Euclidean distances (d) to each centroid:
#
#       AR = 100 * d_DMSO / (d_DMSO + d_MMS)
#
# so that AR ~ 0 for spheroids resembling the DMSO (intact) phenotype and AR ~ 100
# for spheroids resembling the MMS (fully disrupted) phenotype. Higher AR = lower
# similarity to DMSO / higher similarity to MMS.
#
# This produces the per-spheroid AR that was previously missing from the repository,
# and writes a `<experiment>_variation_summary.csv` (with a per-spheroid `MeanRatio`
# column) that is directly consumable by `9_welch_bonferroni.py`. Because the AR is
# now reported per spheroid rather than aggregated to one value per replicate, the
# downstream statistics are no longer limited to n = 3.
#
# INPUT
# -----
# One or more labelled feature Excel files (output of 3_label_treatments.py), i.e.
# tables containing a `Filename` column, a `Treatment` column, and the numeric
# morphological feature columns. File names are expected to encode cell line,
# replicate and timepoint, e.g. `BT549_R1_72H_spheroid_features_trat.xlsx`.
#
# OUTPUT (per input file, written to --out-dir)
# ---------------------------------------------
#   <stem>_AR_per_spheroid.csv   -> Filename, rc, CellLine, Replicate, Time,
#                                    Treatment, AR, d_DMSO, d_MMS
#   <stem>_variation_summary.csv -> CellLine, Replicate, Time, Treatment, MeanRatio
#                                    (MeanRatio = per-spheroid AR; compatible w/ script 8)
#
# NOTES
# -----
# * By default the DMSO/MMS centroids and the z-scoring are computed WITHIN each
#   input file (i.e. per plate), which is the biologically correct anchoring because
#   each plate carries its own controls. Use --pooled to instead z-score/anchor across
#   all input files jointly (not recommended unless plates are highly comparable).
# * The same `diagnostics_*` PyRadiomics columns excluded in the clustering step are
#   excluded here as well.
# * Outlier handling mirrors the clustering scripts (median +/- 3 SD per treatment),
#   but is OPTIONAL here and OFF by default so that AR is reported for every spheroid.
# =======================================================================================

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------------------
# Filename / metadata helpers
# ---------------------------------------------------------------------------------------

FNAME_META = re.compile(r"(BT549|HCC1806|MDA468)_R(\d)_(\d{2,3}H)", flags=re.IGNORECASE)
RC_REGEX = re.compile(r"r(\d{2})c(\d{2})", flags=re.IGNORECASE)


def parse_file_metadata(stem: str):
    """Extract (CellLine, Replicate, Time) from a file stem, or (None, None, None)."""
    m = FNAME_META.search(stem)
    if not m:
        return None, None, None
    line, rep, time = m.groups()
    return line.upper(), f"R{rep}", time.upper()


def filename_to_rc(fn: str) -> str:
    """Normalise a well identifier from an image filename to 'rXXcYY'."""
    m = RC_REGEX.search(str(fn))
    if not m:
        return ""
    return f"r{int(m.group(1)):02d}c{int(m.group(2)):02d}".lower()


# ---------------------------------------------------------------------------------------
# Core AR computation
# ---------------------------------------------------------------------------------------

def numeric_feature_columns(df: pd.DataFrame) -> list:
    """Numeric feature columns, excluding PyRadiomics diagnostics_* and helper columns."""
    helper = {"row", "column", "col", "UMAP1", "UMAP2", "cluster", "plate_rep"}
    cols = []
    for c in df.columns:
        if str(c).startswith("diagnostics_"):
            continue
        if str(c) in helper:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            cols.append(str(c))
    return cols


def remove_outliers_by_treatment(df: pd.DataFrame, feat_cols: list,
                                 treat_col: str, k: float = 3.0) -> pd.DataFrame:
    """Median +/- k*SD per treatment, requiring ALL features within range (as in scripts 4/5)."""
    keep_idx = []
    for _, g in df.groupby(treat_col):
        sub = g[feat_cols]
        med = sub.median()
        sd = sub.std(ddof=1)
        lower, upper = med - k * sd, med + k * sd
        mask = ((sub >= lower) & (sub <= upper)).all(axis=1)
        keep_idx.extend(g.index[mask].tolist())
    return df.loc[sorted(keep_idx)].copy()


def zscore(df_feats: pd.DataFrame) -> pd.DataFrame:
    """Column-wise z-score standardisation (population-style, matching StandardScaler)."""
    mu = df_feats.mean(axis=0)
    sd = df_feats.std(axis=0, ddof=0)
    sd_safe = sd.replace(0, np.nan)  # avoid divide-by-zero for constant features
    z = (df_feats - mu) / sd_safe
    return z.fillna(0.0)  # constant features contribute 0 to distances


def compute_ar_for_frame(df: pd.DataFrame,
                         treat_col: str = "Treatment",
                         dmso_label: str = "DMSO",
                         mms_label: str = "MMS") -> pd.DataFrame:
    """Return df with added columns d_DMSO, d_MMS, AR. z-scoring is done on the frame given."""
    feat_cols = numeric_feature_columns(df)
    if not feat_cols:
        raise RuntimeError("No numeric feature columns found.")

    z = zscore(df[feat_cols].astype(float))

    dmso_mask = df[treat_col].astype(str).str.upper() == dmso_label.upper()
    mms_mask = df[treat_col].astype(str).str.upper() == mms_label.upper()
    if dmso_mask.sum() == 0 or mms_mask.sum() == 0:
        raise RuntimeError(
            f"Need both {dmso_label} and {mms_label} wells to anchor AR "
            f"(found DMSO={int(dmso_mask.sum())}, MMS={int(mms_mask.sum())})."
        )

    c_dmso = z[dmso_mask.values].mean(axis=0).values
    c_mms = z[mms_mask.values].mean(axis=0).values

    Z = z.values
    d_dmso = np.linalg.norm(Z - c_dmso, axis=1)
    d_mms = np.linalg.norm(Z - c_mms, axis=1)

    denom = d_dmso + d_mms
    with np.errstate(divide="ignore", invalid="ignore"):
        ar = np.where(denom > 0, 100.0 * d_dmso / denom, np.nan)

    out = df.copy()
    out["d_DMSO"] = d_dmso
    out["d_MMS"] = d_mms
    out["AR"] = ar
    return out


# ---------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="m3DinAI - Activity Ratio (AR) computation (Eq. 1)")
    p.add_argument("--labeled-dir", required=True,
                   help="Directory with labelled feature Excel files (output of 3_label_treatments.py)")
    p.add_argument("--out-dir", required=True, help="Directory to write AR CSV outputs")
    p.add_argument("--treatment-col", default="Treatment")
    p.add_argument("--dmso-label", default="DMSO")
    p.add_argument("--mms-label", default="MMS")
    p.add_argument("--drop-outliers", action="store_true",
                   help="Apply median +/- 3 SD per-treatment outlier removal before AR (default: off)")
    p.add_argument("--pooled", action="store_true",
                   help="z-score and anchor centroids across ALL files jointly (default: per file)")
    return p.parse_args()


def process_frame(df: pd.DataFrame, stem: str, args, out_dir: Path):
    line, rep, time = parse_file_metadata(stem)
    if args.drop_outliers:
        feat_cols = numeric_feature_columns(df)
        df = remove_outliers_by_treatment(df, feat_cols, args.treatment_col)

    res = compute_ar_for_frame(df, args.treatment_col, args.dmso_label, args.mms_label)

    res["rc"] = res["Filename"].apply(filename_to_rc) if "Filename" in res.columns else ""
    res["CellLine"] = line
    res["Replicate"] = rep
    res["Time"] = time

    per_sph_cols = ["Filename", "rc", "CellLine", "Replicate", "Time",
                    args.treatment_col, "AR", "d_DMSO", "d_MMS"]
    per_sph = res[[c for c in per_sph_cols if c in res.columns]].copy()
    per_sph.to_csv(out_dir / f"{stem}_AR_per_spheroid.csv", index=False)

    # variation_summary.csv compatible with 9_welch_bonferroni.py (per-spheroid MeanRatio)
    summ = per_sph.rename(columns={"AR": "MeanRatio"})[
        ["CellLine", "Replicate", "Time", args.treatment_col, "MeanRatio"]
    ]
    summ.to_csv(out_dir / f"{stem}_variation_summary.csv", index=False)

    print(f"  [OK] {stem}: n={len(per_sph)} spheroids, "
          f"AR mean={per_sph['AR'].mean():.1f} (line={line}, rep={rep}, time={time})")
    return res


def main():
    args = parse_args()
    labeled_dir = Path(args.labeled_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(labeled_dir.glob("*.xlsx"))
    if not files:
        raise SystemExit(f"No .xlsx files found in {labeled_dir}")

    print(f"Found {len(files)} labelled feature file(s).")

    if args.pooled:
        frames = []
        for f in files:
            df = pd.read_excel(f, engine="openpyxl")
            line, rep, time = parse_file_metadata(f.stem)
            df["__stem__"] = f.stem
            df["CellLine"], df["Replicate"], df["Time"] = line, rep, time
            frames.append(df)
        big = pd.concat(frames, ignore_index=True)
        if args.drop_outliers:
            feat_cols = numeric_feature_columns(big)
            big = remove_outliers_by_treatment(big, feat_cols, args.treatment_col)
        res = compute_ar_for_frame(big, args.treatment_col, args.dmso_label, args.mms_label)
        res["rc"] = res["Filename"].apply(filename_to_rc) if "Filename" in res.columns else ""
        for stem, g in res.groupby("__stem__"):
            per = g[["Filename", "rc", "CellLine", "Replicate", "Time",
                     args.treatment_col, "AR", "d_DMSO", "d_MMS"]]
            per.to_csv(out_dir / f"{stem}_AR_per_spheroid.csv", index=False)
            per.rename(columns={"AR": "MeanRatio"})[
                ["CellLine", "Replicate", "Time", args.treatment_col, "MeanRatio"]
            ].to_csv(out_dir / f"{stem}_variation_summary.csv", index=False)
            print(f"  [OK] {stem}: n={len(per)} spheroids (pooled anchoring)")
    else:
        for f in files:
            df = pd.read_excel(f, engine="openpyxl")
            try:
                process_frame(df, f.stem, args, out_dir)
            except Exception as e:
                print(f"  [SKIP] {f.name}: {e}")

    print(f"\nDone. AR outputs written to: {out_dir}")


if __name__ == "__main__":
    main()
