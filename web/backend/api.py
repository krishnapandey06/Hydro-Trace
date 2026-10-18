# --------------------------------------------------
# INGRES FASTAPI BACKEND
# --------------------------------------------------

import sys
import os
import pandas as pd

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# --------------------------------------------------
# PROJECT PATH
# --------------------------------------------------

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        ".."
    )
)

SRC_PATH = os.path.join(
    PROJECT_ROOT,
    "src"
)

sys.path.append(SRC_PATH)


# --------------------------------------------------
# IMPORT INGRES PIPELINE
# --------------------------------------------------

from full_pipeline import run_full_pipeline


# --------------------------------------------------
# FASTAPI APP
# --------------------------------------------------

app = FastAPI(
    title="INGRES API",
    description="AI-driven groundwater data analysis API",
    version="1.0.0"
)


# --------------------------------------------------
# CORS CONFIGURATION
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# --------------------------------------------------
# CHAT REQUEST MODEL
# --------------------------------------------------

class ChatRequest(BaseModel):
    query: str


# --------------------------------------------------
# HELPER: DATASET PATH
# --------------------------------------------------

def get_dataset_path():

    return os.path.join(
        PROJECT_ROOT,
        "data",
        "INGRES_Step1_Cleaned_Dataset.csv"
    )


# --------------------------------------------------
# HELPER: LOAD DATASET
# --------------------------------------------------

def load_dataset():

    data_path = get_dataset_path()

    if not os.path.exists(data_path):
        raise FileNotFoundError(
            f"Dataset not found: {data_path}"
        )

    return pd.read_csv(data_path)


# --------------------------------------------------
# ROOT ENDPOINT
# --------------------------------------------------

@app.get("/")
def root():

    return {
        "success": True,
        "message": "INGRES API is running",
        "endpoints": [
            "/api/health",
            "/api/dataset",
            "/api/map-data",
            "/api/chat"
        ]
    }


# --------------------------------------------------
# HEALTH CHECK ENDPOINT
# --------------------------------------------------

@app.get("/api/health")
def health():

    return {
        "success": True,
        "status": "healthy"
    }


# --------------------------------------------------
# DATASET ENDPOINT
# --------------------------------------------------

@app.get("/api/dataset")
def get_dataset():

    try:

        df = load_dataset()

        # Convert NaN and infinite values to JSON-safe nulls.
        df = df.astype(object)
        df = df.where(pd.notna(df), None)

        records = df.to_dict(orient="records")

        return {
            "success": True,
            "count": len(records),
            "columns": list(df.columns),
            "data": records
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# --------------------------------------------------
# MAP DATA ENDPOINT
# --------------------------------------------------

@app.get("/api/map-data")
def get_map_data():

    try:

        df = load_dataset()

        records = []

        for _, row in df.iterrows():

            extraction = row.get(
                "Stage_of_Ground_Water_Extraction_pct",
                None
            )

            # Convert missing extraction values to None.
            if pd.isna(extraction):
                extraction = None
            else:
                extraction = float(extraction)

            state = row.get("STATE", None)
            district = row.get("DISTRICT", None)
            category = row.get(
                "Extraction_Category",
                "Unknown"
            )

            records.append({
                "state": (
                    None if pd.isna(state) else str(state)
                ),
                "district": (
                    None if pd.isna(district) else str(district)
                ),
                "category": (
                    "Unknown"
                    if pd.isna(category)
                    else str(category)
                ),
                "extraction": extraction
            })

        return {
            "success": True,
            "count": len(records),
            "data": records
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# --------------------------------------------------
# CHAT ENDPOINT
# --------------------------------------------------

@app.post("/api/chat")
def chat(request: ChatRequest):

    try:

        query = request.query.strip()

        if not query:
            return {
                "success": False,
                "error": "Query cannot be empty"
            }

        result = run_full_pipeline(query)

        # Ensure the pipeline returns a dictionary.
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": "Unexpected response from INGRES pipeline"
            }

        # Make sure the frontend receives a success field.
        result["success"] = True

        # ------------------------------------------
        # FIX MISSING STATE IN RESPONSE
        # ------------------------------------------

        if (
            result.get("district")
            and not result.get("state")
        ):

            database_result = result.get(
                "database_result",
                {}
            )

            if isinstance(database_result, dict):

                state_values = database_result.get("STATE")

                if isinstance(state_values, dict) and state_values:

                    result["state"] = next(
                        iter(state_values.values())
                    )

        return result

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# --------------------------------------------------
# RUN SERVER
# --------------------------------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "web.backend.api:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
