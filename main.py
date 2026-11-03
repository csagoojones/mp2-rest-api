import io
import json
import logging
from pathlib import Path
 
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile


# Importing all of the packages in from data_pipeline
 
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
    return {"status": "ok", "version": app.version}
 
 
@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    """Read and store a CSV upload."""
    filename = file.filename or ""
 
    # Only accept .csv files
    suffix = Path(filename).suffix.lower()
    if suffix != ".csv":
        logger.warning(f"Unsupported file format: {suffix}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Please upload a .csv file.",
        )
 
    # This part will read the bytes of the file and parse as a csv
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        logger.warning(f"Cannot read CSV: {error}")
        raise HTTPException(
            status_code=400,
            detail="Cannot read the uploaded CSV. Make sure it is a valid, non-empty CSV file.",
        )
 
    # saves the data and stores the metadaata
    dataset_id = storage.save(df, filename)
    metadata = storage.get_metadata(dataset_id)
    logger.info(
        f"Uploaded dataset: id={dataset_id}, filename={filename}, rows={metadata['rows']}"
    )
    return metadata
 
 
@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, limit: int = Query(default=100, ge=1)):
    """Return up to limit rows from a stored dataset."""
    df = storage.get(dataset_id)  # storage isnt changed here
    if df is None:
        logger.warning(f"Dataset not found: {dataset_id}")
        raise HTTPException(status_code=404, detail="Dataset not found")
 
    records = json.loads(df.head(limit).to_json(orient="records"))
    logger.info(f"Retrieved dataset: id={dataset_id}, returned_rows={len(records)}")
    return {"id": dataset_id, "data": records, "total_rows": len(df)}
 
 
@app.post("/datasets/{dataset_id}/process", response_model=ProcessingReport)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    # gets a copy 
    df = storage.get(dataset_id)
    if df is None:
        logger.warning(f"Dataset not found: {dataset_id}")
        raise HTTPException(status_code=404, detail="Dataset not found")
 
    # Converts the request model to dictionary
    settings = config.model_dump()
    required_columns = settings["validation"]["required_columns"]
    numeric_columns = settings["validation"]["numeric_columns"]
 
    #Every configured numeric column must exist
    for col in numeric_columns:
        if col not in df.columns:
            logger.warning(f"Numeric column not found: {col}")
            raise HTTPException(
                status_code=400, detail=f"Numeric column not found: {col}"
            )
 
    try:
        #Validate and record how many rows removed
        rows_loaded = len(df)
        validated = validate_dataframe(df, required_columns, numeric_columns)
        validation_rows_removed = rows_loaded - len(validated)
        logger.info(f"Validation complete: id={dataset_id}, {rows_loaded} → {len(validated)} rows")
 
        df_before = validated.copy()
        df_after = process_data(validated, settings)
        report = create_cleaning_report(df_before, df_after)
    except ValueError as error:
        logger.warning(f"Processing failed: id={dataset_id}, {error}")
        raise HTTPException(status_code=400, detail=str(error))
 
    # update storage once validation and processing both work
    storage.update(dataset_id, df_after)
    logger.info(
        f"Processed dataset: id={dataset_id}, validation_removed={validation_rows_removed}, "
        f"rows_before={report['rows_before']}, rows_after={report['rows_after']}"
    )
 
    return {
        "id": dataset_id,
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": report,
    }