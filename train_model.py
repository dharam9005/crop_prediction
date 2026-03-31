"""
train_model.py
--------------
Trains a Random Forest model to predict crop production.
Run this SECOND (after data_cleaner.py).

Features used:
  - state_name  (encoded)
  - district_name (encoded)
  - crop         (encoded)
  - season       (encoded)
  - crop_year    (numeric)
  - area         (numeric)

Target:
  - production   (numeric, tonnes / units in dataset)

Usage:
    python train_model.py
"""

import os
import json
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error

CLEAN_PATH = os.path.join("data", "crop_production_clean.csv")
ML_DIR = "ml"

FEATURES = ["state_name", "district_name", "crop", "season", "crop_year", "area"]
TARGET = "production"

CAT_FEATURES = ["state_name", "district_name", "crop", "season"]


def train(clean_path: str = CLEAN_PATH, ml_dir: str = ML_DIR):
    os.makedirs(ml_dir, exist_ok=True)

    # ── Load ──────────────────────────────────────────────────────────────────
    print(f"[1/5] Loading cleaned data from {clean_path}...")
    df = pd.read_csv(clean_path)
    print(f"      Rows: {df.shape[0]:,}")

    # ── Encode categoricals ───────────────────────────────────────────────────
    print("[2/5] Encoding categorical features...")
    encoders: dict[str, LabelEncoder] = {}
    for col in CAT_FEATURES:
        le = LabelEncoder()
        df[col + "_enc"] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    enc_features = [f + "_enc" if f in CAT_FEATURES else f for f in FEATURES]

    X = df[enc_features].values
    y = df[TARGET].values

    # ── Split ─────────────────────────────────────────────────────────────────
    print("[3/5] Splitting into train / test sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"      Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    # ── Train ─────────────────────────────────────────────────────────────────
    print("[4/5] Training RandomForest model (this may take ~30–60 seconds)...")
    model = RandomForestRegressor(
        n_estimators=150,
        max_depth=20,
        min_samples_leaf=5,
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # ── Evaluate ──────────────────────────────────────────────────────────────
    print("[5/5] Evaluating...")
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    print(f"      MAE  : {mae:,.2f}")
    print(f"      RMSE : {rmse:,.2f}")
    print(f"      R²   : {r2:.4f}")

    # ── Save artefacts ────────────────────────────────────────────────────────
    model_path = os.path.join(ml_dir, "model.pkl")
    enc_path = os.path.join(ml_dir, "encoders.pkl")
    meta_path = os.path.join(ml_dir, "metadata.json")

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    with open(enc_path, "wb") as f:
        pickle.dump(encoders, f)

    # Build label maps for easy lookup in the API
    label_maps: dict[str, list[str]] = {
        col: list(le.classes_) for col, le in encoders.items()
    }

    meta = {
        "features": FEATURES,
        "enc_features": enc_features,
        "cat_features": CAT_FEATURES,
        "target": TARGET,
        "label_maps": label_maps,
        "year_range": [int(df["crop_year"].min()), int(df["crop_year"].max())],
        "metrics": {"mae": round(mae, 2), "rmse": round(rmse, 2), "r2": round(r2, 4)},
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅  Model saved  → {model_path}")
    print(f"✅  Encoders saved → {enc_path}")
    print(f"✅  Metadata saved → {meta_path}")
    return model, encoders, meta


if __name__ == "__main__":
    train()
