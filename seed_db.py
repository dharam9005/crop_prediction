"""
seed_db.py
----------
Reads the cleaned CSV and bulk-inserts all records into the
`historical_records` SQLite table using csv module (no pandas needed).

Usage:
    python seed_db.py
"""

import csv
import os
from sqlalchemy.orm import Session

from database import engine, SessionLocal, Base
import models   # noqa – registers all ORM classes with Base

CLEAN_PATH = os.path.join("data", "crop_production_clean.csv")
BATCH_SIZE = 5_000


def seed(clean_path: str = CLEAN_PATH):
    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    # Skip if already seeded
    existing = db.query(models.HistoricalRecord).count()
    if existing > 0:
        print(f"Historical data already seeded ({existing:,} rows). Skipping.")
        db.close()
        return

    if not os.path.exists(clean_path):
        print(f"Warning: {clean_path} not found. Skipping seed.")
        db.close()
        return

    print(f"Loading cleaned data from {clean_path}...")
    records = []
    total = 0

    with open(clean_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            records.append(
                models.HistoricalRecord(
                    state_name    = row["state_name"],
                    district_name = row["district_name"],
                    crop          = row["crop"],
                    season        = row["season"],
                    crop_year     = int(row["crop_year"]),
                    area          = float(row["area"]),
                    production    = float(row["production"]),
                )
            )
            if len(records) >= BATCH_SIZE:
                db.bulk_save_objects(records)
                db.commit()
                records = []
                print(f"  Inserted {total:,} rows...", end="\r")

    if records:
        db.bulk_save_objects(records)
        db.commit()

    db.close()
    print(f"\n✅  Seeded {total:,} historical records into SQLite.")


if __name__ == "__main__":
    seed()
