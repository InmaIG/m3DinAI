# =======================================================================================
# m3DinAI - Generate the MDC 384-well plate map (dose-response layout)
# File: scripts/mdc/01_platemap.py
#
# Writes plate_map.csv describing the compound and dose assigned to every well of the
# 384-well plate used in the MDC (Morphological Disruption Concentration) assay:
#   * Drug blocks: within-plate triplicate rows, 12-point 1:2 dose series (see BLOCKS).
#   * Controls (rows N-P): DMSO (cols 1-12, negative) and MMS (cols 13-24, positive).
#
# OUTPUT SCHEMA (plate_map.csv) - REQUIRED by 0_mdc_pipeline.py (steps 9-10)
#   well         : well id in A01 format (e.g. "G07")
#   rc           : well id in rXXcYY format (e.g. "r07c07"). *** MUST match the rXXcYY token
#                  embedded in the image filenames ***, because step 10 merges features to
#                  the plate map on this key. This is the critical link between images and doses.
#   row, col     : integer row (1-16) and column (1-24)
#   compound     : compound name (or "DMSO"/"MMS" for the controls)
#   dose         : numeric dose value
#   dose_unit    : units for `dose` (e.g. "uM", "%", "mM")
#   control_type : one of "drug", "negative" (DMSO), "positive" (MMS). Step 10 computes the
#                  MDC only over rows where control_type == "drug".
#   plate_rep    : within-plate replicate index (1/2/3) for drug wells; blank for controls.
#                  Step 10 requires all three replicates (1,2,3) to be affected to call an MDC.
#
# >>> ADAPTING TO A NEW DATASET <<<
#   Everything specific to this experiment lives in the USER CONFIGURATION block below
#   (dose series, compound blocks, control layout, units). Edit those to describe your own
#   plate; the output schema above must be preserved so the downstream pipeline still works.
#   An example output is provided at demos/mdc/plate_map_example.csv.
#
# Usage:
#   python 01_platemap.py --out-dir <OUTPUT_DIR>     ->  writes <out-dir>/plate_map.csv
# =======================================================================================

import argparse
import csv
from pathlib import Path

# 384-well plate: rows A-P (16), cols 1-24
ROWS = list("ABCDEFGHIJKLMNOP")
NROWS = {r: i + 1 for i, r in enumerate(ROWS)}  # A->1 ... P->16


def well_a01(row_letter: str, col: int) -> str:
    return f"{row_letter}{col:02d}"


def rc_r01c01(row_letter: str, col: int) -> str:
    return f"r{NROWS[row_letter]:02d}c{col:02d}"


# ------------------------------------------------------------------------------------
# USER CONFIGURATION (edit everything below for your own plate design)
# ------------------------------------------------------------------------------------
# Dose series (12-point, 1:2 serial dilution) for the left (cols 1-12) and right (cols 13-24) halves
DOSES_LEFT = {
    "GEM":  [100, 50, 25, 12.5, 6.25, 3.125, 1.5625, 0.78125, 0.390625, 0.1953125, 0.09765625, 0.048828125],
    "5-FU": [200, 100, 50, 25, 12.5, 6.25, 3.125, 1.5625, 0.78125, 0.390625, 0.1953125, 0.09765625],
    "DOX":  [250, 125, 62.5, 31.25, 15.625, 7.8125, 3.90625, 1.953125, 0.9765625, 0.48828125, 0.244140625, 0.122070313],
    "VP-16":[110, 55, 27.5, 13.75, 6.875, 3.4375, 1.71875, 0.859375, 0.4296875, 0.21484375, 0.107421875, 0.053710938],
}
DOSES_RIGHT = {
    "VP-16":[50, 25, 12.5, 6.25, 3.125, 1.5625, 0.78125, 0.390625, 0.1953125, 0.09765625, 0.048828125, 0.024414063],
    "CPT":  [10, 5, 2.5, 1.25, 0.625, 0.3125, 0.15625, 0.078125, 0.0390625, 0.01953125, 0.009765625, 0.004882813],
    "DTX":  [1, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625, 0.0078125, 0.00390625, 0.001953125, 0.000976563, 0.000488281],
    "PTX":  [10, 5, 2.5, 1.25, 0.625, 0.3125, 0.15625, 0.078125, 0.0390625, 0.01953125, 0.009765625, 0.004882813],
}

# (compound, triplicate row letters, first col, last col, dose list)
BLOCKS = [
    ("GEM",   ["A", "B", "C"],  1, 12, DOSES_LEFT["GEM"]),
    ("5-FU",  ["D", "E", "F"],  1, 12, DOSES_LEFT["5-FU"]),
    ("DOX",   ["G", "H", "I"],  1, 12, DOSES_LEFT["DOX"]),
    ("VP-16", ["J", "K", "L"],  1, 12, DOSES_LEFT["VP-16"]),
    ("VP-16", ["A", "B", "C"], 13, 24, DOSES_RIGHT["VP-16"]),
    ("CPT",   ["D", "E", "F"], 13, 24, DOSES_RIGHT["CPT"]),
    ("DTX",   ["G", "H", "I"], 13, 24, DOSES_RIGHT["DTX"]),
    ("PTX",   ["J", "K", "L"], 13, 24, DOSES_RIGHT["PTX"]),
]

# End of dose/compound layout.
# Units and control doses
DRUG_DOSE_UNIT = "uM"
DMSO_DOSE = 0.5
DMSO_UNIT = "%"
MMS_DOSE = 4
MMS_UNIT = "mM"


def build_rows():
    rows_out = []
    # Drug wells
    for compound, row_letters, c_start, c_end, doses in BLOCKS:
        cols = list(range(c_start, c_end + 1))
        if len(cols) != len(doses):
            raise ValueError(f"Dose list length mismatch for {compound}: {len(cols)} cols vs {len(doses)} doses")
        for rep_idx, r in enumerate(row_letters, start=1):  # within-plate triplicate
            for col, dose in zip(cols, doses):
                rows_out.append({
                    "well": well_a01(r, col), "rc": rc_r01c01(r, col), "row": r, "col": col,
                    "compound": compound, "dose": dose, "dose_unit": DRUG_DOSE_UNIT,
                    "control_type": "drug", "plate_rep": rep_idx,
                })
    # Controls in rows N-P: DMSO left half (negative), MMS right half (positive)
    control_rows = ["N", "O", "P"]
    for control_row in control_rows:
        for col in range(1, 12 + 1):
            rows_out.append({
                "well": well_a01(control_row, col), "rc": rc_r01c01(control_row, col),
                "row": control_row, "col": col, "compound": "DMSO", "dose": DMSO_DOSE,
                "dose_unit": DMSO_UNIT, "control_type": "negative", "plate_rep": "",
            })
    for control_row in control_rows:
        for col in range(13, 24 + 1):
            rows_out.append({
                "well": well_a01(control_row, col), "rc": rc_r01c01(control_row, col),
                "row": control_row, "col": col, "compound": "MMS", "dose": MMS_DOSE,
                "dose_unit": MMS_UNIT, "control_type": "positive", "plate_rep": "",
            })
    return rows_out


def main():
    ap = argparse.ArgumentParser(description="m3DinAI - generate the MDC 384-well plate map")
    ap.add_argument("--out-dir", required=True, help="Output directory for plate_map.csv")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "plate_map.csv"

    rows_out = build_rows()
    fieldnames = ["well", "rc", "row", "col", "compound", "dose", "dose_unit", "control_type", "plate_rep"]
    rows_out.sort(key=lambda d: (NROWS[d["row"]], d["col"]))
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)
    print(f"Wrote {len(rows_out)} wells to: {out_csv}")


if __name__ == "__main__":
    main()
