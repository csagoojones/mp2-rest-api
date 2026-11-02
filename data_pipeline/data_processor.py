# data_processor.py

## The cleaning steps are remove duplicates, handle missing values, remove outliers.

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def remove_duplicates(df):
    """Remove duplicate rows."""
    # save the row count first
    rows_before = len(df)
    # drop duplicates and keep the first copy
    df = df.drop_duplicates()
    rows_after = len(df)
    logger.debug(
        f"remove_duplicates: {rows_before} → {rows_after} rows "
        f"(removed {rows_before - rows_after})"
    )
    return df


def handle_missing(df, axis="rows"):
    """Drop rows or columns containing missing values."""
    if axis == "rows":
        rows_before = len(df)
        df = df.dropna(axis=0)
        rows_after = len(df)
        logger.debug(
            f"handle_missing: {rows_before} → {rows_after} rows "
            f"(removed {rows_before - rows_after})"
        )
    elif axis == "columns":
        cols_before = len(df.columns)
        df = df.dropna(axis=1)
        cols_after = len(df.columns)
        logger.debug(
            f"handle_missing: {cols_before} → {cols_after} columns "
            f"(removed {cols_before - cols_after})"
        )
    else:
        logger.error(f"Unsupported missing-value axis: {axis}")
        raise ValueError(f"Unsupported missing-value axis: {axis}")
    return df


def remove_outliers(df, columns, method, threshold):
    """Remove outliers from the specified numeric columns."""
    if method not in ("iqr", "zscore"):
        logger.error(f"Unsupported outlier method: {method}")
        raise ValueError(f"Unsupported outlier method: {method}")

    for col in columns:
        if col not in df.columns:
            logger.warning(f"Column not found: {col}")
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            logger.warning(f"Column not numeric: {col}")
            continue

        # interquartile range
        if method == "iqr":
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
        else:  # zscore: |value - mean| <= threshold * std
            mean = df[col].mean()
            std = df[col].std()
            lower = mean - threshold * std
            upper = mean + threshold * std

        # Keep values inside the bounds. Missing values are not outliers,so they are kept here (handle_missing deals with them).
        keep = df[col].between(lower, upper) | df[col].isna()
        removed = int((~keep).sum())
        df = df[keep]

        logger.debug(
            f"{col}: method={method}, threshold={threshold}, "
            f"lower={float(lower)}, upper={float(upper)}, removed={removed}"
        )
    return df


def process_data(df, config):
    """Apply the processing steps enabled in the configuration."""
    processing = config.get("processing", {})

    # Remove duplicates
    if processing.get("remove_duplicates", False):
        df = remove_duplicates(df)

    # take care of missing values
    missing = processing.get("missing", {})
    if missing.get("enabled", False):
        df = handle_missing(df, axis=missing.get("axis", "rows"))

    # remove the outliers
    outliers = processing.get("outliers", {})
    if outliers.get("enabled", False):
        df = remove_outliers(
            df,
            columns=outliers.get("columns", []),
            method=outliers.get("method"),
            threshold=outliers.get("threshold"),
        )

    return df


def create_cleaning_report(df_before, df_after):
    """Return a dictionary summarizing the cleaning results."""
    rows_before, columns_before = df_before.shape
    rows_after, columns_after = df_after.shape
    return {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "rows_removed": rows_before - rows_after,
        "columns_before": columns_before,
        "columns_after": columns_after,
        "columns_removed": columns_before - columns_after,
    }