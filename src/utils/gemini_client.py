"""
Clean Gemini client for diagram generation without problematic SSL manipulation.
"""

from google import genai
from google.genai import types
from typing import Dict, Any, Optional
import os
import ssl
import httpx

# AGGRESSIVE SSL BYPASS FOR CROWDSTRIKE
print("[*] Applying aggressive SSL bypass for CrowdStrike...")

# Disable SSL verification globally
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''

# Override SSL context
ssl._create_default_https_context = ssl._create_unverified_context

# Monkey patch httpx to disable SSL verification
import httpx._client
import httpx._config

# Store original methods
_original_httpx_client_init = httpx._client.Client.__init__
_original_httpx_async_client_init = httpx._client.AsyncClient.__init__

def patched_httpx_client_init(self, *args, **kwargs):
    """Patched httpx Client.__init__ that forces verify=False"""
    kwargs['verify'] = False
    kwargs['trust_env'] = False
    return _original_httpx_client_init(self, *args, **kwargs)

def patched_httpx_async_client_init(self, *args, **kwargs):
    """Patched httpx AsyncClient.__init__ that forces verify=False"""
    kwargs['verify'] = False
    kwargs['trust_env'] = False
    return _original_httpx_async_client_init(self, *args, **kwargs)

# Apply patches
httpx._client.Client.__init__ = patched_httpx_client_init
httpx._client.AsyncClient.__init__ = patched_httpx_async_client_init

print("[+] Httpx SSL verification globally disabled")

# Import settings
try:
    from .settings import settings
    print("[+] Settings loaded successfully")
except Exception as e:
    print(f"[!] Settings import failed: {e}")
    class FallbackSettings:
        gemini_api_key = os.environ.get('GEMINI_API_KEY', '')
        gemini_model = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-image-preview')
    settings = FallbackSettings()

class GeminiClient:
    """Clean Gemini client implementation."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.gemini_model
        print("[*] Initializing clean Gemini client...")

        # Try direct client initialization
        try:
            self.client = genai.Client(api_key=settings.gemini_api_key)
            print("[+] Basic Gemini client initialized")
        except Exception as e:
            print(f"[-] Basic client failed: {e}")
            raise

    def generate_diagram(self, prompt: str, ea_data: Dict[str, Any]) -> Optional[str]:
        """Generate diagram using Gemini."""
        try:
            formatted_prompt = self._format_ea_prompt(prompt, ea_data)

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=formatted_prompt
            )

            # Check if response contains both text and image data
            result_content = ""
            image_data = None

            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            result_content += part.text + "\n"
                        elif hasattr(part, 'inline_data'):
                            image_data = part.inline_data
                            print(f"[IMG] Found image data: {image_data.mime_type if hasattr(image_data, 'mime_type') else 'unknown type'}")

            # If we have image data, save it
            if image_data:
                result_content += f"\n[IMG] Image data captured: {image_data.mime_type if hasattr(image_data, 'mime_type') else 'unknown'}\n"

                # Save image data if possible
                if hasattr(image_data, 'data'):
                    import base64
                    from datetime import datetime
                    from pathlib import Path

                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

                    # Ensure output directory exists
                    output_dir = Path("ea_diagrams")
                    output_dir.mkdir(exist_ok=True)

                    # Determine file extension from mime type
                    if hasattr(image_data, 'mime_type'):
                        if 'png' in image_data.mime_type.lower():
                            ext = '.png'
                        elif 'jpeg' in image_data.mime_type.lower() or 'jpg' in image_data.mime_type.lower():
                            ext = '.jpg'
                        elif 'gif' in image_data.mime_type.lower():
                            ext = '.gif'
                        elif 'webp' in image_data.mime_type.lower():
                            ext = '.webp'
                        else:
                            ext = '.png'  # default
                    else:
                        ext = '.png'

                    image_filename = output_dir / f"ea-image-{timestamp}{ext}"

                    try:
                        # Handle different data formats
                        if isinstance(image_data.data, str):
                            # Base64 string
                            image_bytes = base64.b64decode(image_data.data)
                        elif isinstance(image_data.data, bytes):
                            # Raw bytes
                            image_bytes = image_data.data
                        else:
                            # Try to convert to string first
                            image_bytes = base64.b64decode(str(image_data.data))

                        with open(image_filename, 'wb') as f:
                            f.write(image_bytes)

                        result_content += f"[SAVE] Image saved to: {image_filename}\n"
                        print(f"[SAVE] Image saved to: {image_filename}")

                        # Show file size
                        file_size = len(image_bytes)
                        print(f"[INFO] Image size: {file_size:,} bytes")

                    except Exception as img_err:
                        print(f"[!] Failed to save image: {img_err}")
                        print(f"[DBG] Image data type: {type(image_data.data)}")
                        print(f"[DBG] Image data length: {len(str(image_data.data)) if hasattr(image_data.data, '__len__') else 'unknown'}")

                        # Try to save debug info
                        try:
                            debug_file = output_dir / f"debug-{timestamp}.txt"
                            with open(debug_file, 'w', encoding='utf-8') as f:
                                f.write(f"Image data type: {type(image_data.data)}\n")
                                f.write(f"Image data: {str(image_data.data)[:200]}...\n")
                                f.write(f"Mime type: {getattr(image_data, 'mime_type', 'unknown')}\n")
                            print(f"[DBG] Debug info saved to: {debug_file}")
                        except:
                            pass

            # Fallback to simple text if no parts found
            if not result_content.strip():
                result_content = response.text

            return result_content

        except Exception as e:
            print(f"Error generating diagram: {e}")
            return None

    def _format_ea_prompt(self, user_prompt: str, ea_data: Dict[str, Any]) -> str:
        """Format EA data into prompt."""
        prompt = f"""Please create a visual diagram image for: {user_prompt}

ENTERPRISE ARCHITECTURE DATA:
"""

        # Add detailed EA data
        for layer, data in ea_data.items():
            if isinstance(data, dict):
                prompt += f"\n{layer.upper()} LAYER:\n"
                for category, items in data.items():
                    if items:
                        if isinstance(items, list):
                            prompt += f"* {category.title()} ({len(items)} items):\n"
                            for i, item in enumerate(items[:3]):  # Show first 3 items
                                if isinstance(item, dict):
                                    name = item.get('name', f'Item {i+1}')
                                    desc = item.get('description', '')
                                    prompt += f"  - {name}: {desc[:80]}...\n" if len(desc) > 80 else f"  - {name}: {desc}\n"
                                else:
                                    prompt += f"  - {str(item)[:80]}...\n" if len(str(item)) > 80 else f"  - {str(item)}\n"
                            if len(items) > 3:
                                prompt += f"  ... and {len(items) - 3} more\n"
                        else:
                            prompt += f"* {category.title()}: {str(items)[:100]}\n"

        prompt += """

REQUIREMENTS:
* Generate an actual visual diagram image (not just text description)
* Use professional diagram conventions (boxes, arrows, labels)
* Include clear relationships between components
* Use appropriate colors and styling for enterprise architecture
* Make it suitable for executive presentation
* Include a legend if needed

Please create the diagram as an image."""

        return prompt

    def list_supported_types(self) -> list:
        """List supported diagram types."""
        return ["overview", "business-process", "application", "data", "infrastructure", "security", "integration"]

    def get_diagram_info(self, diagram_type: str) -> str:
        """Get info about diagram type."""
        info = {
            "overview": "High-level EA overview",
            "business-process": "Business process flows",
            "application": "Application architecture",
            "data": "Data architecture",
            "infrastructure": "Infrastructure deployment",
            "security": "Security controls",
            "integration": "System integrations"
        }
        return info.get(diagram_type, "Unknown type")

# Global client
_client: Optional[GeminiClient] = None

def get_gemini_client() -> GeminiClient:
    """Get clean client instance."""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client