"""
seed_db.py
----------
Reads the cleaned CSV and bulk-inserts all records into the
`historical_records` SQLite table.  Run ONCE after cleaning.

Usage:
    python seed_db.py
"""

import os
import pandas as pd
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

    print(f"Loading cleaned data from {clean_path}...")
    df = pd.read_csv(clean_path)
    total = len(df)
    print(f"Inserting {total:,} rows in batches of {BATCH_SIZE}...")

    records = []
    for i, row in enumerate(df.itertuples(index=False), 1):
        records.append(
            models.HistoricalRecord(
                state_name    = str(row.state_name),
                district_name = str(row.district_name),
                crop          = str(row.crop),
                season        = str(row.season),
                crop_year     = int(row.crop_year),
                area          = float(row.area),
                production    = float(row.production),
            )
        )
        if len(records) >= BATCH_SIZE:
            db.bulk_save_objects(records)
            db.commit()
            records = []
            print(f"  Inserted {i:,} / {total:,}", end="\r")

    if records:
        db.bulk_save_objects(records)
        db.commit()

    db.close()
    print(f"\n✅  Seeded {total:,} historical records into SQLite.")


if __name__ == "__main__":
    seed()
