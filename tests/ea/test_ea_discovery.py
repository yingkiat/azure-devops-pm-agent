"""
Test cases for EA Discovery engine.
"""

import pytest
import json
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ea.ea_discovery import EADiscovery


class TestEADiscovery:
    """Test EA Discovery functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Create test schema file
        self.schema_dir = Path(self.temp_dir) / "data" / "ea"
        self.schema_dir.mkdir(parents=True, exist_ok=True)

        schema_content = """
matrix_schema:
  columns:
    - name: app_name
      type: string
      required: true
    - name: capability
      type: string
      required: true
    - name: maturity
      type: integer
      range: [1, 5]
"""

        schema_file = self.schema_dir / "ea_schema.yaml"
        schema_file.write_text(schema_content)

        # Create discovery instance and manually set paths for testing
        self.discovery = EADiscovery()
        self.discovery.data_dir = self.schema_dir

        # Override storage with test storage
        from src.shared.storage.csv_storage import CSVStorage
        test_file = self.schema_dir / "test_matrix.csv"
        self.discovery.storage = CSVStorage(str(test_file))

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_schema(self):
        """Test schema loading functionality."""
        schema = self.discovery._load_schema()
        assert 'matrix_schema' in schema
        assert 'columns' in schema['matrix_schema']

    @patch('src.utils.openai_client.chat')
    @patch.object(EADiscovery, '_call_ai_with_matrix_context')
    def test_discover_and_update_matrix_success(self, mock_ai_call, mock_chat):
        """Test successful matrix discovery and update."""
        # Mock AI response directly
        mock_ai_response = {
            "discovery": {
                "applications": [
                    {
                        "name": "Customer Portal",
                        "description": "Modern web application for customer self-service",
                        "capabilities_supported": ["Account Management", "Billing Support"]
                    }
                ]
            },
            "changes": {
                "inserts": [
                    {
                        "app_name": "Customer Portal",
                        "capability": "Account Management",
                        "domain": "Sales",
                        "maturity": 4,
                        "lifecycle_status": "Strategic",
                        "remaining_years": 8,
                        "strategic_importance": "Critical"
                    }
                ],
                "updates": [],
                "deletes": []
            },
            "exploration": {
                "gap_analysis": "New customer portal fills self-service gap",
                "sunset_risks": "No immediate sunset risks identified",
                "maturity_trends": "Customer domain maturity improving",
                "overlaps": "No overlapping systems detected"
            },
            "recommendations": [
                "Monitor portal adoption rates",
                "Plan legacy system migration timeline"
            ]
        }
        mock_ai_call.return_value = mock_ai_response

        # Test discovery
        text_input = "We're implementing a new customer portal for account management"
        results = self.discovery.discover_and_update_matrix(text_input)

        # Verify results structure
        assert 'discovery' in results
        assert 'changes' in results
        assert 'exploration' in results
        assert 'recommendations' in results

        # Verify matrix was updated
        df = self.discovery.storage.load_data()
        assert len(df) == 1
        assert df.iloc[0]['app_name'] == 'Customer Portal'
        assert df.iloc[0]['capability'] == 'Account Management'
        assert df.iloc[0]['maturity'] == 4

    @patch.object(EADiscovery, '_call_ai_with_matrix_context')
    def test_discover_and_update_matrix_with_deletes(self, mock_ai_call):
        """Test matrix discovery with delete operations."""
        # First, add some existing data
        existing_data = [
            {
                'app_name': 'Legacy System',
                'capability': 'Old Process',
                'lifecycle_status': 'Maintain'
            }
        ]
        self.discovery.storage.upsert_rows(existing_data)

        # Mock AI response with delete operation
        mock_ai_response = {
            "discovery": {
                "applications": []
            },
            "changes": {
                "inserts": [],
                "updates": [],
                "deletes": [
                    {
                        "app_name": "Legacy System",
                        "capability": "Old Process"
                    }
                ]
            },
            "exploration": {
                "gap_analysis": "Legacy system being decommissioned",
                "sunset_risks": "Process gap needs to be addressed",
                "maturity_trends": "Modernization in progress",
                "overlaps": "No overlaps"
            },
            "recommendations": [
                "Ensure replacement system is in place"
            ]
        }
        mock_ai_call.return_value = mock_ai_response

        # Test discovery
        text_input = "We're decommissioning the legacy system"
        results = self.discovery.discover_and_update_matrix(text_input)

        # Verify matrix was updated (should be empty now)
        df = self.discovery.storage.load_data()
        assert len(df) == 0

    def test_format_matrix_results(self):
        """Test matrix results formatting."""
        results = {
            "changes": {
                "inserts": [
                    {
                        "app_name": "New App",
                        "capability": "New Feature",
                        "maturity": 3
                    }
                ],
                "updates": [
                    {
                        "app_name": "Existing App",
                        "capability": "Updated Feature"
                    }
                ],
                "deletes": [
                    {
                        "app_name": "Old App",
                        "capability": "Removed Feature"
                    }
                ]
            },
            "exploration": {
                "gap_analysis": "Some gaps found",
                "sunset_risks": "Some risks identified"
            },
            "recommendations": [
                "Do something important",
                "Monitor the situation"
            ]
        }

        formatted = self.discovery.format_matrix_results(results)

        assert "CHANGES APPLIED:" in formatted
        assert " Added: New App → New Feature" in formatted
        assert "  Updated: Existing App → Updated Feature" in formatted
        assert " Deleted:" in formatted
        assert "DATA EXPLORATION:" in formatted
        assert "RECOMMENDATIONS:" in formatted

    def test_get_matrix_summary_empty(self):
        """Test matrix summary when empty."""
        summary = self.discovery.get_matrix_summary()
        assert "EA Matrix is empty" in summary

    def test_get_matrix_summary_with_data(self):
        """Test matrix summary with data."""
        # Add test data
        test_data = [
            {
                'app_name': 'App1',
                'capability': 'Cap1',
                'domain': 'Finance',
                'maturity': 4,
                'lifecycle_status': 'Strategic'
            },
            {
                'app_name': 'App2',
                'capability': 'Cap2',
                'domain': 'Sales',
                'maturity': 3,
                'lifecycle_status': 'Maintain'
            }
        ]
        self.discovery.storage.upsert_rows(test_data)

        summary = self.discovery.get_matrix_summary()

        assert "EA MATRIX SUMMARY" in summary
        assert "Total Records: 2" in summary
        assert "Applications: 2" in summary
        assert "Capabilities: 2" in summary
        assert "Domains: 2" in summary
        assert "Strategic: 1" in summary
        assert "Maintain: 1" in summary
        assert "Average Maturity: 3.5" in summary

    @patch.object(EADiscovery, '_call_ai_with_matrix_context')
    def test_ai_error_handling(self, mock_ai_call):
        """Test handling of AI errors."""
        # Mock AI error
        mock_ai_call.side_effect = Exception("API Error")

        text_input = "Test input"
        results = self.discovery.discover_and_update_matrix(text_input)

        assert "error" in results
        assert "API Error" in str(results["error"])

    @patch.object(EADiscovery, '_call_ai_with_matrix_context')
    def test_json_parsing_error(self, mock_ai_call):
        """Test handling of invalid JSON from AI."""
        # Mock invalid response structure
        mock_ai_call.return_value = {"error": "Failed to parse JSON response"}

        text_input = "Test input"
        results = self.discovery.discover_and_update_matrix(text_input)

        assert "error" in results
        assert "Failed to parse JSON response" in results["error"]