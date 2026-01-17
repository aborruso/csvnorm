"""csvnorm - Validate and normalize CSV files."""

__version__ = "0.3.12"
__all__ = ["normalize_csv", "detect_encoding", "process_csv"]

from csvnorm.core import process_csv
from csvnorm.encoding import detect_encoding
from csvnorm.validation import normalize_csv
