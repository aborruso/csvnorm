"""CSV Normalizer - Validate and normalize CSV files."""

__version__ = "0.2.0"
__all__ = ["normalize_csv", "detect_encoding", "process_csv"]

from csv_normalizer.core import process_csv
from csv_normalizer.encoding import detect_encoding
from csv_normalizer.validation import normalize_csv
