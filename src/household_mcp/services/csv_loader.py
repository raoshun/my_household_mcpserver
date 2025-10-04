from pathlib import Path
from typing import Optional

import pandas as pd


def load_csv(path: Path, encoding: str = "shift_jis") -> Optional[pd.DataFrame]:
    try:
        df = pd.read_csv(path, encoding=encoding)
        return df
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        return None
