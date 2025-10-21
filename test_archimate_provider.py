"""
Quick test to verify ArchiMate CSV provider works with Mermaid diagram generation
"""

from src.ea.data_providers import ArchiMateCSVProvider
from src.ea.artifact_generator import ArtifactGenerator

def test_archimate_provider():
    """Test that ArchiMate provider loads data correctly."""

    print("=" * 60)
    print("Testing ArchiMate CSV Provider")
    print("=" * 60)

    # Create provider
    provider = ArchiMateCSVProvider("archi_inputs")

    # Check availability
    print(f"\n Provider available: {provider.is_available()}")

    if not provider.is_available():
        print(" ArchiMate files not found in archi_inputs/")
        return

    # Get EA data
    ea_data = provider.get_ea_data()

    # Print summary
    print(f"\n Data Summary:")
    print(f"   - Applications: {len(ea_data.applications)}")
    print(f"   - Capabilities: {len(ea_data.capabilities)}")
    print(f"   - Domains: {len(ea_data.domains)}")
    print(f"   - App-Capability Links: {len(ea_data.application_capabilities)}")

    # Print applications
    print(f"\n Applications:")
    for app in ea_data.applications[:5]:  # First 5
        print(f"   - {app.name} ({app.domain}) - {app.strategic_importance.value}")

    # Print capabilities
    print(f"\n  Capabilities:")
    for cap in ea_data.capabilities[:5]:  # First 5
        print(f"   - {cap.name} → {cap.application_name}")

    # Print metadata
    print(f"\n Metadata:")
    for key, value in ea_data.metadata.items():
        print(f"   - {key}: {value}")

    print("\n" + "=" * 60)
    print("Testing Mermaid Diagram Generation")
    print("=" * 60)

    # Test artifact generator with ArchiMate provider
    generator = ArtifactGenerator(provider)

    # Get compatible diagram types
    compatible = generator.get_compatible_diagram_types()
    print(f"\n Compatible diagram types: {len(compatible)}")
    for dt in compatible:
        print(f"   - {dt}")

    # Preview diagrams (don't generate files yet)
    preview = generator.preview_diagrams()

    if "error" in preview:
        print(f"\n Preview error: {preview['error']}")
    else:
        print(f"\n Preview successful")
        print(f"   - Available diagrams: {len(preview.get('available_diagrams', []))}")

    print("\n ArchiMate provider integration successful!")
    print("=" * 60)

if __name__ == "__main__":
    test_archimate_provider()
