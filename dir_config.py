"""
dir_config.py
=============
Single source of truth for all file paths used across the pipeline.
Both hemoloop_pipeline.py and simulate_indonesia.py import from here.
"""

import os

# =============================================================================
# BASE DIRECTORIES — only change these two lines
# =============================================================================
DHS_BASE   = "__data__/dhs"
OUTPUT_DIR = "__data__/out"

# =============================================================================
# DHS INPUT FILES — one per country
# Set a value to None to skip that country in the pipeline
# =============================================================================
COUNTRY_FILES = {
    "BD": os.path.join(DHS_BASE, "Bangladesh", "BDIR81DT", "BDIR81FL.DTA"),
    "IN": os.path.join(DHS_BASE, "India",      "IAIR7EDT", "IAIR7EFL.DTA"),
    "ID": os.path.join(DHS_BASE, "Indonesia",  "IDIR71DT", "IDIR71FL.DTA"),
    "NP": os.path.join(DHS_BASE, "Nepal",      "NPIR82DT", "NPIR82FL.DTA"),
    "TL": os.path.join(DHS_BASE, "TimorLeste", "TLIR71DT", "TLIR71FL.DTA"),
}

# =============================================================================
# OUTPUT FILES
# =============================================================================
OUTPUT_CSV_ALL       = os.path.join(OUTPUT_DIR, "dhs_combined_all.csv")
OUTPUT_CSV_COMPLETE  = os.path.join(OUTPUT_DIR, "dhs_combined_complete.csv")
SUMMARY_CSV_ALL      = os.path.join(OUTPUT_DIR, "dhs_summary_all.csv")
SUMMARY_CSV_COMPLETE = os.path.join(OUTPUT_DIR, "dhs_summary_complete.csv")
OUTPUT_ID_SIMULATED      = os.path.join(OUTPUT_DIR, "ID_simulated.csv")
OUTPUT_FINAL_ALL         = os.path.join(OUTPUT_DIR, "hemoloop_final_all.csv")
OUTPUT_FINAL_COMPLETE    = os.path.join(OUTPUT_DIR, "hemoloop_final_complete.csv")