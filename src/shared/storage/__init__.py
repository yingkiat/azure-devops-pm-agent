"""
Shared storage abstraction layer for cross-persona data management.

This module provides a consistent interface for tabular data storage
that can be used by both PM and EA agents. Supports multiple storage
backends (CSV, SQLite, Azure SQL) with seamless migration paths.
"""

import os
from typing import Optional
from .base_storage import TabularStorageBase
from .csv_storage import CSVStorage


def get_storage(
    storage_type: str = None,
    table_name: str = "data_matrix",
    schema_file: str = None
) -> TabularStorageBase:
    """
    Factory function to create storage instances based on configuration.

    Args:
        storage_type: Type of storage ('csv', 'sqlite', 'azure').
                     Defaults to EA_STORAGE_TYPE env var or 'csv'
        table_name: Name of the table/file to store data
        schema_file: Path to schema configuration file

    Returns:
        Storage instance implementing TabularStorageBase
    """
    if storage_type is None:
        storage_type = os.getenv('EA_STORAGE_TYPE', 'csv')

    if storage_type == 'csv':
        return CSVStorage(
            file_path=f"data/{table_name}.csv",
            schema_file=schema_file
        )
    elif storage_type == 'sqlite':
        # Future implementation
        from .sqlite_storage import SQLiteStorage
        return SQLiteStorage(
            db_path="data/shared_database.db",
            table_name=table_name,
            schema_file=schema_file
        )
    elif storage_type == 'azure':
        # Future implementation
        from .azure_storage import AzureStorage
        return AzureStorage(
            connection_string=os.getenv('AZURE_SQL_CONNECTION'),
            table_name=table_name,
            schema_file=schema_file
        )
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")