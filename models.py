"""
models.py
---------
SQLAlchemy ORM models for:
  - Prediction  : every prediction made via the API, auto-saved
  - HistoricalRecord : the cleaned training data loaded into SQLite for fast lookup
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean, Text
)
from database import Base


class Prediction(Base):
    """Stores every prediction request + result."""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    # --- inputs ---------------------------------------------------------------
    state_name    = Column(String, nullable=False)
    district_name = Column(String, nullable=False)
    crop          = Column(String, nullable=False)
    season        = Column(String, nullable=False)
    crop_year     = Column(Integer, nullable=False)
    area          = Column(Float, nullable=False)
    # --- outputs --------------------------------------------------------------
    predicted_production = Column(Float, nullable=False)
    # --- provenance -----------------------------------------------------------
    has_historical_match = Column(Boolean, default=False)
    # JSON string: list of matching historical records (or empty list)
    historical_matches_json = Column(Text, default="[]")
    # --- meta -----------------------------------------------------------------
    created_at = Column(DateTime, default=datetime.utcnow)
    model_version = Column(String, default="v1")


class HistoricalRecord(Base):
    """Cleaned training data stored in SQLite for provenance lookups."""
    __tablename__ = "historical_records"

    id            = Column(Integer, primary_key=True, index=True)
    state_name    = Column(String, index=True)
    district_name = Column(String, index=True)
    crop          = Column(String, index=True)
    season        = Column(String, index=True)
    crop_year     = Column(Integer, index=True)
    area          = Column(Float)
    production    = Column(Float)
