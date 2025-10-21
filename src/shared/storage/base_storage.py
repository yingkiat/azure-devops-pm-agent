"""
Abstract base class for tabular data storage.

Defines the interface that all storage implementations must follow,
ensuring consistent behavior across CSV, SQLite, and Azure SQL backends.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd


class TabularStorageBase(ABC):
    """
    Abstract interface for tabular data storage operations.

    All storage implementations (CSV, SQLite, Azure SQL) must implement
    these methods to ensure consistent CRUD operations and data management.
    """

    def __init__(self, table_name: str, schema_file: Optional[str] = None):
        """
        Initialize storage with table name and optional schema.

        Args:
            table_name: Name of the table/file to store data
            schema_file: Path to schema configuration file (optional)
        """
        self.table_name = table_name
        self.schema_file = schema_file

    @abstractmethod
    def load_data(self) -> pd.DataFrame:
        """
        Load the current data from storage.

        Returns:
            DataFrame containing all current data, empty if no data exists
        """
        pass

    @abstractmethod
    def save_data(self, df: pd.DataFrame) -> None:
        """
        Save the complete dataset to storage.

        Args:
            df: DataFrame to save (replaces existing data)
        """
        pass

    @abstractmethod
    def upsert_rows(self, changes: List[Dict[str, Any]]) -> None:
        """
        Apply INSERT/UPDATE operations for multiple rows.

        Args:
            changes: List of dictionaries representing rows to insert/update.
                    Uses primary key(s) to determine insert vs update.
        """
        pass

    @abstractmethod
    def delete_rows(self, conditions: Dict[str, Any]) -> None:
        """
        Delete rows matching the given conditions.

        Args:
            conditions: Dictionary of field->value pairs for row matching.
                       Rows matching ALL conditions will be deleted.
        """
        pass

    def get_data_context(self) -> str:
        """
        Generate summary context about the current data for AI processing.

        Returns:
            String summary of data dimensions, patterns, etc.
        """
        df = self.load_data()
        if df.empty:
            return "No existing data in storage."

        context_parts = [
            f"Total records: {len(df)}",
        ]

        # Add column summaries if data exists
        if not df.empty:
            for col in df.columns:
                if df[col].dtype in ['object', 'string']:
                    unique_count = df[col].nunique()
                    context_parts.append(f"{col}: {unique_count} unique values")
                elif df[col].dtype in ['int64', 'float64']:
                    context_parts.append(f"{col}: range {df[col].min()}-{df[col].max()}")

        return "; ".join(context_parts)

    def backup_data(self, backup_suffix: str = None) -> str:
        """
        Create a backup of current data.

        Args:
            backup_suffix: Optional suffix for backup filename

        Returns:
            Path to backup file created
        """
        # Default implementation - can be overridden by specific storage types
        from datetime import datetime

        if backup_suffix is None:
            backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

        df = self.load_data()
        backup_path = f"data/backups/{self.table_name}_{backup_suffix}.csv"

        import os
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        df.to_csv(backup_path, index=False)

        return backup_path