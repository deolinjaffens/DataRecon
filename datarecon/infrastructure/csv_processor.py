from __future__ import annotations

import pandas as pd


def load_csv_records(path: str) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)
