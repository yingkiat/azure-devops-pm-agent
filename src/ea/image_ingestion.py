"""
Image Ingestion for EA Discovery

Processes images (slides, diagrams, whiteboards) using vision LLM to extract
EA-relevant information into text files for subsequent discovery.

Features:
- Batch processing of image directories
- Checksum-based caching (skip already-processed images)
- Outputs text files to ea_inputs/ for ea_discover_directory
"""

import base64
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Image extensions to process
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif'}


@dataclass
class ImageInfo:
    """Information about a tracked image"""
    file_path: str
    checksum: str
    size: int
    last_modified: float
    last_processed: Optional[str] = None
    output_file: Optional[str] = None
    elements_extracted: int = 0
    error: Optional[str] = None


class ImageIngestionTracker:
    """Tracks processed images to avoid re-ingestion"""

    def __init__(self, cache_dir: str = ".file_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "image_ingestion_cache.json"
        self.tracked_images: Dict[str, ImageInfo] = {}
        self._load_cache()

    def _load_cache(self):
        """Load tracking data from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.tracked_images = {
                    path: ImageInfo(**info)
                    for path, info in data.get("images", {}).items()
                }
            except Exception:
                self.tracked_images = {}

    def _save_cache(self):
        """Save tracking data to disk"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "images": {path: asdict(info) for path, info in self.tracked_images.items()},
            "last_updated": datetime.now().isoformat()
        }
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def get_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def needs_processing(self, file_path: Path, output_dir: Path) -> Tuple[bool, str]:
        """
        Check if image needs processing.

        Returns:
            (needs_processing, reason)
        """
        str_path = str(file_path)

        # New image
        if str_path not in self.tracked_images:
            return True, "new image"

        info = self.tracked_images[str_path]

        # Check if checksum changed
        current_checksum = self.get_checksum(file_path)
        if current_checksum != info.checksum:
            return True, "image modified"

        # Check if output file exists
        if info.output_file:
            output_path = output_dir / info.output_file
            if not output_path.exists():
                return True, "output file missing"

        # Check if previous processing had error
        if info.error:
            return True, f"previous error: {info.error}"

        return False, "already processed"

    def mark_processed(self, file_path: Path, output_file: str,
                       elements_extracted: int = 0, error: str = None):
        """Mark image as processed"""
        str_path = str(file_path)
        stat = file_path.stat()

        self.tracked_images[str_path] = ImageInfo(
            file_path=str_path,
            checksum=self.get_checksum(file_path),
            size=stat.st_size,
            last_modified=stat.st_mtime,
            last_processed=datetime.now().isoformat(),
            output_file=output_file,
            elements_extracted=elements_extracted,
            error=error
        )
        self._save_cache()

    def get_stats(self) -> Dict:
        """Get processing statistics"""
        total = len(self.tracked_images)
        successful = sum(1 for i in self.tracked_images.values() if i.output_file and not i.error)
        failed = sum(1 for i in self.tracked_images.values() if i.error)

        return {
            "total_tracked": total,
            "successful": successful,
            "failed": failed,
            "total_elements_extracted": sum(i.elements_extracted for i in self.tracked_images.values())
        }

    def clear_cache(self):
        """Clear all tracking data"""
        self.tracked_images = {}
        if self.cache_file.exists():
            self.cache_file.unlink()


def encode_image_base64(image_path: Path) -> str:
    """Encode image file to base64 string"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_image_mime_type(image_path: Path) -> str:
    """Get MIME type for image"""
    ext = image_path.suffix.lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff'
    }
    return mime_types.get(ext, 'image/png')


def extract_ea_from_image(image_path: Path) -> Tuple[str, int]:
    """
    Use Azure OpenAI GPT-4o vision to extract EA information from image.

    Args:
        image_path: Path to image file

    Returns:
        (extracted_text, element_count)
    """
    from src.utils.openai_client import client
    from src.utils.settings import settings

    # Encode image
    base64_image = encode_image_base64(image_path)
    mime_type = get_image_mime_type(image_path)

    # Build prompt for EA extraction
    extraction_prompt = """Analyze this architecture diagram, slide, or system documentation image.

Extract ALL enterprise architecture information you can identify:

1. **Applications/Systems**: List every application, system, platform, or tool shown
   - Include the full name as displayed
   - Note any abbreviations or short names

2. **Relationships/Integrations**: Describe how systems connect
   - Data flows (what data moves between systems)
   - Integration patterns (API, batch, real-time, etc.)
   - Direction of flow if shown

3. **Business Capabilities**: What business functions are supported
   - Order management, inventory, CRM, etc.

4. **Technical Details**: Any technical information shown
   - Protocols, databases, middleware
   - Cloud services, hosting information

5. **Organizational Context**:
   - Departments, regions, business units mentioned
   - Ownership or responsibility information

Format your response as natural language descriptions that describe the systems and their relationships.
Use phrases like:
- "[System A] integrates with [System B] for [purpose]"
- "[System] handles [business capability]"
- "[System] sends [data type] to [System]"

Be thorough - extract every piece of information visible in the image."""

    # Call Azure OpenAI with vision
    response = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": extraction_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ],
        max_tokens=4096,
        temperature=0.3
    )

    extracted_text = response.choices[0].message.content

    # Rough element count based on common patterns
    element_count = (
        extracted_text.lower().count(' integrates with ') +
        extracted_text.lower().count(' connects to ') +
        extracted_text.lower().count(' sends ') +
        extracted_text.lower().count(' handles ') +
        len([line for line in extracted_text.split('\n') if line.strip().startswith('-')])
    )

    return extracted_text, max(element_count, 1)


def ingest_images_from_directory(
    input_dir: str = "ea_inputs/images",
    output_dir: str = "ea_inputs",
    file_pattern: str = "*"
) -> Dict:
    """
    Batch ingest images from directory, extracting EA information.

    Directory structure is preserved:
        ea_inputs/images/02_IT_systems/diagram.png → ea_inputs/02_IT_systems/diagram.txt

    Args:
        input_dir: Directory containing images (scans subdirectories)
        output_dir: Base directory for extracted text files (default: "ea_inputs")
                   Subdirectory structure from input_dir is preserved
        file_pattern: Glob pattern for filtering (default: all images)

    Returns:
        Processing summary with statistics
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    tracker = ImageIngestionTracker()

    # Find all images
    all_images = []
    for ext in IMAGE_EXTENSIONS:
        if file_pattern == "*":
            all_images.extend(input_path.rglob(f"*{ext}"))
            all_images.extend(input_path.rglob(f"*{ext.upper()}"))
        else:
            all_images.extend(input_path.rglob(file_pattern))

    # Deduplicate
    all_images = list(set(all_images))

    results = {
        "total_images_found": len(all_images),
        "processed": [],
        "skipped": [],
        "failed": [],
        "output_dir": str(output_path)
    }

    for image_path in sorted(all_images):
        needs_proc, reason = tracker.needs_processing(image_path, output_path)

        if not needs_proc:
            results["skipped"].append({
                "file": str(image_path),
                "reason": reason
            })
            continue

        print(f"[IMG] Processing: {image_path.name} ({reason})")

        try:
            # Extract EA information
            extracted_text, element_count = extract_ea_from_image(image_path)

            # Generate output path preserving directory structure
            # ea_inputs/images/subfolder/image.png → ea_inputs/subfolder/image.txt
            try:
                rel_path = image_path.relative_to(input_path)
                # Change extension to .txt and preserve directory structure
                output_rel_path = rel_path.with_suffix('.txt')
                output_file = output_path / output_rel_path
                # Ensure parent directory exists
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_name = str(output_rel_path)
            except ValueError:
                output_name = image_path.stem + ".txt"
                output_file = output_path / output_name

            # Write extracted content
            header = f"""# Extracted from: {image_path.name}
# Source: {image_path}
# Extracted: {datetime.now().isoformat()}
# ---

"""
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(header + extracted_text)

            # Mark as processed
            tracker.mark_processed(image_path, output_name, element_count)

            results["processed"].append({
                "file": str(image_path),
                "output": str(output_file),
                "elements_extracted": element_count
            })

            print(f"  -> {output_name} ({element_count} elements)")

        except Exception as e:
            error_msg = str(e)
            tracker.mark_processed(image_path, None, 0, error_msg)

            results["failed"].append({
                "file": str(image_path),
                "error": error_msg
            })

            print(f"  [ERROR] {error_msg}")

    # Summary
    results["summary"] = {
        "processed_count": len(results["processed"]),
        "skipped_count": len(results["skipped"]),
        "failed_count": len(results["failed"]),
        "total_elements_extracted": sum(p["elements_extracted"] for p in results["processed"]),
        "cache_stats": tracker.get_stats()
    }

    return results


def clear_image_cache() -> Dict:
    """Clear the image ingestion cache"""
    tracker = ImageIngestionTracker()
    stats_before = tracker.get_stats()
    tracker.clear_cache()

    return {
        "cleared": True,
        "previous_stats": stats_before
    }
