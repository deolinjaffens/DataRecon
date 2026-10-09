from __future__ import annotations

import pandas as pd


def get_excel_sheet_names(path: str) -> list[str]:
    with pd.ExcelFile(path) as workbook:
        return workbook.sheet_names


def load_excel_records(path: str, sheet_name: str | None = None) -> pd.DataFrame:
    selected_sheet = sheet_name if sheet_name is not None else 0
    dataframe = pd.read_excel(path, sheet_name=selected_sheet, dtype=str, keep_default_na=False)
    return dataframe.fillna("")
