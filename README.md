# DataRecon

DataRecon is a desktop application for comparing two structured data files. It helps you inspect differences in their columns and records without needing to write comparison scripts.

## Features

- Compare CSV, Excel `.xlsx`, and JSON files.
- Select a worksheet independently for each Excel workbook and see worksheets found only in either file.
- See columns shared by both files and columns found only in File A or File B.
- Match records using all common columns or choose one or more common columns as matching keys.
- Review identical records, changed records, and records found only in either file.
- Display record results as side-by-side columns or formatted JSON.

## Supported Files

| Format | Extensions |
| --- | --- |
| Comma-separated values | `.csv` |
| Excel workbook | `.xlsx` |
| JSON | `.json` |

JSON input can be a single object or a list of objects. Nested objects are flattened into dotted column names, such as `customer.address.city`. JSON arrays are retained as values.

Legacy Excel `.xls` files are not currently supported.

## Compare Two Files

1. Select **File A** and **File B**. For Excel workbooks, choose the worksheet to compare in each file card.
2. Choose how records should be matched. By default, DataRecon uses all common columns. Turn off **Use all common columns** to select specific shared columns as matching keys.
3. Select **Run comparison**.
4. Review the **Workbook sheets** tab for worksheets present in only one workbook, the **Schema** tab for column differences, and the **Records** tab for record results. Use the display selector to switch between column and JSON views.

Matching keys determine which records are paired. DataRecon compares the paired records across the union of both files' columns to classify them as identical or changed. For finding edits to records, choose a stable identifier (such as an ID column) as the matching key. Using every common column as the key means a record with a changed common-field value may instead appear as present only in A and present only in B, because those rows do not match on all selected keys.

## Comparison Behavior

- Column names are trimmed and compared without regard to case.
- Values are case-sensitive in the desktop app, and surrounding whitespace is ignored.
- Empty and missing values are treated as equivalent.
- Repeated records are retained and matched individually.

## Requirements

- Python 3.10 or newer
- Dependencies listed in [`requirements.txt`](requirements.txt)

## Install and Run

From the project directory, create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, activate the environment with:

```sh
source .venv/bin/activate
```

Launch the desktop application with:

```sh
python -m datarecon.ui.main_window
```

## Run Tests

Run the comparison tests from the project directory:

```sh
pytest
```