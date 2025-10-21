#!/usr/bin/env python3
"""
Manual CLI testing script for EA Discovery MVP.
Run this to test the CLI functionality step by step.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run a command and show results."""
    print(f"\n {description}")
    print(f"   Command: {' '.join(cmd)}")
    print("   " + "="*50)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            timeout=30
        )

        print(f"   Exit Code: {result.returncode}")

        if result.stdout:
            print("   STDOUT:")
            for line in result.stdout.split('\n')[:10]:  # First 10 lines
                print(f"     {line}")
            if len(result.stdout.split('\n')) > 10:
                print("     ... (truncated)")

        if result.stderr:
            print("   STDERR:")
            for line in result.stderr.split('\n')[:5]:  # First 5 lines
                print(f"     {line}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("    Command timed out")
        return False
    except Exception as e:
        print(f"    Error: {e}")
        return False

def check_file_exists(filepath, description):
    """Check if a file exists."""
    print(f"\n {description}")
    if Path(filepath).exists():
        size = Path(filepath).stat().st_size
        print(f"    Exists: {filepath} ({size} bytes)")

        # Show first few lines if it's a text file
        if filepath.endswith('.csv') or filepath.endswith('.yaml'):
            try:
                with open(filepath, 'r') as f:
                    lines = f.readlines()[:5]
                    print("   Content preview:")
                    for line in lines:
                        print(f"     {line.strip()}")
                    if len(lines) == 5:
                        print("     ... (truncated)")
            except Exception as e:
                print(f"     Could not read file: {e}")
        return True
    else:
        print(f"    Missing: {filepath}")
        return False

def main():
    """Run manual CLI tests."""
    print(" EA DISCOVERY CLI MANUAL TEST")
    print("="*60)

    # Change to project directory
    os.chdir(Path(__file__).parent)

    tests_passed = 0
    total_tests = 0

    # Test 1: Basic help
    total_tests += 1
    if run_command([sys.executable, "-m", "src.cli.main", "--help"], "Test main CLI help"):
        tests_passed += 1

    # Test 2: EA discover help
    total_tests += 1
    if run_command([sys.executable, "-m", "src.cli.main", "ea-discover", "--help"], "Test ea-discover help"):
        tests_passed += 1

    # Test 3: Check required files exist
    total_tests += 1
    if check_file_exists("prompts/ea/ea_discovery.md", "Check prompt file exists"):
        tests_passed += 1

    total_tests += 1
    if check_file_exists("data/ea/ea_schema.yaml", "Check schema file exists"):
        tests_passed += 1

    # Test 4: Simple discovery (will likely fail without AI, but should not crash)
    total_tests += 1
    print(f"\n Testing basic discovery (may fail without AI keys - that's OK)")
    if run_command([
        sys.executable, "-m", "src.cli.main", "ea-discover",
        "We have a simple test system"
    ], "Test basic discovery"):
        tests_passed += 1

    # Test 5: Check if matrix file was created
    total_tests += 1
    if check_file_exists("data/ea/ea_matrix.csv", "Check if matrix file was created"):
        tests_passed += 1

    # Test 6: No-matrix mode
    total_tests += 1
    if run_command([
        sys.executable, "-m", "src.cli.main", "ea-discover",
        "Test input", "--no-matrix"
    ], "Test no-matrix mode"):
        tests_passed += 1

    # Summary
    print("\n" + "="*60)
    print(f" RESULTS: {tests_passed}/{total_tests} tests passed")

    if tests_passed >= total_tests - 2:  # Allow 2 failures for AI-dependent tests
        print(" CLI appears to be working correctly!")
        print("\n Try these commands manually:")
        print("   python -m src.cli.main ea-discover --help")
        print("   python -m src.cli.main ea-discover \"We have a new CRM system\"")
    else:
        print(" Several tests failed. Check the output above.")

    print("\n Next steps:")
    print("   1. Set up real Azure OpenAI credentials in .env")
    print("   2. Test with actual AI responses")
    print("   3. Check data/ea/ea_matrix.csv for results")

if __name__ == "__main__":
    main()