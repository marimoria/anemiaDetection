import sys
import os

# Allow imports from project root (dir_config.py lives there, scripts live in analysis/)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pandas as pd

from dir_config import (
    OUTPUT_DIR,
    COUNTRY_FILES,
    OUTPUT_CSV_ALL,
    OUTPUT_CSV_COMPLETE,
    SUMMARY_CSV_ALL,
    SUMMARY_CSV_COMPLETE,
)

# =============================================================================
# CONSTANTS
# =============================================================================
COLUMNS_NEEDED = ["v213", "v453", "v457", "v012", "v201", "v222", "v445", "m45_1"]
FINAL_SCHEMA   = ["patient_id", "country", "v453", "v457", "v012", "v201", "v222", "v445", "m45_1"]


# =============================================================================
# HELPERS
# =============================================================================

def _empty_summary(country, total, note, pregnant=0, valid_hb=0):
    return {
        "country":       country,
        "total_in_file": total,
        "pregnant":      pregnant,
        "valid_hb":      valid_hb,
        "final_rows_all":      0,
        "final_rows_complete": 0,
        "note":          note,
    }


def load_country(country_code, filepath):
    """
    Load one country DTA, filter to pregnant women with valid Hb,
    and clean columns.

    Returns
    -------
    df_all : pd.DataFrame | None
        All rows with valid Hb (NaN allowed in other columns).
    df_complete : pd.DataFrame | None
        Subset where every column has a non-NA value (0 is kept, NA is dropped).
    summary : dict
    """

    print(f"[{country_code}] Loading {filepath} ...")
    df = pd.read_stata(filepath, columns=COLUMNS_NEEDED, convert_categoricals=False)

    total_rows = len(df)
    print(f"[{country_code}] Total rows in file: {total_rows}")

    # --- Filter: currently pregnant only ---
    if "v213" not in df.columns:
        print(f"[{country_code}] WARNING: v213 (currently pregnant) not found. Skipping.")
        return None, None, _empty_summary(country_code, total_rows, "v213 missing")

    df = df[df["v213"] == 1].copy()
    pregnant_count = len(df)
    print(f"[{country_code}] Pregnant women: {pregnant_count}")

    # --- Filter: must have Hb data ---
    if "v453" not in df.columns:
        print(f"[{country_code}] WARNING: v453 (Hb) not found. Skipping.")
        return None, None, _empty_summary(country_code, total_rows, "v453 missing", pregnant_count)

    df = df[df["v453"].notna()].copy()
    # DHS flags missing Hb with codes >= 900 (e.g. 994=not measured, 999=missing)
    df = df[df["v453"] < 900].copy()
    hb_valid_count = len(df)
    print(f"[{country_code}] Pregnant women with valid Hb: {hb_valid_count}")

    if hb_valid_count == 0:
        print(f"[{country_code}] No usable rows after Hb filter. Skipping.")
        return None, None, _empty_summary(
            country_code, total_rows, "No valid Hb after filter", pregnant_count, 0
        )

    # --- Normalize values ---

    # v453: DHS stores as integer tenths (e.g. 112 = 11.2 g/dL)
    df["v453"] = df["v453"] / 10.0

    # v445 (BMI): DHS stores as integer hundredths (e.g. 2150 = 21.50)
    # Codes >= 9000 mean missing/not measured → NA
    if "v445" in df.columns:
        df["v445"] = df["v445"].where(df["v445"] < 9000, other=pd.NA)  # type: ignore
        df["v445"] = df["v445"] / 100.0

    # v222 (birth interval): 0 for first-time mothers (v201 == 0)
    # DHS uses 999 for missing → NA
    if "v222" in df.columns and "v201" in df.columns:
        df["v222"] = df["v222"].where(df["v201"] != 0, other=0)
        df["v222"] = df["v222"].where(df["v222"] < 900, other=pd.NA)  # type: ignore

    # m45_1 (iron tablets): recode to 0/1 only; anything else → NA
    if "m45_1" in df.columns:
        df["m45_1"] = df["m45_1"].where(df["m45_1"].isin([0, 1]), other=pd.NA)  # type: ignore

    # v457 (anemia category): valid codes are 0–3 only; anything else → NA
    if "v457" in df.columns:
        df["v457"] = df["v457"].where(df["v457"].isin([0, 1, 2, 3]), other=pd.NA)  # type: ignore

    # --- Add identifiers ---
    df = df.reset_index(drop=True)
    df["patient_id"] = country_code + "_" + df.index.astype(str).str.zfill(5)
    df["country"]    = country_code

    # Drop filter column, enforce final schema
    df = df.drop(columns=["v213"])
    df = df[FINAL_SCHEMA]

    # --- Split into "all" and "complete" ---
    df_all = df.copy()

    df_complete = df.dropna().copy()
    dropped = len(df_all) - len(df_complete)
    print(
        f"[{country_code}] all={len(df_all)} rows | "
        f"complete={len(df_complete)} rows ({dropped} dropped for NA)"
    )

    summary = {
        "country":             country_code,
        "total_in_file":       total_rows,
        "pregnant":            pregnant_count,
        "valid_hb":            hb_valid_count,
        "final_rows_all":      len(df_all),
        "final_rows_complete": len(df_complete),
        "note":                "OK",
    }

    return (
        df_all      if len(df_all)      > 0 else None,
        df_complete if len(df_complete) > 0 else None,
        summary,
    )


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Resolve to absolute paths so pandas to_csv works regardless of working directory
    output_dir           = os.path.abspath(OUTPUT_DIR)
    out_csv_all          = os.path.abspath(OUTPUT_CSV_ALL)
    out_csv_complete     = os.path.abspath(OUTPUT_CSV_COMPLETE)
    out_summary          = os.path.abspath(SUMMARY_CSV_ALL)
    out_summary_complete = os.path.abspath(SUMMARY_CSV_COMPLETE)

    print(f"Output dir: {output_dir}\n")
    os.makedirs(output_dir, exist_ok=True)

    all_dfs_all      = []
    all_dfs_complete = []
    summaries        = []

    for country_code, filepath in COUNTRY_FILES.items():

        # Skip if explicitly set to None
        if filepath is None:
            print(f"[{country_code}] Skipped — path set to None.")
            summaries.append(_empty_summary(country_code, 0, "Path set to None"))
            continue

        # Skip if parent directory doesn't exist
        if not os.path.isdir(os.path.dirname(filepath)):
            print(f"[{country_code}] Directory not found: {os.path.dirname(filepath)}. Skipping.")
            summaries.append(_empty_summary(country_code, 0, "Directory not found"))
            continue

        # Skip if file doesn't exist
        if not os.path.exists(filepath):
            print(f"[{country_code}] File not found: {filepath}. Skipping.")
            summaries.append(_empty_summary(country_code, 0, "File not found"))
            continue

        df_all, df_complete, summary = load_country(country_code, filepath)
        summaries.append(summary)

        if df_all is not None:
            all_dfs_all.append(df_all)
        if df_complete is not None:
            all_dfs_complete.append(df_complete)

    # --- Combine and save ---
    if not all_dfs_all:
        print("\nNo data loaded. Check your file paths and DHS_BASE.")
        return

    combined_all = pd.concat(all_dfs_all, ignore_index=True)
    combined_all.to_csv(out_csv_all, index=False)
    print(f"\n[all]      Saved: {out_csv_all} ({len(combined_all)} rows)")

    if all_dfs_complete:
        combined_complete = pd.concat(all_dfs_complete, ignore_index=True)
        combined_complete.to_csv(out_csv_complete, index=False)
        print(f"[complete] Saved: {out_csv_complete} ({len(combined_complete)} rows)")
    else:
        print("[complete] No complete rows found across all countries.")

    # --- Save summaries ---
    summary_df = pd.DataFrame(summaries)

    summary_df.to_csv(out_summary, index=False)
    print(f"\n[summary]      Saved: {out_summary}")

    print("\n", summary_df.to_string(index=False))


if __name__ == "__main__":
    main()