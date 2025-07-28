"""
json_fence.py
Strip ```json ... ``` or ``` ... ``` fences from an LLM response.
"""

def extract(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        # split on first and last ```
        parts = raw.split("```")
        if len(parts) >= 3:
            # parts[1] may begin with "json\n"
            inner = parts[1].lstrip()
            if inner.lower().startswith("json"):
                inner = inner[4:].lstrip()
            return inner
    return raw
