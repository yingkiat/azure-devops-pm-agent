"""Test deduplication logic"""

# Simulate the merge logic
merged = {"discovery": {}}
seen_elements = {}

# Simulate 3 discovery files with MedQuote
files_data = [
    {
        "discovery": {
            "ApplicationComponent": [
                {"name": "MedQuote", "description": "Custom quoting system for SPT sales"}
            ]
        }
    },
    {
        "discovery": {
            "ApplicationComponent": [
                {"name": "MedQuote", "description": "For SPT sales, quoting"}
            ]
        }
    },
    {
        "discovery": {
            "ApplicationComponent": [
                {"name": "MedQuote", "description": "Legacy sales application"}
            ]
        }
    }
]

# Merge logic from _merge_discoveries
for file_idx, data in enumerate(files_data):
    print(f"\n=== Processing File {file_idx + 1} ===")

    discovery = data.get('discovery', {})
    for element_type, items in discovery.items():
        if not isinstance(items, list):
            continue

        if element_type not in merged["discovery"]:
            merged["discovery"][element_type] = []

        for item in items:
            if isinstance(item, dict):
                name = item.get('name')
                key = (element_type, name)

                if key not in seen_elements:
                    # First occurrence
                    print(f"  NEW: {name} - adding to index {len(merged['discovery'][element_type])}")
                    seen_elements[key] = len(merged["discovery"][element_type])
                    merged["discovery"][element_type].append(item)
                else:
                    # Duplicate
                    existing_idx = seen_elements[key]
                    print(f"  DUP: {name} - merging into index {existing_idx}")
                    existing = merged["discovery"][element_type][existing_idx]

                    existing_desc = existing.get('description', '')
                    new_desc = item.get('description', '')

                    if new_desc and new_desc != existing_desc:
                        if existing_desc:
                            combined = f"{existing_desc}; {new_desc}"
                            existing['description'] = combined
                            print(f"    Combined: {combined}")
                        else:
                            existing['description'] = new_desc

print(f"\n=== Final Result ===")
print(f"Total ApplicationComponents: {len(merged['discovery']['ApplicationComponent'])}")
for idx, item in enumerate(merged['discovery']['ApplicationComponent']):
    print(f"  {idx}: {item['name']} - {item.get('description', 'NO DESC')}")
