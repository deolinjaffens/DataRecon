from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datarecon.domain.comparison import ComparisonOptions, compare_dataframes
from datarecon.infrastructure.csv_processor import load_csv_records
from datarecon.infrastructure.excel_processor import get_excel_sheet_names, load_excel_records
from datarecon.infrastructure.json_processor import load_json_records


class DataSet:
    def __init__(self, source_path: str, dataframe: pd.DataFrame, file_type: str, sheet_name: str | None = None):
        self.source_path = source_path
        self.dataframe = dataframe
        self.file_type = file_type
        self.sheet_name = sheet_name
        self.columns = list(dataframe.columns)


class ComparisonService:
    def get_sheet_names(self, path: str) -> list[str]:
        if Path(path).suffix.lower() == ".xlsx":
            return get_excel_sheet_names(path)
        return []

    def load_dataset(self, path: str, sheet_name: str | None = None) -> DataSet:
        file_path = Path(path)
        suffix = file_path.suffix.lower()

        if suffix == ".csv":
            dataframe = load_csv_records(str(file_path))
            file_type = "csv"
        elif suffix == ".xlsx":
            dataframe = load_excel_records(str(file_path), sheet_name)
            file_type = "excel"
        elif suffix == ".json":
            dataframe = load_json_records(str(file_path))
            file_type = "json"
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        return DataSet(str(file_path), dataframe, file_type, sheet_name)

    def compare(self, left: DataSet, right: DataSet, options: ComparisonOptions | None = None) -> Any:
        return compare_dataframes(left.dataframe, right.dataframe, options)
