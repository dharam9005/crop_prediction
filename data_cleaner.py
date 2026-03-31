"""
data_cleaner.py
---------------
Cleans the raw crop production CSV and saves a cleaned version.
Run this FIRST before training.

Usage:
    python data_cleaner.py
"""

import pandas as pd
import numpy as np
import os

RAW_PATH = os.path.join("data", "crop_production.csv")
CLEAN_PATH = os.path.join("data", "crop_production_clean.csv")


def clean_data(raw_path: str = RAW_PATH, clean_path: str = CLEAN_PATH) -> pd.DataFrame:
    print(f"[1/6] Loading data from: {raw_path}")
    df = pd.read_csv(raw_path)
    print(f"      Original shape: {df.shape}")

    # ── Step 1: Strip whitespace from all string columns ──────────────────────
    print("[2/6] Stripping whitespace from string columns...")
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        df[col] = df[col].str.strip()

    # ── Step 2: Standardise column names ─────────────────────────────────────
    print("[3/6] Standardising column names...")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    # Expected: state_name, district_name, crop_year, season, crop, area, production

    # ── Step 3: Handle missing Production values ──────────────────────────────
    print("[4/6] Handling missing production values...")
    missing_before = df["production"].isna().sum()
    print(f"      Missing production rows: {missing_before}")

    # Fill missing production using median by (crop, season, state_name)
    df["production"] = df.groupby(["crop", "season", "state_name"])["production"].transform(
        lambda x: x.fillna(x.median())
    )
    # If still NaN (whole group was NaN), fill with global crop median
    df["production"] = df.groupby("crop")["production"].transform(
        lambda x: x.fillna(x.median())
    )
    # Final fallback
    df["production"] = df["production"].fillna(df["production"].median())
    missing_after = df["production"].isna().sum()
    print(f"      Missing production after fill: {missing_after}")

    # ── Step 4: Remove duplicate rows ─────────────────────────────────────────
    print("[5/6] Removing duplicate rows...")
    dup_count = df.duplicated().sum()
    df.drop_duplicates(inplace=True)
    print(f"      Duplicates removed: {dup_count}")

    # ── Step 5: Remove rows with non-positive Area ────────────────────────────
    negative_area = (df["area"] <= 0).sum()
    df = df[df["area"] > 0]
    print(f"      Rows with non-positive area removed: {negative_area}")

    # ── Step 6: Save ──────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(clean_path), exist_ok=True)
    df.to_csv(clean_path, index=False)
    print(f"[6/6] Cleaned data saved to: {clean_path}")
    print(f"      Final shape: {df.shape}")
    return df


if __name__ == "__main__":
    clean_data()
