"""
Test realistic EA Matrix scenarios and use cases.
"""

import pytest
import pandas as pd
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.shared.storage.csv_storage import CSVStorage


class TestEAMatrixScenarios:
    """Test realistic enterprise architecture scenarios."""

    def setup_method(self):
        """Set up test fixtures with realistic data."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = CSVStorage(f"{self.temp_dir}/ea_matrix.csv")

        # Load initial realistic EA matrix
        self.initial_data = [
            {
                'app_name': 'SAP ERP',
                'capability': 'Financial Reporting',
                'domain': 'Finance',
                'maturity': 4,
                'lifecycle_status': 'Strategic',
                'remaining_years': 10,
                'strategic_importance': 'Critical'
            },
            {
                'app_name': 'SAP ERP',
                'capability': 'Procurement',
                'domain': 'Operations',
                'maturity': 4,
                'lifecycle_status': 'Strategic',
                'remaining_years': 10,
                'strategic_importance': 'Critical'
            },
            {
                'app_name': 'Legacy HR System',
                'capability': 'Employee Management',
                'domain': 'HR',
                'maturity': 2,
                'lifecycle_status': 'Sunset',
                'remaining_years': 1,
                'strategic_importance': 'Important'
            },
            {
                'app_name': 'Salesforce CRM',
                'capability': 'Customer Management',
                'domain': 'Sales',
                'maturity': 5,
                'lifecycle_status': 'Strategic',
                'remaining_years': 8,
                'strategic_importance': 'Critical'
            },
            {
                'app_name': 'Excel Spreadsheets',
                'capability': 'Reporting',
                'domain': 'Finance',
                'maturity': 1,
                'lifecycle_status': 'Sunset',
                'remaining_years': 0,
                'strategic_importance': 'Nice-to-Have'
            }
        ]
        self.storage.upsert_rows(self.initial_data)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sunset_risk_analysis(self):
        """Test identifying sunset risks in the matrix."""
        df = self.storage.load_data()

        # Find systems with high risk (sunset + critical/important)
        sunset_critical = df[
            (df['lifecycle_status'] == 'Sunset') &
            (df['strategic_importance'].isin(['Critical', 'Important']))
        ]

        assert len(sunset_critical) == 1  # Legacy HR System
        assert sunset_critical.iloc[0]['app_name'] == 'Legacy HR System'

        # Find systems ending soon
        ending_soon = df[df['remaining_years'] <= 1]
        assert len(ending_soon) == 2  # Legacy HR + Excel

    def test_capability_gap_analysis(self):
        """Test identifying capability gaps."""
        df = self.storage.load_data()

        # Find capabilities with low maturity (< 3)
        low_maturity = df[df['maturity'] < 3]
        assert len(low_maturity) == 2  # Legacy HR (2) + Excel (1)

        # Find domains with few applications
        domain_counts = df.groupby('domain')['app_name'].nunique()
        understaffed_domains = domain_counts[domain_counts < 2]
        assert 'HR' in understaffed_domains.index  # Only 1 app
        assert 'Sales' in understaffed_domains.index  # Only 1 app

    def test_overlap_detection(self):
        """Test detecting overlapping capabilities."""
        df = self.storage.load_data()

        # Find capabilities supported by multiple systems
        capability_counts = df.groupby('capability')['app_name'].nunique()
        overlapping = capability_counts[capability_counts > 1]

        # In our test data, no overlaps exist initially
        assert len(overlapping) == 0

        # Add overlapping system
        new_system = [
            {
                'app_name': 'Power BI',
                'capability': 'Reporting',
                'domain': 'Finance',
                'maturity': 4,
                'lifecycle_status': 'Strategic'
            }
        ]
        self.storage.upsert_rows(new_system)

        # Now check for overlaps
        df = self.storage.load_data()
        capability_counts = df.groupby('capability')['app_name'].nunique()
        overlapping = capability_counts[capability_counts > 1]
        assert 'Reporting' in overlapping.index  # Excel + Power BI

    def test_modernization_priority_matrix(self):
        """Test creating a modernization priority matrix."""
        df = self.storage.load_data()

        # Priority = (6 - maturity) * importance_weight + urgency_weight
        importance_weights = {'Critical': 3, 'Important': 2, 'Nice-to-Have': 1}
        urgency_weights = df['remaining_years'].apply(lambda x: 3 if x <= 2 else 1)

        df['importance_weight'] = df['strategic_importance'].map(importance_weights)
        df['urgency_weight'] = urgency_weights
        df['modernization_priority'] = (6 - df['maturity']) * df['importance_weight'] + df['urgency_weight']

        # Sort by priority (higher = more urgent)
        priority_order = df.sort_values('modernization_priority', ascending=False)

        # Legacy HR should be high priority (low maturity + important + urgent)
        assert priority_order.iloc[0]['app_name'] == 'Legacy HR System'

        # Excel should be next (very low maturity but low importance)
        top_priorities = priority_order.head(2)['app_name'].tolist()
        assert 'Excel Spreadsheets' in top_priorities

    def test_domain_maturity_dashboard(self):
        """Test creating domain maturity metrics."""
        df = self.storage.load_data()

        # Calculate domain-level metrics
        domain_metrics = df.groupby('domain').agg({
            'maturity': ['mean', 'min', 'max', 'count'],
            'app_name': 'nunique'
        }).round(2)

        domain_metrics.columns = ['avg_maturity', 'min_maturity', 'max_maturity', 'total_mappings', 'unique_apps']

        # Finance domain should have mixed maturity (SAP=4, Excel=1)
        finance_metrics = domain_metrics.loc['Finance']
        assert finance_metrics['avg_maturity'] == 2.5  # (4+1)/2
        assert finance_metrics['min_maturity'] == 1
        assert finance_metrics['max_maturity'] == 4

        # Sales domain should have high maturity (Salesforce=5)
        sales_metrics = domain_metrics.loc['Sales']
        assert sales_metrics['avg_maturity'] == 5.0

    def test_replacement_scenario(self):
        """Test system replacement scenario."""
        # Scenario: Replace Legacy HR with modern HR system

        # Add new HR system
        new_hr = [
            {
                'app_name': 'Workday HCM',
                'capability': 'Employee Management',
                'domain': 'HR',
                'maturity': 5,
                'lifecycle_status': 'Strategic',
                'remaining_years': 10,
                'strategic_importance': 'Critical'
            }
        ]
        self.storage.upsert_rows(new_hr)

        # Remove legacy system
        self.storage.delete_rows({'app_name': 'Legacy HR System'})

        # Verify replacement
        df = self.storage.load_data()
        hr_systems = df[df['domain'] == 'HR']

        assert len(hr_systems) == 1
        assert hr_systems.iloc[0]['app_name'] == 'Workday HCM'
        assert hr_systems.iloc[0]['maturity'] == 5

        # Check domain improvement
        hr_avg_maturity = hr_systems['maturity'].mean()
        assert hr_avg_maturity == 5.0  # Improved from 2

    def test_portfolio_rationalization(self):
        """Test portfolio rationalization analysis."""
        df = self.storage.load_data()

        # Categorize applications for rationalization
        def categorize_app(row):
            if row['lifecycle_status'] == 'Sunset':
                return 'ELIMINATE'
            elif row['maturity'] >= 4 and row['strategic_importance'] == 'Critical':
                return 'INVEST'
            elif row['maturity'] <= 2:
                return 'REPLACE'
            else:
                return 'MAINTAIN'

        df['rationalization_category'] = df.apply(categorize_app, axis=1)

        # Check categorization
        categories = df.groupby('rationalization_category')['app_name'].apply(list)

        assert 'SAP ERP' in categories.get('INVEST', [])
        assert 'Salesforce CRM' in categories.get('INVEST', [])
        assert 'Legacy HR System' in categories.get('ELIMINATE', [])
        assert 'Excel Spreadsheets' in categories.get('ELIMINATE', [])

    def test_capability_coverage_matrix(self):
        """Test capability coverage analysis."""
        df = self.storage.load_data()

        # Create capability coverage matrix
        coverage_matrix = df.pivot_table(
            values='maturity',
            index='capability',
            columns='domain',
            fill_value=0,
            aggfunc='max'  # Use highest maturity if multiple apps
        )

        # Check coverage gaps (domains without certain capabilities)
        expected_capabilities = ['Employee Management', 'Customer Management', 'Financial Reporting']
        expected_domains = ['HR', 'Sales', 'Finance', 'Operations']

        for capability in expected_capabilities:
            for domain in expected_domains:
                coverage = coverage_matrix.loc[capability, domain] if domain in coverage_matrix.columns else 0
                # This would help identify cross-domain capability gaps

        # Finance domain should have reporting capabilities
        assert coverage_matrix.loc['Financial Reporting', 'Finance'] == 4  # SAP ERP

    def test_technology_debt_analysis(self):
        """Test technology debt identification."""
        df = self.storage.load_data()

        # Identify tech debt (low maturity + strategic importance)
        tech_debt_score = df.apply(
            lambda row: (6 - row['maturity']) * ({'Critical': 3, 'Important': 2, 'Nice-to-Have': 1}[row['strategic_importance']]),
            axis=1
        )

        df['tech_debt_score'] = tech_debt_score
        high_debt = df[df['tech_debt_score'] >= 6].sort_values('tech_debt_score', ascending=False)

        # Legacy HR should have highest tech debt (maturity=2, importance=Important)
        assert high_debt.iloc[0]['app_name'] == 'Legacy HR System'
        assert high_debt.iloc[0]['tech_debt_score'] == 8  # (6-2) * 2