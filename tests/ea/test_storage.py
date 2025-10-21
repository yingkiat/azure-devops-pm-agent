"""
Test cases for the shared storage layer.
"""

import pytest
import pandas as pd
import tempfile
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.shared.storage.csv_storage import CSVStorage


class TestCSVStorage:
    """Test CSV storage implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_matrix.csv")
        self.storage = CSVStorage(self.test_file)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_empty_data(self):
        """Test loading data when file doesn't exist."""
        df = self.storage.load_data()
        assert df.empty
        assert isinstance(df, pd.DataFrame)

    def test_save_and_load_data(self):
        """Test basic save and load operations."""
        # Create test data
        test_data = pd.DataFrame({
            'app_name': ['ERP System', 'CRM System'],
            'capability': ['Financial Reporting', 'Customer Management'],
            'domain': ['Finance', 'Sales'],
            'maturity': [5, 4],
            'lifecycle_status': ['Strategic', 'Maintain']
        })

        # Save data
        self.storage.save_data(test_data)

        # Load and verify
        loaded_data = self.storage.load_data()
        assert len(loaded_data) == 2
        assert loaded_data['app_name'].tolist() == ['ERP System', 'CRM System']
        assert 'last_updated' in loaded_data.columns  # Auto-added metadata

    def test_upsert_new_rows(self):
        """Test inserting new rows."""
        changes = [
            {
                'app_name': 'Customer Portal',
                'capability': 'Account Management',
                'domain': 'Sales',
                'maturity': 3,
                'lifecycle_status': 'Strategic'
            }
        ]

        self.storage.upsert_rows(changes)

        df = self.storage.load_data()
        assert len(df) == 1
        assert df.iloc[0]['app_name'] == 'Customer Portal'
        assert df.iloc[0]['capability'] == 'Account Management'

    def test_upsert_update_existing(self):
        """Test updating existing rows."""
        # Insert initial data
        initial_changes = [
            {
                'app_name': 'Legacy System',
                'capability': 'User Management',
                'maturity': 2,
                'lifecycle_status': 'Maintain'
            }
        ]
        self.storage.upsert_rows(initial_changes)

        # Update the same row
        update_changes = [
            {
                'app_name': 'Legacy System',
                'capability': 'User Management',
                'maturity': 1,
                'lifecycle_status': 'Sunset'
            }
        ]
        self.storage.upsert_rows(update_changes)

        df = self.storage.load_data()
        assert len(df) == 1  # Should still be 1 row
        assert df.iloc[0]['maturity'] == 1  # Updated value
        assert df.iloc[0]['lifecycle_status'] == 'Sunset'  # Updated value

    def test_delete_rows(self):
        """Test deleting rows by conditions."""
        # Insert test data
        changes = [
            {
                'app_name': 'System A',
                'capability': 'Feature X',
                'lifecycle_status': 'Strategic'
            },
            {
                'app_name': 'System B',
                'capability': 'Feature Y',
                'lifecycle_status': 'Sunset'
            }
        ]
        self.storage.upsert_rows(changes)

        # Delete sunset systems
        self.storage.delete_rows({'lifecycle_status': 'Sunset'})

        df = self.storage.load_data()
        assert len(df) == 1
        assert df.iloc[0]['app_name'] == 'System A'

    def test_get_data_context(self):
        """Test data context generation."""
        # Initially empty
        context = self.storage.get_data_context()
        assert "No existing data" in context

        # Add some data
        changes = [
            {
                'app_name': 'App1',
                'capability': 'Cap1',
                'maturity': 3
            },
            {
                'app_name': 'App2',
                'capability': 'Cap2',
                'maturity': 5
            }
        ]
        self.storage.upsert_rows(changes)

        context = self.storage.get_data_context()
        assert "Total records: 2" in context
        assert "app_name: 2 unique values" in context
        assert "maturity: range 3-5" in context

    def test_backup_data(self):
        """Test backup functionality."""
        # Add some data
        changes = [{'app_name': 'Test App', 'capability': 'Test Cap'}]
        self.storage.upsert_rows(changes)

        # Create backup
        backup_path = self.storage.backup_data("test_backup")

        # Verify backup exists and contains data
        assert os.path.exists(backup_path)
        backup_df = pd.read_csv(backup_path)
        assert len(backup_df) == 1
        assert backup_df.iloc[0]['app_name'] == 'Test App'