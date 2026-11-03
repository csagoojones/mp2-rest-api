#model.py helps define, validate and structure the data models for the API as it
#comes in and out of the system.

from pydantic import BaseModel, Field
 
 
# Part 1
class HealthResponse(BaseModel):
    status: str
    version: str
 
 
class DatasetInfo(BaseModel):
    id: int
    filename: str
    rows: int
    columns: int
    column_names: list[str]
 
 
# Part 2 -- request model
class ValidationSettings(BaseModel):
    required_columns: list[str] = Field(default_factory=list)
    numeric_columns: list[str] = Field(default_factory=list)
 
 
class MissingSettings(BaseModel):
    enabled: bool = True
    axis: str = "rows"
 
 
class OutlierSettings(BaseModel):
    enabled: bool = False
    columns: list[str] = Field(default_factory=list)
    method: str = "iqr"
    threshold: float = 1.5
 
 
class ProcessingSettings(BaseModel):
    remove_duplicates: bool = True
    missing: MissingSettings = Field(default_factory=MissingSettings)
    outliers: OutlierSettings = Field(default_factory=OutlierSettings)
 
 
class ProcessConfig(BaseModel):
    validation: ValidationSettings = Field(default_factory=ValidationSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
 
 
# Part 2 -- response model
class ProcessingReport(BaseModel):
    id: int
    validation_rows_removed: int
    cleaning_report: dict[str, int]