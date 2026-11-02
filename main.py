import io
import json
import logging
from pathlib import Path
 
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
 
from data_pipeline import create_cleaning_report, process_data, validate_dataframe
from src import (
    DatasetInfo,
    DatasetStorage,
    HealthResponse,
    ProcessConfig,
    ProcessingReport,
    log_requests,
    setup_logging,
)
 
setup_logging(verbose=True)
logger = logging.getLogger(__name__)
 
app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
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
 
 
@app.post(
    "/datasets/{dataset_id}/process",
    response_model=ProcessingReport,
)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    # 1. Retrieve a copy (404 check stays outside the try block)
    df = storage.get(dataset_id)
    if df is None:
        logger.warning("Dataset not found: %d", dataset_id)
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
 
    # 2. Convert the request model to the dict structure MP1 expects
    config_dict = config.model_dump()
    required_columns = config_dict["validation"]["required_columns"]
    numeric_columns = config_dict["validation"]["numeric_columns"]
 
    # 3. Every numeric column must exist in the data
    missing_numeric = [col for col in numeric_columns if col not in df.columns]
    if missing_numeric:
        logger.warning(
            "Numeric columns not in dataset %d: %s", dataset_id, missing_numeric
        )
        raise HTTPException(
            status_code=400,
            detail=f"Numeric columns not found in dataset: {missing_numeric}",
        )
 
    try:
        # 4. Validate and record how many rows were removed
        rows_original = len(df)
        validated = validate_dataframe(df, required_columns, numeric_columns)
        validation_rows_removed = rows_original - len(validated)
        logger.info(
            "Validated dataset: id=%d, %d -> %d rows",
            dataset_id, rows_original, len(validated),
        )
 
        # 5. Process a copy, then compare it with the validated data
        validated_copy = validated.copy()
        processed = process_data(validated, config_dict)
        cleaning_report = create_cleaning_report(validated_copy, processed)
    except ValueError as error:
        logger.warning("Processing failed for dataset %d: %s", dataset_id, error)
        raise HTTPException(status_code=400, detail=str(error))
 
    # 6. Only save once validation and processing both succeeded
    storage.update(dataset_id, processed)
    logger.info(
        "Processed dataset: id=%d, validation_removed=%d, rows_before=%d, rows_after=%d",
        dataset_id, validation_rows_removed,
        cleaning_report["rows_before"], cleaning_report["rows_after"],
    )
 
    return {
        "id": dataset_id,
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": cleaning_report,
    }