import pandas as pd
import pytest

from datarecon.domain.comparison import (
    ComparisonOptions,
    SchemaComparisonResult,
    compare_dataframes,
)


def test_same_columns_and_matching_records():
    left = pd.DataFrame([
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": 40},
    ])
    right = pd.DataFrame([
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": 40},
    ])

    result = compare_dataframes(left, right)

    assert result.schema.common_columns == ["age", "id", "name"]
    assert result.record_counts["common_identical"] == 2
    assert result.record_counts["changed"] == 0
    assert result.record_counts["only_in_a"] == 0
    assert result.record_counts["only_in_b"] == 0


def test_different_columns_and_header_case_difference():
    left = pd.DataFrame([
        {"patient_id": 1, "Name": "Alice", "Age": 30},
    ])
    right = pd.DataFrame([
        {"PATIENT_ID": 1, "Name": "Alice", "Salary": 50000},
    ])

    result = compare_dataframes(left, right)

    assert "patient_id" in result.schema.common_columns
    assert "name" in result.schema.common_columns
    assert result.schema.columns_only_in_a == ["age"]
    assert result.schema.columns_only_in_b == ["salary"]


def test_custom_matching_columns_and_changed_records():
    left = pd.DataFrame([
        {"patient_id": 1, "name": "John", "age": 30},
        {"patient_id": 2, "name": "Mary", "age": 25},
    ])
    right = pd.DataFrame([
        {"patient_id": 1, "name": "John", "age": 31},
        {"patient_id": 3, "name": "Steve", "age": 35},
    ])

    result = compare_dataframes(
        left,
        right,
        ComparisonOptions(matching_columns=["patient_id"]),
    )

    assert result.record_counts["common_identical"] == 0
    assert result.record_counts["changed"] == 1
    assert result.record_counts["only_in_a"] == 1
    assert result.record_counts["only_in_b"] == 1
    assert result.changed_records[0]["differences"]["age"] == (30, 31)


def test_default_matching_columns_use_all_common_columns():
    left = pd.DataFrame([
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ])
    right = pd.DataFrame([
        {"id": 1, "name": "Alice"},
        {"id": 3, "name": "Charlie"},
    ])

    result = compare_dataframes(left, right)

    assert result.record_counts["common_identical"] == 1
    assert result.record_counts["only_in_a"] == 1
    assert result.record_counts["only_in_b"] == 1


def test_duplicate_records_preserved():
    left = pd.DataFrame([
        {"id": 1, "name": "Alice"},
        {"id": 1, "name": "Alice"},
    ])
    right = pd.DataFrame([
        {"id": 1, "name": "Alice"},
    ])

    result = compare_dataframes(left, right)

    assert result.record_counts["common_identical"] == 1
    assert result.record_counts["only_in_a"] == 1
    assert result.record_counts["only_in_b"] == 0


def test_empty_values_and_whitespace_treated_as_equal():
    left = pd.DataFrame([
        {"id": 1, "name": " Alice "},
        {"id": 2, "name": None},
    ])
    right = pd.DataFrame([
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": ""},
    ])

    result = compare_dataframes(left, right)

    assert result.record_counts["common_identical"] == 2
    assert result.record_counts["changed"] == 0


def test_case_sensitive_and_case_insensitive_values():
    left = pd.DataFrame([
        {"id": 1, "name": "Alice"},
    ])
    right = pd.DataFrame([
        {"id": 1, "name": "alice"},
    ])

    sensitive = compare_dataframes(left, right, ComparisonOptions(case_sensitive_values=True))
    insensitive = compare_dataframes(left, right, ComparisonOptions(case_sensitive_values=False))

    assert sensitive.record_counts["only_in_a"] == 1
    assert sensitive.record_counts["only_in_b"] == 1
    assert insensitive.record_counts["common_identical"] == 1


def test_json_nested_paths_are_flattened():
    left = pd.DataFrame([
        {"patient.id": 10, "patient.name.first_name": "John", "patient.name.last_name": "Doe"},
    ])
    right = pd.DataFrame([
        {"patient.id": 10, "patient.name.first_name": "John", "patient.name.last_name": "Doe"},
    ])

    result = compare_dataframes(left, right)

    assert result.record_counts["common_identical"] == 1


def test_missing_json_properties_are_treated_as_empty():
    left = pd.DataFrame([
        {"patient.id": 1, "patient.name.first_name": "John", "patient.name.last_name": "Doe"},
    ])
    right = pd.DataFrame([
        {"patient.id": 1, "patient.name.first_name": "John"},
    ])

    result = compare_dataframes(left, right)

    assert result.record_counts["common_identical"] == 0
    assert result.record_counts["changed"] == 1


def test_schema_result_is_structured():
    result = SchemaComparisonResult(
        common_columns=["id"],
        columns_only_in_a=["name"],
        columns_only_in_b=["age"],
    )

    assert result.common_columns == ["id"]
    assert result.columns_only_in_a == ["name"]
    assert result.columns_only_in_b == ["age"]
