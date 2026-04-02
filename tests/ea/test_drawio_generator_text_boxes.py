"""Tests for draw.io text box expansion helpers."""

from src.ea.drawio_generator import DrawIOGenerator


def test_expand_text_boxes_supports_stacked_lines():
    """Stacked line notes should expand into one header and one box per line."""
    expanded = DrawIOGenerator._expand_text_boxes([
        {
            "kind": "stacked_lines",
            "x": 540,
            "y": 555,
            "header_width": 150,
            "header_height": 28,
            "header_text": "Principles",
            "line_x": 560,
            "line_y": 592,
            "line_width": 455,
            "line_height": 24,
            "line_gap": 6,
            "lines": [
                "Extract from source unless there are explicit performance exceptions.",
                "Follow global direction for technical standards.",
                "AI strategy remains pending global direction.",
            ],
        }
    ])

    assert len(expanded) == 4
    assert expanded[0]["text"] == "Principles"
    assert expanded[0]["style_kind"] == "note_header"
    assert [box["y"] for box in expanded[1:]] == [592, 622, 652]
    assert all(box["width"] == 455 for box in expanded[1:])
    assert [box["style_kind"] for box in expanded[1:]] == ["note_line", "note_line", "note_line"]
