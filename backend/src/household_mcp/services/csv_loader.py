"""CSV file loading utilities for household data."""

from pathlib import Path
from typing import Optional

import pandas as pd


def load_csv(path: Path, encoding: str = "shift_jis") -> Optional[pd.DataFrame]:
    """Load a CSV file and return as a DataFrame.

    Args:
        path: Path to the CSV file.
        encoding: Character encoding of the CSV file (default: shift_jis).

    Returns:
        DataFrame containing the CSV data, or None if loading fails.
    """
    try:
        df = pd.read_csv(path, encoding=encoding)
        return df
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        return None
