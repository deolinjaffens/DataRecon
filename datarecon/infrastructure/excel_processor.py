from __future__ import annotations

import pandas as pd


def load_excel_records(path: str) -> pd.DataFrame:
    dataframe = pd.read_excel(path, dtype=str, keep_default_na=False)
    return dataframe.fillna("")
