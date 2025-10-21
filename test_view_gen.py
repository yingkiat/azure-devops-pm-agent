from src.ea.view_builder import ViewBuilder

builder = ViewBuilder()
result = builder.generate_views_from_specs()

print(f"\nResult: {result}")
