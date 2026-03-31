"""
main.py
-------
FastAPI application for Crop Production Prediction.

Endpoints
─────────
POST /predict                      → make a prediction (auto-saved)
GET  /predictions                  → list all saved predictions
GET  /predictions/{id}             → get one prediction by ID
DELETE /predictions/{id}           → delete a prediction

GET  /historical                   → query historical records (filterable)
GET  /historical/{id}              → get one historical record

GET  /model/info                   → model metrics + label options
GET  /options/states               → list all states
GET  /options/districts            → list districts (optionally by state)
GET  /options/crops                → list all crops
GET  /options/seasons              → list all seasons

GET  /health                       → health-check
"""

from __future__ import annotations

import json
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
import schemas
from database import Base, engine, get_db
from predictor import get_meta, predict
from seed_db import seed

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Crop Production Prediction API",
    description=(
        "Predict future crop production using a Random Forest model trained on "
        "Indian agricultural data (1997-2015). Every prediction is auto-saved "
        "and linked to matching historical records so you can see whether the "
        "requested combination existed in the training data."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    """Serve the FarmAI frontend."""
    return FileResponse("static/index.html")


@app.on_event("startup")
def startup():
    """Create tables and seed historical data on first run."""
    Base.metadata.create_all(bind=engine)
    seed()          # no-op if already seeded


# ─────────────────────────────────────────────────────────────────────────────
# Prediction endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post(
    "/predict",
    response_model=schemas.PredictionResponse,
    summary="Make a crop production prediction",
    tags=["Predictions"],
)
def make_prediction(
    req: schemas.PredictionRequest,
    db: Session = Depends(get_db),
):
    """
    Predict **production** (in metric tonnes / dataset units) for the given
    combination of state, district, crop, season, year and cultivated area.

    The response also includes any matching rows from the **historical dataset**
    so you can see whether this combination was observed during training.
    """
    # ── Run model ──────────────────────────────────────────────────────────────
    try:
        predicted = predict(
            state_name    = req.state_name,
            district_name = req.district_name,
            crop          = req.crop,
            season        = req.season,
            crop_year     = req.crop_year,
            area          = req.area,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # ── Historical lookup ──────────────────────────────────────────────────────
    hist_q = (
        db.query(models.HistoricalRecord)
        .filter(
            models.HistoricalRecord.state_name.ilike(req.state_name),
            models.HistoricalRecord.district_name.ilike(req.district_name),
            models.HistoricalRecord.crop.ilike(req.crop),
            models.HistoricalRecord.season.ilike(req.season),
        )
        .all()
    )

    has_match = len(hist_q) > 0
    hist_dicts = [
        {
            "state_name":    r.state_name,
            "district_name": r.district_name,
            "crop":          r.crop,
            "season":        r.season,
            "crop_year":     r.crop_year,
            "area":          r.area,
            "production":    r.production,
        }
        for r in hist_q
    ]

    # ── Persist prediction ────────────────────────────────────────────────────
    db_pred = models.Prediction(
        state_name               = req.state_name,
        district_name            = req.district_name,
        crop                     = req.crop,
        season                   = req.season,
        crop_year                = req.crop_year,
        area                     = req.area,
        predicted_production     = predicted,
        has_historical_match     = has_match,
        historical_matches_json  = json.dumps(hist_dicts),
    )
    db.add(db_pred)
    db.commit()
    db.refresh(db_pred)

    return _pred_to_response(db_pred)


@app.get(
    "/predictions",
    response_model=List[schemas.PredictionResponse],
    summary="List all saved predictions",
    tags=["Predictions"],
)
def list_predictions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    crop: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Return all previously made predictions, newest first. Filterable by crop / state."""
    q = db.query(models.Prediction)
    if crop:
        q = q.filter(models.Prediction.crop.ilike(f"%{crop}%"))
    if state:
        q = q.filter(models.Prediction.state_name.ilike(f"%{state}%"))
    preds = q.order_by(models.Prediction.id.desc()).offset(skip).limit(limit).all()
    return [_pred_to_response(p) for p in preds]


@app.get(
    "/predictions/{prediction_id}",
    response_model=schemas.PredictionResponse,
    summary="Get a single saved prediction",
    tags=["Predictions"],
)
def get_prediction(prediction_id: int, db: Session = Depends(get_db)):
    pred = db.query(models.Prediction).filter(models.Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return _pred_to_response(pred)


@app.delete(
    "/predictions/{prediction_id}",
    response_model=schemas.StatusResponse,
    summary="Delete a saved prediction",
    tags=["Predictions"],
)
def delete_prediction(prediction_id: int, db: Session = Depends(get_db)):
    pred = db.query(models.Prediction).filter(models.Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    db.delete(pred)
    db.commit()
    return {"status": "ok", "message": f"Prediction {prediction_id} deleted."}


# ─────────────────────────────────────────────────────────────────────────────
# Historical data endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get(
    "/historical",
    response_model=List[schemas.HistoricalRecordOut],
    summary="Query historical crop records",
    tags=["Historical Data"],
)
def get_historical(
    state:    Optional[str] = Query(None, description="Filter by state name"),
    district: Optional[str] = Query(None, description="Filter by district name"),
    crop:     Optional[str] = Query(None, description="Filter by crop name"),
    season:   Optional[str] = Query(None, description="Filter by season"),
    year:     Optional[int] = Query(None, description="Filter by crop year"),
    skip:     int = Query(0, ge=0),
    limit:    int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Fetch raw historical records from the training dataset.
    You can filter by any combination of state, district, crop, season, year.
    """
    q = db.query(models.HistoricalRecord)
    if state:
        q = q.filter(models.HistoricalRecord.state_name.ilike(f"%{state}%"))
    if district:
        q = q.filter(models.HistoricalRecord.district_name.ilike(f"%{district}%"))
    if crop:
        q = q.filter(models.HistoricalRecord.crop.ilike(f"%{crop}%"))
    if season:
        q = q.filter(models.HistoricalRecord.season.ilike(f"%{season}%"))
    if year:
        q = q.filter(models.HistoricalRecord.crop_year == year)
    return q.offset(skip).limit(limit).all()


@app.get(
    "/historical/{record_id}",
    response_model=schemas.HistoricalRecordOut,
    summary="Get one historical record by ID",
    tags=["Historical Data"],
)
def get_historical_record(record_id: int, db: Session = Depends(get_db)):
    rec = db.query(models.HistoricalRecord).filter(
        models.HistoricalRecord.id == record_id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Historical record not found")
    return rec


# ─────────────────────────────────────────────────────────────────────────────
# Options / lookup endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get(
    "/options/states",
    response_model=List[str],
    summary="List all available states",
    tags=["Options"],
)
def list_states():
    meta = get_meta()
    return sorted(meta["label_maps"]["state_name"])


@app.get(
    "/options/districts",
    response_model=List[str],
    summary="List districts (optionally filtered by state)",
    tags=["Options"],
)
def list_districts(state: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(models.HistoricalRecord.district_name).distinct()
    if state:
        q = q.filter(models.HistoricalRecord.state_name.ilike(f"%{state}%"))
    return sorted(set(r[0] for r in q.all()))


@app.get(
    "/options/crops",
    response_model=List[str],
    summary="List all available crops",
    tags=["Options"],
)
def list_crops():
    meta = get_meta()
    return sorted(meta["label_maps"]["crop"])


@app.get(
    "/options/seasons",
    response_model=List[str],
    summary="List all seasons",
    tags=["Options"],
)
def list_seasons():
    meta = get_meta()
    return sorted(meta["label_maps"]["season"])


# ─────────────────────────────────────────────────────────────────────────────
# Model info
# ─────────────────────────────────────────────────────────────────────────────

@app.get(
    "/model/info",
    response_model=schemas.ModelInfoResponse,
    summary="Model metrics and available options",
    tags=["Model"],
)
def model_info():
    """Returns accuracy metrics and all available label values for the model."""
    try:
        meta = get_meta()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "mae":        meta["metrics"]["mae"],
        "rmse":       meta["metrics"]["rmse"],
        "r2":         meta["metrics"]["r2"],
        "year_range": meta["year_range"],
        "states":     sorted(meta["label_maps"]["state_name"]),
        "crops":      sorted(meta["label_maps"]["crop"]),
        "seasons":    sorted(meta["label_maps"]["season"]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "message": "Crop Prediction API is running."}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pred_to_response(pred: models.Prediction) -> schemas.PredictionResponse:
    hist = json.loads(pred.historical_matches_json or "[]")
    return schemas.PredictionResponse(
        id                    = pred.id,
        state_name            = pred.state_name,
        district_name         = pred.district_name,
        crop                  = pred.crop,
        season                = pred.season,
        crop_year             = pred.crop_year,
        area                  = pred.area,
        predicted_production  = pred.predicted_production,
        has_historical_match  = pred.has_historical_match,
        historical_matches    = [schemas.HistoricalMatch(**h) for h in hist],
        created_at            = pred.created_at,
        model_version         = pred.model_version,
    )
