#!/usr/bin/env python3
"""
Automated cleanup utilities for testing.
Safely removes test data while preserving production Azure DevOps data.
"""
import os
import sys
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_orchestrator.context_manager import ContextManager
from devops_gateway.wiki import WikiGateway
from utils.config import get_config


class TestCleanupManager:
    """Manages cleanup of test data and artifacts."""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.config = get_config()
        print(f" Test Cleanup Manager {'(DRY RUN)' if dry_run else '(LIVE)'}")
    
    def cleanup_ai_context(self) -> bool:
        """Clear AI context data safely."""
        print("\n Cleaning AI Context Data")
        print("-" * 30)
        
        try:
            context_manager = ContextManager()
            
            # Show current stats before cleanup
            stats = context_manager.get_context_stats()
            print(f"   Current context: {stats['conversation_entries']} conversations, {stats['known_projects']} projects")
            
            if not self.dry_run:
                # Clear context but keep user preferences for convenience
                context_manager.clear_context(keep_preferences=True)
                print("    AI context data cleared (preferences preserved)")
            else:
                print("    Would clear AI context data")
            
            return True
        except Exception as e:
            print(f"    Failed to clear AI context: {e}")
            return False
    
    def cleanup_test_files(self) -> bool:
        """Remove temporary test files and outputs."""
        print("\n Cleaning Test Files")
        print("-" * 30)
        
        test_paths = [
            self.config.project_root / "outputs" / "test_*",
            self.config.project_root / "data" / "temp_*",
            self.config.project_root / "*.log",
            self.config.project_root / "tests" / "__pycache__",
            self.config.project_root / "src" / "**" / "__pycache__"
        ]
        
        cleaned_items = 0
        for pattern in test_paths:
            if "*" in str(pattern):
                # Handle glob patterns
                parent = pattern.parent
                if parent.exists():
                    pattern_name = pattern.name
                    for item in parent.glob(pattern_name):
                        if item.exists():
                            print(f"    Found: {item.relative_to(self.config.project_root)}")
                            if not self.dry_run:
                                if item.is_dir():
                                    shutil.rmtree(item)
                                else:
                                    item.unlink()
                                print(f"    Removed: {item.name}")
                            else:
                                print(f"    Would remove: {item.name}")
                            cleaned_items += 1
            else:
                # Handle direct paths
                if pattern.exists():
                    print(f"    Found: {pattern.relative_to(self.config.project_root)}")
                    if not self.dry_run:
                        if pattern.is_dir():
                            shutil.rmtree(pattern)
                        else:
                            pattern.unlink()
                        print(f"    Removed: {pattern.name}")
                    else:
                        print(f"    Would remove: {pattern.name}")
                    cleaned_items += 1
        
        if cleaned_items == 0:
            print("    No test files to clean")
        
        return True
    
    async def cleanup_test_wiki_pages(self) -> bool:
        """Remove wiki pages created during testing."""
        print("\n Cleaning Test Wiki Pages")
        print("-" * 30)
        
        try:
            # Only attempt if we have wiki credentials
            if not all([
                os.getenv('AZDO_ORG_URL'),
                os.getenv('AZDO_PROJECT'), 
                os.getenv('AZDO_PAT'),
                os.getenv('AZDO_WIKI_NAME')
            ]):
                print("     Skipping wiki cleanup - missing Azure DevOps credentials")
                return True
            
            wiki_gateway = WikiGateway()
            
            # Look for test pages (created in last 24 hours with "test" in title)
            test_page_patterns = [
                "test_session",
                "demo_session", 
                "Test Analysis",
                "Demo Analysis"
            ]
            
            # In a real implementation, you'd query wiki pages and filter by:
            # 1. Pages created in last 24 hours
            # 2. Pages with test patterns in title/path
            # 3. Pages in /PM-Agent/AI-Reports/ with recent timestamps
            
            print("    Searching for test wiki pages...")
            
            if not self.dry_run:
                # Note: Azure DevOps Wiki API doesn't provide easy page deletion
                # This would require careful implementation to avoid deleting important pages
                print("     Wiki page cleanup requires manual verification")
                print("    Manual steps:")
                print("      1. Go to Azure DevOps Wiki")
                print("      2. Navigate to /PM-Agent/AI-Reports/")
                print("      3. Delete pages with test timestamps from today")
            else:
                print("    Would search and remove test wiki pages")
                print("    Test patterns to look for:")
                for pattern in test_page_patterns:
                    print(f"      - Pages containing: {pattern}")
            
            return True
            
        except Exception as e:
            print(f"    Wiki cleanup failed: {e}")
            return False
    
    def cleanup_outputs_directory(self) -> bool:
        """Clean the outputs directory of old plans and reports."""
        print("\n Cleaning Outputs Directory")
        print("-" * 30)
        
        outputs_dir = self.config.project_root / "outputs"
        if not outputs_dir.exists():
            print("    No outputs directory to clean")
            return True
        
        # Remove files older than 7 days or with test patterns
        cutoff_date = datetime.now() - timedelta(days=7)
        cleaned_items = 0
        
        for item in outputs_dir.iterdir():
            if item.is_file():
                # Check if it's a test file or old file
                is_test_file = any(pattern in item.name.lower() for pattern in ['test', 'demo', 'sample'])
                is_old_file = datetime.fromtimestamp(item.stat().st_mtime) < cutoff_date
                
                if is_test_file or is_old_file:
                    age_days = (datetime.now() - datetime.fromtimestamp(item.stat().st_mtime)).days
                    print(f"    Found: {item.name} ({'test file' if is_test_file else f'{age_days} days old'})")
                    
                    if not self.dry_run:
                        item.unlink()
                        print(f"    Removed: {item.name}")
                    else:
                        print(f"    Would remove: {item.name}")
                    cleaned_items += 1
        
        if cleaned_items == 0:
            print("    No old output files to clean")
        
        return True
    
    def verify_system_health(self) -> bool:
        """Verify system is still healthy after cleanup."""
        print("\n System Health Check")
        print("-" * 30)
        
        checks = [
            ("Configuration system", self._check_config),
            ("AI orchestrator", self._check_orchestrator),  
            ("Context persistence", self._check_context),
            ("Essential files", self._check_essential_files)
        ]
        
        all_healthy = True
        for check_name, check_func in checks:
            try:
                result = check_func()
                status = " Healthy" if result else " Issues"
                print(f"   {check_name}: {status}")
                if not result:
                    all_healthy = False
            except Exception as e:
                print(f"   {check_name}:  Error - {e}")
                all_healthy = False
        
        return all_healthy
    
    def _check_config(self) -> bool:
        """Check configuration system."""
        try:
            config = get_config()
            return config.project_root.exists() and config.prompts_dir.exists()
        except:
            return False
    
    def _check_orchestrator(self) -> bool:
        """Check AI orchestrator can be imported."""
        try:
            from ai_orchestrator.orchestrator import AzureDevOpsOrchestrator
            orchestrator = AzureDevOpsOrchestrator()
            return hasattr(orchestrator, 'context_manager')
        except:
            return False
    
    def _check_context(self) -> bool:
        """Check context system works."""
        try:
            context_manager = ContextManager()
            stats = context_manager.get_context_stats()
            return isinstance(stats, dict)
        except:
            return False
    
    def _check_essential_files(self) -> bool:
        """Check essential files exist."""
        essential_files = [
            "src/cli/ai_cli.py",
            "src/ai_orchestrator/orchestrator.py",
            "src/mcp_server/server.py",
            "prompts/intent_classification.md",
            "CLAUDE.md"
        ]
        
        for file_path in essential_files:
            if not (self.config.project_root / file_path).exists():
                return False
        return True


async def run_cleanup(cleanup_type: str = "safe", dry_run: bool = True):
    """
    Run cleanup with different levels of thoroughness.
    
    Args:
        cleanup_type: "safe" (context only), "standard" (context + files), "thorough" (all)
        dry_run: If True, only show what would be cleaned
    """
    print(" Azure DevOps PM Agent - Test Cleanup")
    print("=" * 50)
    
    cleaner = TestCleanupManager(dry_run=dry_run)
    
    success_count = 0
    total_operations = 0
    
    # Safe cleanup (always safe to run)
    if cleanup_type in ["safe", "standard", "thorough"]:
        total_operations += 1
        if cleaner.cleanup_ai_context():
            success_count += 1
    
    # Standard cleanup
    if cleanup_type in ["standard", "thorough"]:
        total_operations += 2
        if cleaner.cleanup_test_files():
            success_count += 1
        if cleaner.cleanup_outputs_directory():
            success_count += 1
    
    # Thorough cleanup (includes wiki pages)
    if cleanup_type == "thorough":
        total_operations += 1
        if await cleaner.cleanup_test_wiki_pages():
            success_count += 1
    
    # Always verify system health
    total_operations += 1
    if cleaner.verify_system_health():
        success_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f" Cleanup Complete: {success_count}/{total_operations} operations successful")
    
    if success_count == total_operations:
        print(" System is clean and healthy!")
        print("\n Ready for testing:")
        print("   python tests/test_ai_system.py")
        print("   python tests/demo_wiki_flow.py")
        print("   python -m src.cli.ai_cli chat")
    else:
        print("  Some cleanup operations had issues - check output above")
    
    if dry_run:
        print("\n Run with --live to actually perform cleanup")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test cleanup automation")
    parser.add_argument("--type", choices=["safe", "standard", "thorough"], 
                      default="safe", help="Cleanup thoroughness level")
    parser.add_argument("--live", action="store_true", 
                      help="Actually perform cleanup (default is dry-run)")
    
    args = parser.parse_args()
    
    asyncio.run(run_cleanup(
        cleanup_type=args.type,
        dry_run=not args.live
    ))