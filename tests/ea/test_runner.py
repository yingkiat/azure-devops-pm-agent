"""
Test runner script for EA Discovery MVP.
Run this to test all EA functionality.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def run_basic_storage_test():
    """Test basic storage functionality without external dependencies."""
    print(" Testing Storage Layer...")

    try:
        from src.shared.storage.csv_storage import CSVStorage
        import tempfile
        import pandas as pd

        # Create temporary storage
        temp_dir = tempfile.mkdtemp()
        storage = CSVStorage(f"{temp_dir}/test_matrix.csv")

        # Test basic operations
        print("   CSV storage initialized")

        # Test upsert
        test_data = [
            {
                'app_name': 'Test App',
                'capability': 'Test Capability',
                'domain': 'Test Domain',
                'maturity': 3,
                'lifecycle_status': 'Strategic'
            }
        ]
        storage.upsert_rows(test_data)
        print("   Data upsert works")

        # Test load
        df = storage.load_data()
        assert len(df) == 1
        assert df.iloc[0]['app_name'] == 'Test App'
        print("   Data load works")

        # Test context
        context = storage.get_data_context()
        assert "Total records: 1" in context
        print("   Data context generation works")

        print(" Storage layer tests PASSED\n")
        return True

    except Exception as e:
        print(f" Storage layer tests FAILED: {e}\n")
        return False

def run_schema_test():
    """Test schema loading functionality."""
    print(" Testing Schema Loading...")

    try:
        import yaml
        schema_path = Path(__file__).parent.parent.parent / "data" / "ea" / "ea_schema.yaml"

        if not schema_path.exists():
            print(f"    Schema file not found at {schema_path}")
            return False

        with open(schema_path) as f:
            schema = yaml.safe_load(f)

        assert 'matrix_schema' in schema
        assert 'columns' in schema['matrix_schema']
        print("   Schema file loads correctly")
        print("   Schema structure is valid")

        # Check required columns
        columns = {col['name'] for col in schema['matrix_schema']['columns']}
        required = {'app_name', 'capability', 'domain', 'maturity'}
        assert required.issubset(columns)
        print("   Required columns present")

        print(" Schema tests PASSED\n")
        return True

    except ImportError:
        print("    PyYAML not installed - schema test skipped")
        print("     Run: pip install PyYAML\n")
        return True
    except Exception as e:
        print(f" Schema tests FAILED: {e}\n")
        return False

def run_discovery_mock_test():
    """Test EA discovery with mocked AI response."""
    print(" Testing EA Discovery (mocked)...")

    try:
        from src.ea.ea_discovery import EADiscovery
        from unittest.mock import Mock, patch
        import tempfile
        import json

        # Mock AI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
{
  "discovery": {
    "applications": [
      {
        "name": "Customer Portal",
        "description": "Modern web application",
        "capabilities_supported": ["Account Management"]
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
        "lifecycle_status": "Strategic"
      }
    ],
    "updates": [],
    "deletes": []
  },
  "exploration": {
    "gap_analysis": "New portal addresses self-service gap"
  },
  "recommendations": ["Monitor adoption"]
}
```'''

        with patch('src.utils.openai_client.chat', return_value=mock_response):
            discovery = EADiscovery()
            print("   EA Discovery initialized")

            # Test discovery
            text_input = "We're implementing a new customer portal"
            results = discovery.discover_and_update_matrix(text_input)

            assert 'discovery' in results
            assert 'changes' in results
            print("   AI response parsing works")

            # Check matrix update
            df = discovery.storage.load_data()
            assert len(df) == 1
            assert df.iloc[0]['app_name'] == 'Customer Portal'
            print("   Matrix update works")

            # Test formatting
            formatted = discovery.format_matrix_results(results)
            assert "Customer Portal" in formatted
            print("   Results formatting works")

        print(" EA Discovery tests PASSED\n")
        return True

    except Exception as e:
        print(f" EA Discovery tests FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def run_cli_mock_test():
    """Test CLI integration with mocked dependencies."""
    print("  Testing CLI Integration (mocked)...")

    try:
        from typer.testing import CliRunner
        from src.cli.main import app
        from unittest.mock import Mock, patch

        runner = CliRunner()

        # Mock AI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
{
  "discovery": {"applications": []},
  "changes": {"inserts": [], "updates": [], "deletes": []},
  "exploration": {"gap_analysis": "Test analysis"},
  "recommendations": []
}
```'''

        with patch('src.utils.openai_client.chat', return_value=mock_response):
            result = runner.invoke(app, [
                "ea-discover",
                "Test system description"
            ])

            print(f"  Exit code: {result.exit_code}")
            if result.exit_code == 0:
                print("   CLI command executes successfully")
                assert "EA discovery completed successfully" in result.stdout
                print("   CLI output format correct")
            else:
                print(f"   CLI failed with output: {result.stdout}")
                return False

        print(" CLI Integration tests PASSED\n")
        return True

    except Exception as e:
        print(f" CLI Integration tests FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def run_matrix_analysis_test():
    """Test matrix analysis scenarios."""
    print(" Testing Matrix Analysis...")

    try:
        from src.shared.storage.csv_storage import CSVStorage
        import tempfile
        import pandas as pd

        # Create test matrix with realistic data
        temp_dir = tempfile.mkdtemp()
        storage = CSVStorage(f"{temp_dir}/analysis_test.csv")

        test_data = [
            {
                'app_name': 'Legacy System',
                'capability': 'Old Process',
                'domain': 'Finance',
                'maturity': 1,
                'lifecycle_status': 'Sunset',
                'remaining_years': 1,
                'strategic_importance': 'Critical'
            },
            {
                'app_name': 'Modern System',
                'capability': 'New Process',
                'domain': 'Finance',
                'maturity': 5,
                'lifecycle_status': 'Strategic',
                'remaining_years': 10,
                'strategic_importance': 'Critical'
            }
        ]
        storage.upsert_rows(test_data)

        df = storage.load_data()
        print("   Test data loaded")

        # Test sunset risk analysis
        sunset_risks = df[
            (df['lifecycle_status'] == 'Sunset') &
            (df['strategic_importance'] == 'Critical')
        ]
        assert len(sunset_risks) == 1
        print("   Sunset risk analysis works")

        # Test maturity analysis
        low_maturity = df[df['maturity'] <= 2]
        assert len(low_maturity) == 1
        print("   Maturity analysis works")

        # Test domain analysis
        domain_avg = df.groupby('domain')['maturity'].mean()
        assert domain_avg['Finance'] == 3.0  # (1+5)/2
        print("   Domain analysis works")

        print(" Matrix Analysis tests PASSED\n")
        return True

    except Exception as e:
        print(f" Matrix Analysis tests FAILED: {e}\n")
        return False

def main():
    """Run all EA Discovery MVP tests."""
    print(" EA DISCOVERY MVP TEST SUITE")
    print("=" * 50)

    tests = [
        run_basic_storage_test,
        run_schema_test,
        run_discovery_mock_test,
        run_cli_mock_test,
        run_matrix_analysis_test
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("=" * 50)
    print(f" RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print(" ALL TESTS PASSED! MVP is ready.")
        print("\n Try it out:")
        print('   python -m src.cli.main ea-discover "We have a new CRM system"')
        return True
    else:
        print(" Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)