from pathlib import Path
 
import pytest
from fastapi.testclient import TestClient
 
from main import app, storage
 

 # allows us to give each test a TestClient
@pytest.fixture
def client():
    storage.clear()
    with TestClient(app) as test_client:
        yield test_client
    storage.clear()
 
 #reads sample data and returns it as bytes
@pytest.fixture
def sample_csv_bytes():
    filepath = Path("fixtures") / "sample_data.csv"
    return filepath.read_bytes()
 
 
 # uploads the sample CSV and returns the dataset ID
@pytest.fixture
def uploaded_dataset_id(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={
            "file": (
                "sample_data.csv",
                sample_csv_bytes,
                "text/csv"
            )
        }
    )
    assert response.status_code == 200
    return response.json()["id"]
 
 # provides the body for the processing request
@pytest.fixture
def processing_body():
    return {
        "validation": {
            "required_columns": ["student_id", "score"],
            "numeric_columns": ["score"]
        },
        "processing": {
            "remove_duplicates": True,
            "missing": {
                "enabled": True,
                "axis": "rows"
            },
            "outliers": {
                "enabled": False,
                "columns": [],
                "method": "iqr",
                "threshold": 1.5
            }
        }
    }
 