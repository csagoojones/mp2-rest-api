# src/data_output.py

# Saves the clean data frame to the CSV file
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def save_data(df, filepath):
    """Save a DataFrame as a CSV file."""
    path = Path(filepath)

    # parents=True also creates any missing parent folders, and exist_ok=True means 
    # it's not an error if the folder is already there.
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    # DEBUG, so it only appears with --verbose. pipeline.py logs the
    # INFO message "saved cleaned data to ..." after this function returns.
    logger.debug(f"Saved {len(df)} rows to {path}")
    return path