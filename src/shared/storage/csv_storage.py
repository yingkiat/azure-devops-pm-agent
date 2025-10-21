"""
CSV-based storage implementation for tabular data.

Provides file-based storage using CSV format, suitable for development
and small-to-medium datasets. Includes automatic backups and schema validation.
"""

import os
import pandas as pd
from typing import List, Dict, Any, Optional
from .base_storage import TabularStorageBase
import hashlib
from datetime import datetime


class CSVStorage(TabularStorageBase):
    """
    CSV file-based storage implementation.

    Features:
    - Automatic directory creation
    - Backup functionality
    - Schema validation (if schema_file provided)
    - Duplicate detection via hash columns
    """

    def __init__(self, file_path: str, schema_file: Optional[str] = None):
        """
        Initialize CSV storage.

        Args:
            file_path: Path to CSV file (will be created if doesn't exist)
            schema_file: Optional path to schema validation file
        """
        # Extract table name from file path
        table_name = os.path.splitext(os.path.basename(file_path))[0]
        super().__init__(table_name, schema_file)

        self.file_path = file_path
        self._ensure_directory_exists()

    def _ensure_directory_exists(self):
        """Create directory structure if it doesn't exist."""
        directory = os.path.dirname(self.file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _generate_row_hash(self, row_dict: Dict[str, Any]) -> str:
        """
        Generate a hash for a data row to detect duplicates.

        Args:
            row_dict: Dictionary representing a data row

        Returns:
            MD5 hash of the row content
        """
        # Remove hash and timestamp fields from hash calculation
        content_dict = {k: v for k, v in row_dict.items()
                       if k not in ['source_text_hash', 'last_updated']}

        # Sort keys for consistent hashing
        content_str = str(sorted(content_dict.items()))
        return hashlib.md5(content_str.encode()).hexdigest()[:8]

    def load_data(self) -> pd.DataFrame:
        """Load data from CSV file."""
        if os.path.exists(self.file_path):
            try:
                return pd.read_csv(self.file_path)
            except pd.errors.EmptyDataError:
                return pd.DataFrame()
        return pd.DataFrame()

    def save_data(self, df: pd.DataFrame) -> None:
        """Save DataFrame to CSV file."""
        # Create backup before saving
        if os.path.exists(self.file_path):
            self.backup_data()

        # Add metadata columns if they don't exist
        if not df.empty:
            if 'last_updated' not in df.columns:
                df['last_updated'] = datetime.now().strftime("%Y-%m-%d")

            if 'source_text_hash' not in df.columns:
                df['source_text_hash'] = df.apply(
                    lambda row: self._generate_row_hash(row.to_dict()), axis=1
                )

        df.to_csv(self.file_path, index=False)

    def upsert_rows(self, changes: List[Dict[str, Any]]) -> None:
        """
        Insert or update rows in the CSV.

        Uses app_name + capability as composite key for upserts.
        """
        if not changes:
            return

        df = self.load_data()

        for change in changes:
            # Add metadata
            change['last_updated'] = datetime.now().strftime("%Y-%m-%d")
            change['source_text_hash'] = self._generate_row_hash(change)

            # Find existing row (using app_name + capability as key)
            if not df.empty and 'app_name' in df.columns and 'capability' in df.columns:
                mask = (
                    (df['app_name'] == change.get('app_name', '')) &
                    (df['capability'] == change.get('capability', ''))
                )
                existing_rows = df[mask]

                if not existing_rows.empty:
                    # Update existing row
                    for key, value in change.items():
                        df.loc[mask, key] = value
                else:
                    # Insert new row
                    new_row_df = pd.DataFrame([change])
                    df = pd.concat([df, new_row_df], ignore_index=True)
            else:
                # First row or empty DataFrame
                new_row_df = pd.DataFrame([change])
                df = pd.concat([df, new_row_df], ignore_index=True)

        self.save_data(df)

    def delete_rows(self, conditions: Dict[str, Any]) -> None:
        """
        Delete rows matching all conditions.

        Args:
            conditions: Dictionary of field->value pairs for matching
        """
        if not conditions:
            return

        df = self.load_data()
        if df.empty:
            return

        # Build mask for rows to keep (NOT delete)
        keep_mask = pd.Series([True] * len(df))

        for field, value in conditions.items():
            if field in df.columns:
                keep_mask &= (df[field] != value)

        # Keep only rows that don't match the delete conditions
        df_filtered = df[keep_mask]
        self.save_data(df_filtered)

    def get_primary_keys(self) -> List[str]:
        """
        Get the primary key columns for this storage.

        Returns:
            List of column names that form the primary key
        """
        # For EA matrix, use app_name + capability as composite key
        return ['app_name', 'capability']

    def validate_schema(self, df: pd.DataFrame) -> List[str]:
        """
        Validate DataFrame against schema (if schema_file provided).

        Args:
            df: DataFrame to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        # TODO: Implement schema validation if schema_file is provided
        # For now, just basic validation
        errors = []

        required_columns = ['app_name', 'capability']
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")

        return errors