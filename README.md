# 🌾 Crop Production Prediction API

A FastAPI application that **cleans**, **trains**, and **serves predictions** for Indian crop production data (1997–2015).  
Every prediction is auto-saved and linked back to matching historical records so you always know whether the requested combination existed in the training data.

---

## 📁 Project Structure

```
crop_prediction_api/
├── data/
│   ├── crop_production.csv          ← original raw data (put it here)
│   └── crop_production_clean.csv    ← auto-generated after cleaning
├── ml/
│   ├── model.pkl                    ← trained RandomForest model
│   ├── encoders.pkl                 ← label encoders for categoricals
│   └── metadata.json                ← feature names, label maps, metrics
├── data_cleaner.py                  ← Step 1: clean raw CSV
├── train_model.py                   ← Step 2: train & save model
├── seed_db.py                       ← Step 3: load historical data into SQLite
├── predictor.py                     ← ML inference singleton
├── database.py                      ← SQLAlchemy engine + session
├── models.py                        ← ORM table definitions
├── schemas.py                       ← Pydantic request/response schemas
├── main.py                          ← FastAPI app + all routes
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Clean the data
```bash
python data_cleaner.py
```

### 3. Train the model  *(takes ~30–60 seconds)*
```bash
python train_model.py
```

### 4. Start the API
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> The historical data is seeded into SQLite automatically on the **first startup**.

---

## 📖 API Endpoints

Open the interactive docs at: **http://localhost:8000/docs**

### 🔮 Predictions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/predict` | Make a prediction (auto-saved) |
| `GET` | `/predictions` | List all saved predictions |
| `GET` | `/predictions/{id}` | Get a single prediction |
| `DELETE` | `/predictions/{id}` | Delete a prediction |

### 📚 Historical Data

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/historical` | Query historical records (filterable) |
| `GET` | `/historical/{id}` | Get one historical record |

### 🔧 Options / Lookup

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/options/states` | All available states |
| `GET` | `/options/districts` | Districts (filter by state) |
| `GET` | `/options/crops` | All available crops |
| `GET` | `/options/seasons` | All seasons |

### ℹ️ Model & Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/model/info` | Model accuracy metrics + label options |
| `GET` | `/health` | Health check |

---

## 📝 Example: Make a Prediction

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "state_name": "Karnataka",
    "district_name": "BANGALORE",
    "crop": "Rice",
    "season": "Kharif",
    "crop_year": 2020,
    "area": 5000.0
  }'
```

**Response:**
```json
{
  "id": 1,
  "state_name": "Karnataka",
  "district_name": "BANGALORE",
  "crop": "Rice",
  "season": "Kharif",
  "crop_year": 2020,
  "area": 5000.0,
  "predicted_production": 14823.45,
  "has_historical_match": true,
  "historical_matches": [
    {
      "state_name": "Karnataka",
      "district_name": "BANGALORE",
      "crop": "Rice",
      "season": "Kharif",
      "crop_year": 2005,
      "area": 4200.0,
      "production": 12600.0
    }
  ],
  "created_at": "2024-06-01T10:30:00",
  "model_version": "v1"
}
```

> **`has_historical_match: true`** means this state/district/crop/season combination **was seen** in the training data. The `historical_matches` array shows the actual past records.

---

## 🧠 Model Details

- **Algorithm**: Random Forest Regressor (150 trees, max_depth=20)
- **Features**: state, district, crop, season, year, area
- **Target**: production (metric tonnes)
- **Train/Test split**: 80/20

---

## 💾 Database

SQLite is used (no external DB needed). The file `crop_predictions.db` is created automatically.  
Two tables:
- `predictions` — every API prediction request, auto-saved
- `historical_records` — the full cleaned training dataset (seeded on first startup)
