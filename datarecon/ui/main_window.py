from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from datarecon.application.comparison_service import ComparisonService
from datarecon.domain.comparison import ComparisonOptions


class DataReconWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DataRecon")
        self.resize(1100, 700)

        self.service = ComparisonService()
        self.left_path: str | None = None
        self.right_path: str | None = None
        self.left_dataset = None
        self.right_dataset = None
        self.matching_column_checkboxes: list[QCheckBox] = []

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(18)

        title_row = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel("Compare your data")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Load two files, choose matching keys, and inspect every difference.")
        subtitle.setObjectName("pageSubtitle")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        title_row.addLayout(title_block)
        title_row.addStretch()

        self.compare_button = QPushButton("Run comparison")
        self.compare_button.setObjectName("primaryButton")
        self.compare_button.setMinimumHeight(42)
        self.compare_button.clicked.connect(self._run_comparison)
        title_row.addWidget(self.compare_button)
        scroll_layout.addLayout(title_row)

        self.left_path_label = QLabel("No file selected")
        self.right_path_label = QLabel("No file selected")
        self.select_left_button = QPushButton("Select File A")
        self.select_right_button = QPushButton("Select File B")
        self.select_left_button.clicked.connect(self._choose_left_file)
        self.select_right_button.clicked.connect(self._choose_right_file)

        files_row = QHBoxLayout()
        files_row.setSpacing(14)
        files_row.addWidget(self._create_file_card("FILE A", self.left_path_label, self.select_left_button))
        files_row.addWidget(self._create_file_card("FILE B", self.right_path_label, self.select_right_button))
        scroll_layout.addLayout(files_row)

        self.matching_columns_group = QGroupBox("Matching columns")
        self.matching_columns_layout = QVBoxLayout(self.matching_columns_group)
        self.matching_columns_layout.setContentsMargins(18, 16, 18, 16)
        self.matching_columns_layout.setSpacing(10)
        matching_hint = QLabel("Keys identify which records belong together. Use all shared columns by default.")
        matching_hint.setObjectName("sectionHint")
        self.matching_columns_layout.addWidget(matching_hint)
        self.use_all_columns_checkbox = QCheckBox("Use all common columns")
        self.use_all_columns_checkbox.setChecked(True)
        self.use_all_columns_checkbox.toggled.connect(self._toggle_matching_columns)
        self.matching_columns_layout.addWidget(self.use_all_columns_checkbox)

        self.matching_columns_container = QWidget()
        self.matching_columns_container_layout = QVBoxLayout(self.matching_columns_container)
        self.matching_columns_container_layout.setContentsMargins(0, 0, 0, 0)
        self.matching_columns_layout.addWidget(self.matching_columns_container)

        scroll_layout.addWidget(self.matching_columns_group)

        self.status_box = QTextEdit()
        self.status_box.setObjectName("statusBox")
        self.status_box.setFixedHeight(58)
        self.status_box.setReadOnly(True)
        self.status_box.setPlaceholderText("Comparison status will appear here after both files are loaded.")
        scroll_layout.addWidget(self.status_box)

        self.results_tabs = QTabWidget()
        self.results_tabs.setDocumentMode(True)
        self.schema_table = QTableWidget(0, 3)
        self.schema_table.setHorizontalHeaderLabels(["Common", "Only in A", "Only in B"])
        self._configure_table(self.schema_table)
        self.results_tabs.addTab(self.schema_table, "Schema")

        records_page = QWidget()
        records_layout = QVBoxLayout(records_page)
        records_layout.setContentsMargins(0, 12, 0, 0)
        records_toolbar = QHBoxLayout()
        records_toolbar.addWidget(QLabel("Display records as:"))
        self.record_format_combo = QComboBox()
        self.record_format_combo.addItems(["Columns", "JSON"])
        self.record_format_combo.setToolTip("Choose a readable column view or the complete JSON record view.")
        self.record_format_combo.currentTextChanged.connect(self._refresh_record_tables)
        records_toolbar.addWidget(self.record_format_combo)
        records_toolbar.addStretch()
        records_layout.addLayout(records_toolbar)

        self.record_tabs = QTabWidget()
        self.record_tabs.setDocumentMode(True)
        self.record_tables: dict[str, QTableWidget] = {}
        for key, label in (
            ("identical", "Identical"),
            ("changed", "Changed"),
            ("only_in_a", "Only in A"),
            ("only_in_b", "Only in B"),
        ):
            table = QTableWidget()
            self._configure_table(table)
            self.record_tables[key] = table
            self.record_tabs.addTab(table, label)
        self.records_table = self.record_tables["identical"]
        records_layout.addWidget(self.record_tabs, 1)
        self.results_tabs.addTab(records_page, "Records")
        scroll_layout.addWidget(self.results_tabs, 1)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        self.setCentralWidget(central)

    def _create_file_card(self, label: str, path_label: QLabel, button: QPushButton) -> QFrame:
        card = QFrame()
        card.setObjectName("fileCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(8)
        eyebrow = QLabel(label)
        eyebrow.setObjectName("cardEyebrow")
        path_label.setObjectName("filePath")
        path_label.setWordWrap(True)
        button.setObjectName("secondaryButton")
        button.setMinimumHeight(34)
        layout.addWidget(eyebrow)
        layout.addWidget(path_label)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        return card

    def _configure_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setWordWrap(False)
        table.setMinimumHeight(300)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow { background: #f5f7fb; }
            QWidget { color: #172033; font-family: 'Segoe UI'; font-size: 10pt; }
            QScrollArea { background: transparent; }
            #pageTitle { color: #172033; font-size: 23pt; font-weight: 700; }
            #pageSubtitle, #sectionHint { color: #667085; }
            #cardEyebrow { color: #5267a8; font-size: 8pt; font-weight: 700; }
            #fileCard, QGroupBox { background: white; border: 1px solid #dfe4ee; border-radius: 10px; }
            #filePath { color: #344054; font-weight: 600; min-height: 24px; }
            QGroupBox { margin-top: 8px; padding-top: 14px; font-weight: 700; }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #172033; }
            QCheckBox { spacing: 8px; color: #344054; }
            QPushButton { border-radius: 7px; padding: 7px 14px; font-weight: 600; }
            #primaryButton { background: #5267a8; color: white; border: none; padding: 9px 20px; }
            #primaryButton:hover { background: #40548f; }
            #secondaryButton { background: #eef1f8; color: #40548f; border: 1px solid #d8deec; }
            #secondaryButton:hover { background: #e2e7f4; }
            #statusBox { background: #eef6f3; border: 1px solid #cfe5dc; border-radius: 8px; padding: 8px; color: #275c4c; }
            QTabWidget::pane { background: white; border: 1px solid #dfe4ee; border-radius: 0 8px 8px 8px; }
            QTabBar::tab { background: #e9edf5; color: #667085; padding: 9px 18px; margin-right: 3px; border-radius: 6px 6px 0 0; }
            QTabBar::tab:selected { background: white; color: #40548f; font-weight: 700; }
            QTableWidget { background: white; alternate-background-color: #f7f9fc; gridline-color: #e7ebf2; border: none; }
            QHeaderView::section { background: #f0f3f8; color: #475467; padding: 9px; border: none; border-bottom: 1px solid #dfe4ee; font-weight: 700; }
        """)

    def _choose_left_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File A",
            str(Path.home()),
            "Data files (*.csv *.xlsx *.json)",
        )
        if path:
            self.left_path = path
            self.left_path_label.setText(Path(path).name)
            self._refresh_matching_columns()

    def _choose_right_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File B",
            str(Path.home()),
            "Data files (*.csv *.xlsx *.json)",
        )
        if path:
            self.right_path = path
            self.right_path_label.setText(Path(path).name)
            self._refresh_matching_columns()

    def _refresh_matching_columns(self) -> None:
        if not self.left_path or not self.right_path:
            self._set_matching_column_checkboxes([])
            return

        try:
            left_dataset = self.service.load_dataset(self.left_path)
            right_dataset = self.service.load_dataset(self.right_path)
            self.left_dataset = left_dataset
            self.right_dataset = right_dataset
            common_columns = sorted(
                set(str(column).strip().lower() for column in left_dataset.columns)
                & set(str(column).strip().lower() for column in right_dataset.columns)
            )
            self._set_matching_column_checkboxes(common_columns)
        except Exception as exc:  # pragma: no cover - UI fail path
            self._set_matching_column_checkboxes([])
            self.status_box.setPlainText(f"Unable to inspect columns: {exc}")

    def _set_matching_column_checkboxes(self, columns: list[str]) -> None:
        for checkbox in self.matching_column_checkboxes:
            self.matching_columns_container_layout.removeWidget(checkbox)
            checkbox.deleteLater()
        self.matching_column_checkboxes = []

        if not columns:
            self.use_all_columns_checkbox.setChecked(True)
            self.use_all_columns_checkbox.setEnabled(False)
            self.matching_columns_container.setEnabled(False)
            return

        self.use_all_columns_checkbox.setEnabled(True)
        self.matching_columns_container.setEnabled(not self.use_all_columns_checkbox.isChecked())

        for column in columns:
            checkbox = QCheckBox(column)
            checkbox.setChecked(True)
            self.matching_column_checkboxes.append(checkbox)
            self.matching_columns_container_layout.addWidget(checkbox)

    def _toggle_matching_columns(self, checked: bool) -> None:
        self.matching_columns_container.setEnabled(not checked)
        if checked:
            for checkbox in self.matching_column_checkboxes:
                checkbox.setChecked(True)

    def _get_selected_matching_columns(self) -> list[str]:
        if self.use_all_columns_checkbox.isChecked():
            return []
        return [checkbox.text() for checkbox in self.matching_column_checkboxes if checkbox.isChecked()]

    def _run_comparison(self) -> None:
        if not self.left_path or not self.right_path:
            QMessageBox.warning(self, "Missing files", "Please select both File A and File B.")
            return

        try:
            if self.left_dataset is None or self.right_dataset is None:
                self.left_dataset = self.service.load_dataset(self.left_path)
                self.right_dataset = self.service.load_dataset(self.right_path)

            result = self.service.compare(
                self.left_dataset,
                self.right_dataset,
                ComparisonOptions(
                    matching_columns=self._get_selected_matching_columns(),
                    case_sensitive_values=True,
                ),
            )

            self.status_box.setPlainText(
                f"Loaded: {self.left_dataset.file_type} / {self.right_dataset.file_type}\n"
                f"Common columns: {result.schema.common_columns}\n"
                f"Only in A: {result.schema.columns_only_in_a}\n"
                f"Only in B: {result.schema.columns_only_in_b}"
            )

            self._render_schema(result)
            self._render_records(result)
        except Exception as exc:  # pragma: no cover - UI fail path
            QMessageBox.critical(self, "Comparison failed", str(exc))

    def _render_schema(self, result) -> None:
        self.schema_table.setRowCount(0)
        row_count = max(
            len(result.schema.common_columns),
            len(result.schema.columns_only_in_a),
            len(result.schema.columns_only_in_b),
        )
        self.schema_table.setRowCount(row_count)

        for row in range(row_count):
            common_value = result.schema.common_columns[row] if row < len(result.schema.common_columns) else ""
            only_a_value = result.schema.columns_only_in_a[row] if row < len(result.schema.columns_only_in_a) else ""
            only_b_value = result.schema.columns_only_in_b[row] if row < len(result.schema.columns_only_in_b) else ""
            self.schema_table.setItem(row, 0, QTableWidgetItem(common_value))
            self.schema_table.setItem(row, 1, QTableWidgetItem(only_a_value))
            self.schema_table.setItem(row, 2, QTableWidgetItem(only_b_value))

    def _render_records(self, result) -> None:
        self.record_result = result
        self._refresh_record_tables()

    def _refresh_record_tables(self) -> None:
        result = getattr(self, "record_result", None)
        if result is None:
            return

        record_groups = {
            "identical": result.common_identical_records,
            "changed": result.changed_records,
            "only_in_a": result.records_only_in_a,
            "only_in_b": result.records_only_in_b,
        }
        for key, records in record_groups.items():
            self._populate_record_table(self.record_tables[key], records, key)
            label = self.record_tabs.tabText(self.record_tabs.indexOf(self.record_tables[key])).split(" (")[0]
            self.record_tabs.setTabText(self.record_tabs.indexOf(self.record_tables[key]), f"{label} ({len(records)})")

    def _populate_record_table(self, table: QTableWidget, records: list[dict], group: str) -> None:
        if self.record_format_combo.currentText() == "JSON":
            table.setColumnCount(1)
            table.setHorizontalHeaderLabels(["Record details"])
            table.setRowCount(len(records))
            for row_index, record in enumerate(records):
                table.setItem(row_index, 0, QTableWidgetItem(json.dumps(record, default=str, indent=2)))
            table.setColumnWidth(0, 900)
            return

        rows, columns = self._column_rows(records, group)
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, column in enumerate(columns):
                table.setItem(row_index, column_index, QTableWidgetItem(str(row.get(column, ""))))

    def _column_rows(self, records: list[dict], group: str) -> tuple[list[dict], list[str]]:
        rows: list[dict] = []
        columns: list[str] = []

        for item in records:
            if group in {"identical", "changed"}:
                left_record = item.get("left_record", {})
                right_record = item.get("right_record", {})
                row = {f"A: {key}": value for key, value in left_record.items()}
                row.update({f"B: {key}": value for key, value in right_record.items()})
            else:
                source_record = item.get("record", {})
                prefix = "A: " if group == "only_in_a" else "B: "
                row = {f"{prefix}{key}": value for key, value in source_record.items()}
            rows.append(row)
            for column in row:
                if column not in columns:
                    columns.append(column)

        return rows, columns or ["No records"]


def main() -> None:
    app = QApplication([])
    window = DataReconWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
