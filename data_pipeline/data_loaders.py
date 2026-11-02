# data_loaders.py

# loads input files into python objects
from pathlib import Path
import logging
import pandas as pd
import json
import yaml

# Do not call logging.basicConfig() here.
# Use the logging configuration from Part 1.
logger = logging.getLogger(__name__)


def load_csv(filepath):
    """Load a CSV file into a DataFrame.
    filepath is a Path object.
    """

    # Reads CSV and returns back a data frame
    df = pd.read_csv(filepath)
    logger.info(f"Loaded CSV file: {filepath} ({len(df)} rows)")
    return df


def load_json(filepath):
    """Load a JSON file into a Python object (dict or list).
    filepath is a Path object.
    """
    with open(filepath) as f:
        data = json.load(f)
    logger.info(f"Loaded JSON file: {filepath}")
    return data


def load_yaml(filepath):
    """Load a YAML file into a Python object.
    filepath is a Path object.
    """

    # this is how config.yaml becomes a dictionary that the pipeline will read
    with open(filepath) as f:
        data = yaml.safe_load(f)
    logger.info(f"Loaded YAML file: {filepath}")
    return data


def load_data(filepath):
    """Load a file based on its extension.
    filepath is a string, such as 'fixtures/sample.csv'
    """

    # converting the string to a path
    path = Path(filepath)
    extension = path.suffix.lower()


    # pass the path object to the matched loader
    if extension == ".csv":
        return load_csv(path)
    elif extension == ".json":
        return load_json(path)
    elif extension in (".yaml", ".yml"):
        return load_yaml(path)
    else:
        # log the problem and then raise ValueError. pipeline catches the error not this module
        logger.error(f"Unsupported file format: {extension}")
        raise ValueError(f"Unsupported file format: {extension}")
