"""
predictor.py
------------
Singleton that loads the trained model + encoders once and exposes a
predict() function used by the FastAPI routes.
"""

from __future__ import annotations

import gzip
import json
import os
import pickle
from typing import Any

import numpy as np

ML_DIR = "ml"

_model = None
_encoders = None
_meta = None


def _load() -> tuple[Any, dict, dict]:
    global _model, _encoders, _meta
    if _model is None:
        model_path_gz = os.path.join(ML_DIR, "model.pkl.gz")
        model_path    = os.path.join(ML_DIR, "model.pkl")
        enc_path      = os.path.join(ML_DIR, "encoders.pkl")
        meta_path     = os.path.join(ML_DIR, "metadata.json")

        if not os.path.exists(enc_path) or not os.path.exists(meta_path):
            raise FileNotFoundError(
                "Model files not found. Run `python train_model.py` first."
            )
        if not os.path.exists(model_path_gz) and not os.path.exists(model_path):
            raise FileNotFoundError(
                "Model files not found. Run `python train_model.py` first."
            )

        if os.path.exists(model_path_gz):
            with gzip.open(model_path_gz, "rb") as f:
                _model = pickle.load(f)
        else:
            with open(model_path, "rb") as f:
                _model = pickle.load(f)
        with open(enc_path, "rb") as f:
            _encoders = pickle.load(f)
        with open(meta_path) as f:
            _meta = json.load(f)

    return _model, _encoders, _meta


def get_meta() -> dict:
    _, _, meta = _load()
    return meta


def _safe_encode(encoder, value: str) -> int:
    """Encode a value; if unseen, return -1 (RF handles it gracefully)."""
    try:
        return int(encoder.transform([value])[0])
    except ValueError:
        # Use the most frequent class index (0) as fallback
        return 0


def predict(
    state_name:    str,
    district_name: str,
    crop:          str,
    season:        str,
    crop_year:     int,
    area:          float,
) -> float:
    """Return the predicted production (float)."""
    model, encoders, meta = _load()

    cat_features = meta["cat_features"]
    inputs = {
        "state_name":    state_name.strip(),
        "district_name": district_name.strip().upper(),
        "crop":          crop.strip(),
        "season":        season.strip(),
        "crop_year":     crop_year,
        "area":          area,
    }

    row = []
    for feat in meta["features"]:
        if feat in cat_features:
            encoded = _safe_encode(encoders[feat], inputs[feat])
            row.append(encoded)
        else:
            row.append(inputs[feat])

    X = np.array(row, dtype=float).reshape(1, -1)
    prediction = float(model.predict(X)[0])
    return max(prediction, 0.0)   # production can't be negative
