"""Fix duplicate IDs in model.xml by generating unique IDs for duplicates."""
import re
import uuid

def generate_unique_id():
    """Generate a unique ID in the same format as existing IDs."""
    return f"id-{uuid.uuid4().hex[:12]}"

def fix_duplicate_ids(xml_file):
    """Fix all duplicate IDs in the XML file."""
    with open(xml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Track all IDs we've seen
    seen_ids = {}
    id_replacements = {}

    # Find all identifier attributes
    id_pattern = re.compile(r'identifier="(id-[^"]+)"')

    for match in id_pattern.finditer(content):
        old_id = match.group(1)

        if old_id in seen_ids:
            # This is a duplicate - generate a new unique ID
            if old_id not in id_replacements:
                id_replacements[old_id] = []

            new_id = generate_unique_id()
            # Make sure the new ID is truly unique
            while new_id in seen_ids or new_id in [x for replacements in id_replacements.values() for x in replacements]:
                new_id = generate_unique_id()

            id_replacements[old_id].append(new_id)
            seen_ids[new_id] = True
        else:
            seen_ids[old_id] = True

    # Now replace duplicates in the file
    # We need to replace each occurrence after the first one
    for old_id, new_ids in id_replacements.items():
        replacement_index = 0
        position = 0

        while True:
            # Find next occurrence of the old ID
            match = re.search(re.escape(f'identifier="{old_id}"'), content[position:])
            if not match:
                break

            actual_position = position + match.start()

            # Skip the first occurrence (keep it as-is)
            if position == 0 and actual_position == content.find(f'identifier="{old_id}"'):
                position = actual_position + len(f'identifier="{old_id}"')
                continue

            # Replace this duplicate occurrence
            if replacement_index < len(new_ids):
                new_id = new_ids[replacement_index]
                # Replace all references to this ID (in identifier and relationship source/target)

                # Find the element with this ID and replace throughout the file
                # This is tricky - we need to replace the ID and all references to it

                # For now, let's just replace the identifier attribute
                content = content[:actual_position] + f'identifier="{new_id}"' + content[actual_position + len(f'identifier="{old_id}"'):]

                replacement_index += 1

            position = actual_position + len(f'identifier="{new_id}"')

    # Write the fixed content
    with open(xml_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Fixed {sum(len(v) for v in id_replacements.values())} duplicate IDs")
    print(f"Duplicate ID groups: {len(id_replacements)}")
    for old_id, new_ids in id_replacements.items():
        print(f"  {old_id}: replaced {len(new_ids)} duplicates with {new_ids}")

if __name__ == '__main__':
    fix_duplicate_ids('archi_inputs/model.xml')
    print("\nDone! model.xml has been fixed.")
