"""
Labels the 'Treatment' column in all Excel files in the specified folder
and saves a copy in a subfolder called 'Excels etiquetados'.

Requirements:
    pip install pandas openpyxl
"""

import re
from pathlib import Path
import pandas as pd

# 1) Folder with the original Excel files
BASE_DIR = Path(r"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D\EXCELS esferas_completo")

# 2) Output folder (created if it doesn't exist)
OUT_DIR = BASE_DIR.parent / "Excels etiquetados"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# --- CLI  ---
import argparse

parser = argparse.ArgumentParser(description="m3DinAI - Label treatments in Excel files")
parser.add_argument("--excels-dir", default=str(BASE_DIR), help="Directory with collected Excel files")
parser.add_argument("--out-labeled-dir", default=str(OUT_DIR), help="Directory to write labeled Excel files")
args, _unknown = parser.parse_known_args()

BASE_DIR = Path(args.excels_dir)
OUT_DIR = Path(args.out_labeled_dir)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 3) Regular expression to extract the column number c##
COL_REGEX = re.compile(r"c(\d{2})", flags=re.IGNORECASE)

def assign_treatment(colnum: int) -> str:
    if   1 <= colnum <= 3:   return "DMSO"
    elif 4 <= colnum <= 9:   return "Anthracyclines"
    elif 10 <= colnum <= 15: return "Topoisomerase inhibitor"
    elif 16 <= colnum <= 21: return "Taxane"
    elif 22 <= colnum <= 24: return "MMS"
    else:                    return "UNKNOWN"

# 4) Process each .xlsx file in the original folder
for excel in BASE_DIR.glob("*.xlsx"):
    print(f"- Processing {excel.name}…")
    df = pd.read_excel(excel, engine="openpyxl")

    # Add / update the "Treatment" column
    df["Treatment"] = (
        df["Filename"].astype(str)
          .str.extract(COL_REGEX)[0]            # column number as string
          .astype(float).astype("Int64")        # tolerates NaN
          .apply(lambda x: assign_treatment(int(x)) if pd.notna(x) else None)
    )

    # Output path: same base name + _trat.xlsx inside OUT_DIR
    out_path = OUT_DIR / f"{excel.stem}_trat.xlsx"
    df.to_excel(out_path, index=False, engine="openpyxl")
    print(f"  ✔ Saved to {out_path}")

print("Completed! All labeled files are in the 'Excels etiquetados' folder.")

