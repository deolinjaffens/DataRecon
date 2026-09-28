from __future__ import annotations

import json
from typing import Any

import pandas as pd


def flatten_json_object(value: Any, prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}

    if isinstance(value, dict):
        for key, nested in value.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(nested, dict):
                flattened.update(flatten_json_object(nested, new_prefix))
            elif isinstance(nested, list):
                flattened[new_prefix] = nested
            else:
                flattened[new_prefix] = nested
    else:
        flattened[prefix] = value

    return flattened


def load_json_records(path: str) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = [data]
    else:
        records = []

    flattened = [flatten_json_object(record) for record in records]
    return pd.DataFrame(flattened)
