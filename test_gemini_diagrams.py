#!/usr/bin/env python3
"""
Test script for Gemini-powered EA diagram generation.
Run this to test the new diagram generation functionality.
"""

import json
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_list_diagram_types():
    """Test listing available diagram types."""
    print(" Testing diagram type listing...")

    try:
        from ea.ea_diagrams import EADiagramGenerator

        generator = EADiagramGenerator()
        types = generator.list_supported_types()

        print(f" Found {len(types)} diagram types:")
        for dtype in types:
            print(f"   • {dtype}: {generator.get_diagram_info(dtype)}")

        return True
    except Exception as e:
        print(f" Failed to list diagram types: {e}")
        return False

def test_ea_data_loading():
    """Test loading EA data from sample file."""
    print("\n Testing EA data loading...")

    ea_file = Path("ea_outputs/ea_analysis.json")
    if not ea_file.exists():
        print(f" Sample EA file not found: {ea_file}")
        return False

    try:
        with open(ea_file, 'r') as f:
            ea_data = json.load(f)

        print(f" Loaded EA data with {len(ea_data)} layers:")
        for layer, content in ea_data.items():
            if isinstance(content, dict):
                print(f"   • {layer}: {len(content)} categories")
            else:
                print(f"   • {layer}: {type(content).__name__}")

        return True, ea_data
    except Exception as e:
        print(f" Failed to load EA data: {e}")
        return False, None

def test_gemini_client():
    """Test Gemini client initialization."""
    print("\n Testing Gemini client...")

    try:
        from utils.gemini_client import get_gemini_client

        client = get_gemini_client()
        print(f" Gemini client initialized with model: {client.model_name}")
        return True, client
    except Exception as e:
        print(f" Failed to initialize Gemini client: {e}")
        print("   Make sure GEMINI_API_KEY is set in your .env file")
        return False, None

def test_diagram_generation():
    """Test actual diagram generation (requires API key)."""
    print("\n Testing diagram generation...")

    # Load EA data
    success, ea_data = test_ea_data_loading()
    if not success:
        return False

    # Initialize client
    success, client = test_gemini_client()
    if not success:
        return False

    try:
        from ea.ea_diagrams import EADiagramGenerator

        generator = EADiagramGenerator()

        # Test with a simple overview diagram
        print("   Generating overview diagram...")
        result_path = generator.generate_diagram(ea_data, "overview")

        if Path(result_path).exists():
            file_size = Path(result_path).stat().st_size
            print(f" Diagram generated successfully: {result_path}")
            print(f"   File size: {file_size} bytes")

            # Show first few lines of the result
            try:
                with open(result_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    preview = content[:300] + "..." if len(content) > 300 else content
                    print(f"   Preview: {preview}")
            except Exception as read_err:
                print(f"    Could not read file preview: {read_err}")
                print(f"    But file was created successfully")

            return True
        else:
            print(f" Diagram file not created: {result_path}")
            return False

    except Exception as e:
        print(f" Failed to generate diagram: {e}")
        return False

def main():
    """Run all tests."""
    print(" Testing Gemini EA Diagram Generation\n")

    tests = [
        ("List Diagram Types", test_list_diagram_types),
        ("Load EA Data", lambda: test_ea_data_loading()[0]),
        ("Initialize Gemini Client", lambda: test_gemini_client()[0]),
        ("Generate Diagram", test_diagram_generation)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f" Running: {test_name}")
        print(f"{'='*50}")

        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f" Test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print(f"\n{'='*50}")
    print(" TEST SUMMARY")
    print(f"{'='*50}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = " PASS" if result else " FAIL"
        print(f"{status} {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n All tests passed! Gemini diagram generation is ready to use.")
        print("\nUsage examples:")
        print("  python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --list")
        print("  python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type overview")
        print("  python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type application")
    else:
        print(f"\n  {total - passed} tests failed. Check the errors above.")

if __name__ == "__main__":
    main()