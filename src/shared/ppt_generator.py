"""
PPT Generator - Creates PowerPoint presentations from YAML slide plans.

Uses corporate templates when provided, with layout mapping for consistent styling.
"""

import yaml
from pathlib import Path
from typing import Optional
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR


# Default layout mapping (can be overridden in YAML)
# Values can be integers (index) or strings (layout name)
DEFAULT_LAYOUT_MAPPING = {
    "title": 0,
    "section": 1,
    "bullets": 2,
    "image": 3,
    "two_column": 4,
    "table": 5,
    "blank": 6,
}


def _find_layout(prs: Presentation, layout_ref) -> 'SlideLayout':
    """
    Find a slide layout by index or name.

    Args:
        prs: Presentation object
        layout_ref: Integer index or string layout name

    Returns:
        SlideLayout object
    """
    if isinstance(layout_ref, int):
        idx = min(layout_ref, len(prs.slide_layouts) - 1)
        return prs.slide_layouts[idx]

    # Search by name across all layouts
    layout_name = str(layout_ref)
    for layout in prs.slide_layouts:
        if layout.name == layout_name:
            return layout

    # Partial match fallback
    for layout in prs.slide_layouts:
        if layout_name.lower() in layout.name.lower():
            return layout

    # Default to first layout
    return prs.slide_layouts[0]


def inspect_template(template_path: str) -> dict:
    """
    Inspect a PowerPoint template and return available layouts and sample slides.

    Use this to understand what layouts are available in your corporate template,
    then configure the layout_mapping in your YAML accordingly.
    """
    prs = Presentation(template_path)
    layouts = []

    for idx, layout in enumerate(prs.slide_layouts):
        placeholders = []
        for shape in layout.placeholders:
            placeholders.append({
                "idx": shape.placeholder_format.idx,
                "type": str(shape.placeholder_format.type),
                "name": shape.name
            })
        layouts.append({
            "index": idx,
            "name": layout.name,
            "placeholders": placeholders
        })

    # Also inspect actual slides in the template
    sample_slides = []
    for idx, slide in enumerate(prs.slides):
        slide_info = {
            "index": idx,
            "layout_name": slide.slide_layout.name if slide.slide_layout else "Unknown",
            "shapes": []
        }
        for shape in slide.shapes:
            shape_info = {"name": shape.name, "type": shape.shape_type.name if hasattr(shape.shape_type, 'name') else str(shape.shape_type)}
            if hasattr(shape, 'text') and shape.text:
                shape_info["text_preview"] = shape.text[:50] + "..." if len(shape.text) > 50 else shape.text
            # Check if shape is a placeholder using try/except (hasattr alone is unreliable)
            try:
                pf = shape.placeholder_format
                if pf:
                    shape_info["placeholder_idx"] = pf.idx
                    shape_info["placeholder_type"] = str(pf.type)
            except ValueError:
                pass  # Shape is not a placeholder
            slide_info["shapes"].append(shape_info)
        sample_slides.append(slide_info)

    return {
        "template": template_path,
        "layout_count": len(layouts),
        "layouts": layouts,
        "sample_slide_count": len(sample_slides),
        "sample_slides": sample_slides
    }


def generate_ppt(yaml_path: str, output_path: Optional[str] = None) -> str:
    """
    Generate a PowerPoint presentation from a YAML slide plan.

    Args:
        yaml_path: Path to the YAML slide plan
        output_path: Optional output path (overrides YAML setting)

    Returns:
        Path to the generated .pptx file
    """
    yaml_path = Path(yaml_path)

    with open(yaml_path, 'r', encoding='utf-8') as f:
        plan = yaml.safe_load(f)

    presentation_config = plan.get('presentation', {})
    slides_config = plan.get('slides', [])

    # Determine template
    template_path = presentation_config.get('template')
    if template_path and Path(template_path).exists():
        prs = Presentation(template_path)
    else:
        prs = Presentation()

    # Get layout mapping (from YAML or defaults)
    layout_mapping = {**DEFAULT_LAYOUT_MAPPING, **presentation_config.get('layout_mapping', {})}

    # Process each slide
    for slide_config in slides_config:
        layout_name = slide_config.get('layout', 'bullets')
        layout_ref = layout_mapping.get(layout_name, 2)

        # Find layout by index or name
        slide_layout = _find_layout(prs, layout_ref)
        slide = prs.slides.add_slide(slide_layout)

        # Apply content based on layout type
        if layout_name == 'title':
            _apply_title_slide(slide, slide_config)
        elif layout_name == 'section':
            _apply_section_slide(slide, slide_config)
        elif layout_name == 'bullets':
            _apply_bullets_slide(slide, slide_config)
        elif layout_name == 'image':
            _apply_image_slide(slide, slide_config)
        elif layout_name == 'table':
            _apply_table_slide(slide, slide_config)
        elif layout_name == 'two_column':
            _apply_two_column_slide(slide, slide_config)
        else:
            _apply_bullets_slide(slide, slide_config)

        # Add speaker notes if provided
        if 'notes' in slide_config:
            slide.notes_slide.notes_text_frame.text = slide_config['notes']

    # Determine output path
    if output_path:
        out_path = Path(output_path)
    elif 'output' in presentation_config:
        out_path = Path(presentation_config['output'])
    else:
        out_path = yaml_path.with_suffix('.pptx')

    # Ensure output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    prs.save(str(out_path))
    return str(out_path)


def _apply_title_slide(slide, config: dict):
    """Apply content to a title slide layout."""
    title = config.get('title', '')
    subtitle = config.get('subtitle', '')

    if slide.shapes.title:
        slide.shapes.title.text = title

    # Find subtitle placeholder (try common indices: 1 standard, 10 corporate templates)
    subtitle_indices = [1, 10, 2]
    for shape in slide.placeholders:
        if shape.placeholder_format.idx in subtitle_indices:
            shape.text = subtitle
            break


def _apply_section_slide(slide, config: dict):
    """Apply content to a section divider slide."""
    title = config.get('title', '')
    subtitle = config.get('subtitle', '')

    if slide.shapes.title:
        slide.shapes.title.text = title

    for shape in slide.placeholders:
        if shape.placeholder_format.idx == 1:
            shape.text = subtitle
            break


def _apply_bullets_slide(slide, config: dict):
    """Apply content to a bullet point slide."""
    title = config.get('title', '')
    bullets = config.get('bullets', [])

    if slide.shapes.title:
        slide.shapes.title.text = title

    # Find content placeholder
    for shape in slide.placeholders:
        if shape.placeholder_format.idx == 1:  # Content placeholder
            tf = shape.text_frame
            tf.clear()

            for i, bullet in enumerate(bullets):
                if i == 0:
                    p = tf.paragraphs[0]
                else:
                    p = tf.add_paragraph()

                # Handle nested bullets
                if isinstance(bullet, dict):
                    p.text = bullet.get('text', '')
                    p.level = bullet.get('level', 0)
                else:
                    p.text = str(bullet)
                    p.level = 0
            break


def _apply_image_slide(slide, config: dict):
    """Apply content to an image slide."""
    title = config.get('title', '')
    image_path = config.get('image', '')

    if slide.shapes.title:
        slide.shapes.title.text = title

    # Add image if path exists
    if image_path and Path(image_path).exists():
        # Find picture placeholder or add image directly
        picture_placeholder = None
        for shape in slide.placeholders:
            if shape.placeholder_format.type == 18:  # Picture placeholder
                picture_placeholder = shape
                break

        if picture_placeholder:
            picture_placeholder.insert_picture(image_path)
        else:
            # Add image to center of slide
            left = Inches(1)
            top = Inches(1.5)
            width = Inches(8)
            slide.shapes.add_picture(image_path, left, top, width=width)


def _apply_table_slide(slide, config: dict):
    """Apply content to a table slide."""
    title = config.get('title', '')
    table_config = config.get('table', {})
    headers = table_config.get('headers', [])
    rows = table_config.get('rows', [])

    if slide.shapes.title:
        slide.shapes.title.text = title

    if not headers and not rows:
        return

    # Calculate table dimensions
    col_count = len(headers) if headers else (len(rows[0]) if rows else 0)
    row_count = len(rows) + (1 if headers else 0)

    if col_count == 0 or row_count == 0:
        return

    # Add table
    left = Inches(0.5)
    top = Inches(1.5)
    width = Inches(9)
    height = Inches(0.5 * row_count)

    table = slide.shapes.add_table(row_count, col_count, left, top, width, height).table

    # Set column widths
    col_width = int(width / col_count)
    for col in table.columns:
        col.width = col_width

    # Add headers
    if headers:
        for col_idx, header in enumerate(headers):
            cell = table.cell(0, col_idx)
            cell.text = str(header)
            # Bold headers
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True

    # Add data rows
    start_row = 1 if headers else 0
    for row_idx, row_data in enumerate(rows):
        for col_idx, cell_value in enumerate(row_data):
            cell = table.cell(start_row + row_idx, col_idx)
            cell.text = str(cell_value)


def _apply_two_column_slide(slide, config: dict):
    """Apply content to a two-column slide."""
    title = config.get('title', '')
    left_content = config.get('left', [])
    right_content = config.get('right', [])

    if slide.shapes.title:
        slide.shapes.title.text = title

    # Find content placeholders (typically idx 1 and 2 for two-column)
    placeholders = sorted(
        [s for s in slide.placeholders if s.placeholder_format.idx > 0],
        key=lambda s: s.placeholder_format.idx
    )

    if len(placeholders) >= 1 and left_content:
        _fill_text_placeholder(placeholders[0], left_content)

    if len(placeholders) >= 2 and right_content:
        _fill_text_placeholder(placeholders[1], right_content)


def _fill_text_placeholder(shape, content: list):
    """Fill a placeholder with bullet content."""
    tf = shape.text_frame
    tf.clear()

    for i, item in enumerate(content):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        if isinstance(item, dict):
            p.text = item.get('text', '')
            p.level = item.get('level', 0)
        else:
            p.text = str(item)
            p.level = 0


def generate_from_plan(plan: dict, output_path: str, template_path: Optional[str] = None) -> str:
    """
    Generate PPT directly from a plan dictionary (no YAML file needed).

    Useful for programmatic generation without intermediate files.
    """
    # Create temp YAML and process
    import tempfile
    import os

    if template_path:
        plan.setdefault('presentation', {})['template'] = template_path

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        yaml.dump(plan, f, default_flow_style=False, allow_unicode=True)
        temp_path = f.name

    try:
        result = generate_ppt(temp_path, output_path)
    finally:
        os.unlink(temp_path)

    return result
