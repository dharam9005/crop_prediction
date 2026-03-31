"""
schemas.py
----------
Pydantic models (request / response bodies) for the FastAPI endpoints.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ─── Prediction ───────────────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    state_name:    str   = Field(..., example="Karnataka")
    district_name: str   = Field(..., example="BANGALORE")
    crop:          str   = Field(..., example="Rice")
    season:        str   = Field(..., example="Kharif")
    crop_year:     int   = Field(..., ge=1900, le=2100, example=2020)
    area:          float = Field(..., gt=0, example=5000.0,
                                  description="Cultivated area in hectares")


class HistoricalMatch(BaseModel):
    state_name:    str
    district_name: str
    crop:          str
    season:        str
    crop_year:     int
    area:          float
    production:    float

    class Config:
        from_attributes = True


class PredictionResponse(BaseModel):
    id:                      int
    state_name:              str
    district_name:           str
    crop:                    str
    season:                  str
    crop_year:               int
    area:                    float
    predicted_production:    float
    has_historical_match:    bool
    historical_matches:      List[HistoricalMatch]
    created_at:              datetime
    model_version:           str

    class Config:
        from_attributes = True


# ─── Historical ───────────────────────────────────────────────────────────────

class HistoricalRecordOut(BaseModel):
    id:            int
    state_name:    str
    district_name: str
    crop:          str
    season:        str
    crop_year:     int
    area:          float
    production:    float

    class Config:
        from_attributes = True


# ─── Generic ─────────────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    status:  str
    message: str


class ModelInfoResponse(BaseModel):
    mae:        float
    rmse:       float
    r2:         float
    year_range: List[int]
    states:     List[str]
    crops:      List[str]
    seasons:    List[str]
