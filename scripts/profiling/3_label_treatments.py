# =======================================================================================
# m3DinAI - Label the 'Treatment' column from the plate layout
# File: scripts/profiling/3_label_treatments.py
#
# WHAT THIS DOES
#   Reads every feature Excel in --excels-dir, derives each spheroid's Treatment from the
#   plate COLUMN encoded in its image filename (…c##…), and writes a labelled copy
#   (<name>_trat.xlsx) into --out-labeled-dir. The Treatment column is what all downstream
#   analyses (UMAP, violins, Activity Ratio) group by.
#
# HOW THE TREATMENT IS DECIDED
#   Filenames follow the Opera/Harmony convention rXXcYYfZZ, where cYY is the plate column.
#   In this study each block of columns holds one treatment class (see COLUMN_TREATMENT_MAP).
#
# >>> ADAPTING TO A NEW DATASET <<<
#   This column->treatment layout is the ONLY dataset-specific parameter here. Edit
#   COLUMN_TREATMENT_MAP below to match your own plate design: each entry is
#   (first_column, last_column, "Treatment label"), inclusive, 1-based. Columns not covered
#   by any range are labelled "UNKNOWN".
# =======================================================================================

import argparse
import re
from pathlib import Path
import pandas as pd

# ------------------------------------------------------------------------------------
# USER CONFIGURATION - plate layout for THIS study (edit for your own plate design)
#
#   Columns 1-3  : DMSO (vehicle / negative control)
#   Columns 4-9  : Anthracyclines          (4-6 Doxorubicin, 7-9 Epirubicin)
#   Columns 10-15: Topoisomerase inhibitor (10-12 Etoposide, 13-15 Camptothecin)
#   Columns 16-21: Taxane                  (16-18 Docetaxel, 19-21 Paclitaxel)
#   Columns 22-24: MMS (positive / maximal-disruption control)
#
# Each tuple is (first_col, last_col, label), inclusive and 1-based.
# ------------------------------------------------------------------------------------
COLUMN_TREATMENT_MAP = [
    (1, 3, "DMSO"),
    (4, 9, "Anthracyclines"),
    (10, 15, "Topoisomerase inhibitor"),
    (16, 21, "Taxane"),
    (22, 24, "MMS"),
]

# Regex to pull the column number (c##) out of the image filename
COL_REGEX = re.compile(r"c(\d{2})", flags=re.IGNORECASE)


def assign_treatment(colnum: int) -> str:
    """Map a 1-based plate column to its Treatment label using COLUMN_TREATMENT_MAP."""
    for first, last, label in COLUMN_TREATMENT_MAP:
        if first <= colnum <= last:
            return label
    return "UNKNOWN"


def main():
    ap = argparse.ArgumentParser(description="m3DinAI - label treatments from plate column")
    ap.add_argument("--excels-dir", required=True, help="Directory with the feature Excel files")
    ap.add_argument("--out-labeled-dir", default=None,
                    help="Directory to write labelled files (default: <excels-dir>/Excels etiquetados)")
    args = ap.parse_args()

    base_dir = Path(args.excels_dir)
    out_dir = Path(args.out_labeled_dir) if args.out_labeled_dir else base_dir.parent / "Excels etiquetados"
    out_dir.mkdir(parents=True, exist_ok=True)

    for excel in base_dir.glob("*.xlsx"):
        print(f"- Processing {excel.name} ...")
        df = pd.read_excel(excel, engine="openpyxl")

        # Extract the column number from each Filename and map it to a Treatment label.
        # (Int64 tolerates missing/invalid filenames -> those rows get Treatment = None.)
        df["Treatment"] = (
            df["Filename"].astype(str)
              .str.extract(COL_REGEX)[0]
              .astype(float).astype("Int64")
              .apply(lambda x: assign_treatment(int(x)) if pd.notna(x) else None)
        )

        out_path = out_dir / f"{excel.stem}_trat.xlsx"
        df.to_excel(out_path, index=False, engine="openpyxl")
        print(f"  Saved to {out_path}")

    print(f"Completed. Labelled files are in: {out_dir}")


if __name__ == "__main__":
    main()
