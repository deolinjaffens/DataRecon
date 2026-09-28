from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ComparisonOptions:
    matching_columns: list[str] | None = None
    case_sensitive_values: bool = True
    normalize_whitespace: bool = True


@dataclass
class SchemaComparisonResult:
    common_columns: list[str]
    columns_only_in_a: list[str]
    columns_only_in_b: list[str]


@dataclass
class ComparisonResult:
    schema: SchemaComparisonResult
    record_counts: dict[str, int]
    common_identical_records: list[dict[str, Any]] = field(default_factory=list)
    changed_records: list[dict[str, Any]] = field(default_factory=list)
    records_only_in_a: list[dict[str, Any]] = field(default_factory=list)
    records_only_in_b: list[dict[str, Any]] = field(default_factory=list)


def compare_dataframes(
    left: pd.DataFrame,
    right: pd.DataFrame,
    options: ComparisonOptions | None = None,
) -> ComparisonResult:
    options = options or ComparisonOptions()

    left_norm = _normalize_dataframe(left)
    right_norm = _normalize_dataframe(right)

    left_columns = list(left_norm.columns)
    right_columns = list(right_norm.columns)

    common_columns = sorted(set(left_columns) & set(right_columns))
    only_in_a = sorted(set(left_columns) - set(right_columns))
    only_in_b = sorted(set(right_columns) - set(left_columns))

    schema = SchemaComparisonResult(
        common_columns=common_columns,
        columns_only_in_a=only_in_a,
        columns_only_in_b=only_in_b,
    )

    if options.matching_columns is not None:
        matching_columns = _normalize_list(options.matching_columns)
        matching_columns = [column for column in matching_columns if column in common_columns]
    else:
        matching_columns = common_columns

    if not matching_columns and common_columns:
        matching_columns = common_columns

    left_rows = _iter_rows(left_norm, left_columns)
    right_rows = _iter_rows(right_norm, right_columns)

    matched_left_indexes: set[int] = set()
    matched_right_indexes: set[int] = set()
    pairs: list[tuple[int, int]] = []

    for left_index, left_row in enumerate(left_rows):
        for right_index, right_row in enumerate(right_rows):
            if right_index in matched_right_indexes:
                continue
            if _rows_match_on_keys(left_row, right_row, matching_columns, options):
                matched_left_indexes.add(left_index)
                matched_right_indexes.add(right_index)
                pairs.append((left_index, right_index))
                break

    all_union_columns = sorted(set(left_columns) | set(right_columns))
    identical_records: list[dict[str, Any]] = []
    changed_records: list[dict[str, Any]] = []

    for left_index, right_index in pairs:
        left_row = left_rows[left_index]
        right_row = right_rows[right_index]
        differences = _diff_row_values(
            left_row,
            right_row,
            all_union_columns,
            case_sensitive=options.case_sensitive_values,
            normalize_whitespace=options.normalize_whitespace,
        )

        if differences:
            changed_records.append(
                {
                    "left_index": left_index,
                    "right_index": right_index,
                    "key": {column: left_row.get(column, "") for column in matching_columns},
                    "differences": differences,
                    "left_record": left_row,
                    "right_record": right_row,
                }
            )
        else:
            identical_records.append(
                {
                    "left_index": left_index,
                    "right_index": right_index,
                    "key": {column: left_row.get(column, "") for column in matching_columns},
                    "left_record": left_row,
                    "right_record": right_row,
                }
            )

    records_only_in_a = [
        {"index": index, "record": left_rows[index]}
        for index in range(len(left_rows))
        if index not in matched_left_indexes
    ]
    records_only_in_b = [
        {"index": index, "record": right_rows[index]}
        for index in range(len(right_rows))
        if index not in matched_right_indexes
    ]

    record_counts = {
        "common_identical": len(identical_records),
        "changed": len(changed_records),
        "only_in_a": len(records_only_in_a),
        "only_in_b": len(records_only_in_b),
    }

    return ComparisonResult(
        schema=schema,
        record_counts=record_counts,
        common_identical_records=identical_records,
        changed_records=changed_records,
        records_only_in_a=records_only_in_a,
        records_only_in_b=records_only_in_b,
    )


def _normalize_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = [str(column).strip() for column in normalized.columns]
    normalized.columns = [column.lower() if isinstance(column, str) else str(column) for column in normalized.columns]
    return normalized


def _normalize_list(columns: list[str]) -> list[str]:
    return [str(column).strip().lower() for column in columns]


def _iter_rows(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    return [
        {
            str(column): frame.iloc[row][column]
            for column in columns
        }
        for row in range(len(frame))
    ]


def _normalize_value(value: Any, case_sensitive: bool) -> Any:
    if value is None or pd.isna(value):
        return ""

    if isinstance(value, (list, dict)):
        value = json.dumps(value, sort_keys=True, default=str)

    if isinstance(value, str):
        value = value.strip()
        if not case_sensitive:
            value = value.lower()
        return value

    if isinstance(value, (int, float, bool)):
        value = str(value)
        if not case_sensitive:
            value = value.lower()
        return value

    return str(value)


def _rows_match_on_keys(
    left_row: dict[str, Any],
    right_row: dict[str, Any],
    matching_columns: list[str],
    options: ComparisonOptions,
) -> bool:
    if not matching_columns:
        return True

    for column in matching_columns:
        left_value = _normalize_value(left_row.get(column, ""), case_sensitive=options.case_sensitive_values)
        right_value = _normalize_value(right_row.get(column, ""), case_sensitive=options.case_sensitive_values)
        if left_value != right_value:
            return False
    return True


def _diff_row_values(
    left_row: dict[str, Any],
    right_row: dict[str, Any],
    columns: list[str],
    case_sensitive: bool,
    normalize_whitespace: bool,
) -> dict[str, tuple[Any, Any]]:
    differences: dict[str, tuple[Any, Any]] = {}
    for column in columns:
        raw_left = left_row.get(column, "")
        raw_right = right_row.get(column, "")

        left_norm = _normalize_value(raw_left, case_sensitive=case_sensitive)
        right_norm = _normalize_value(raw_right, case_sensitive=case_sensitive)

        if normalize_whitespace:
            left_norm = str(left_norm).strip()
            right_norm = str(right_norm).strip()

        if left_norm != right_norm:
            differences[column] = (raw_left, raw_right)
    return differences
