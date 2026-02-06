"""
File format converters for EA ingestion.

Converts various file formats to text/CSV for processing by EA discovery engine.
"""

import csv
import io
from pathlib import Path
from typing import Optional

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None


def xlsx_to_csv(file_path: str) -> str:
    """
    Convert XLSX file to CSV format text.

    Reads the first sheet from an XLSX workbook and converts it to proper CSV format,
    preserving cell boundaries (handles embedded commas and newlines correctly).

    Args:
        file_path: Path to the XLSX file

    Returns:
        CSV-formatted text with all rows and columns

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If openpyxl is not installed or file is not valid XLSX
    """
    if load_workbook is None:
        raise ValueError("openpyxl is required for XLSX support. Install with: pip install openpyxl")

    xlsx_path = Path(file_path)
    if not xlsx_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        # Load the workbook
        workbook = load_workbook(xlsx_path, data_only=True)

        # Get the first sheet
        sheet = workbook.active

        # Read all rows and convert to CSV
        output = io.StringIO()
        csv_writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')

        for row in sheet.iter_rows(values_only=True):
            # Convert None values to empty strings for proper CSV formatting
            cleaned_row = ['' if cell is None else str(cell) for cell in row]
            csv_writer.writerow(cleaned_row)

        workbook.close()

        csv_text = output.getvalue()
        output.close()

        return csv_text

    except Exception as e:
        raise ValueError(f"Failed to read XLSX file {file_path}: {e}")
