"""Utility functions for csvnorm."""

import logging
import re
from pathlib import Path

from rich.logging import RichHandler


def to_snake_case(name: str) -> str:
    """Convert filename to clean snake_case.

    Replicates the bash logic:
    tr '[:upper:]' '[:lower:]' |
    sed -E 's/[^a-z0-9]+/_/g' |
    sed -E 's/_+/_/g' |
    sed -E 's/^_|_$//g'
    """
    # Remove .csv extension if present
    if name.lower().endswith(".csv"):
        name = name[:-4]

    # Convert to lowercase
    name = name.lower()

    # Replace non-alphanumeric with underscore
    name = re.sub(r"[^a-z0-9]+", "_", name)

    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)

    # Remove leading/trailing underscores
    name = name.strip("_")

    return name


def setup_logger(verbose: bool = False) -> logging.Logger:
    """Setup and return a logger instance with rich formatting.

    Args:
        verbose: If True, set log level to DEBUG, else INFO.
    """
    logger = logging.getLogger("csvnorm")

    if not logger.handlers:
        handler = RichHandler(
            show_time=False,
            show_path=verbose,
            markup=True,
            rich_tracebacks=True
        )
        logger.addHandler(handler)

    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    return logger


def validate_delimiter(delimiter: str) -> None:
    """Validate that delimiter is a single character.

    Raises:
        ValueError: If delimiter is not exactly one character.
    """
    if len(delimiter) != 1:
        raise ValueError("--delimiter must be a single character")


def ensure_output_dir(output_dir: Path) -> None:
    """Create output directory if it doesn't exist."""
    output_dir.mkdir(parents=True, exist_ok=True)
