# src/utils.py

# helper functions that the whole pipeline shares
# logging setup and the check that an input file exists. They were moved out of pipeline.py
# so that pipeline.py only coordinates the steps.
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_logging(verbose=False):
    """Configure logging for the pipeline."""

    # DEBUG shows everything (used with --verbose), INFO hides the DEBUG detail.
    # This is a one-line if/else: level is DEBUG when verbose is True.
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )