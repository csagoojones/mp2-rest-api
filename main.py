import io
import json
import logging
from pathlib import Path
 
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
 
from src import DatasetInfo, DatasetStorage, HealthResponse, setup_logging
 
setup_logging(verbose=True)
logger = logging.getLogger(__name__)
 
app = FastAPI(title="Data Processing API", version="1.0.0")
storage = DatasetStorage()
 
 
@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return HealthResponse(status="ok", version=app.version)
 
 
@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    """Read and store a CSV upload."""
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
 
    # 1. Only accept .csv files
    if suffix != ".csv":
        logger.warning("Unsupported file format: %s", suffix or "(none)")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Please upload a .csv file.",
        )
 
    # 2. Read the bytes and parse them as CSV
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except pd.errors.EmptyDataError:
        logger.warning("Empty CSV upload: %s", filename)
        raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")
    except (pd.errors.ParserError, UnicodeDecodeError) as e:
        logger.warning("Could not parse CSV %s: %s", filename, e)
        raise HTTPException(
            status_code=400,
            detail="Could not read the file as CSV. Make sure it is a valid, UTF-8 encoded CSV.",
        )
 
    # 3. Save it and return its metadata
    dataset_id = storage.save(df, filename)
    metadata = storage.get_metadata(dataset_id)
    logger.info(
        "Uploaded dataset: id=%d, filename=%s, rows=%d",
        dataset_id, filename, metadata["rows"],
    )
    return DatasetInfo(**metadata)
 
 
@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, limit: int = Query(default=100, ge=1)):
    """Return up to limit rows from a stored dataset."""
    df = storage.get(dataset_id)  # a copy, so storage is never changed here
    if df is None:
        logger.warning("Dataset not found: %d", dataset_id)
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
 
    records = json.loads(df.head(limit).to_json(orient="records"))
    logger.info("Retrieved dataset: id=%d, returned_rows=%d", dataset_id, len(records))
    return {"id": dataset_id, "data": records, "total_rows": len(df)}