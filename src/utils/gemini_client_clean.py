"""
Clean Gemini client for diagram generation without problematic SSL manipulation.
"""

from google import genai
from google.genai import types
from typing import Dict, Any, Optional
import os
import ssl
import httpx

# SIMPLE SSL BYPASS
print(" Applying simple SSL bypass...")

# Disable SSL verification globally
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''

# Override SSL context
ssl._create_default_https_context = ssl._create_unverified_context

# Import settings
try:
    from .settings import settings
    print(" Settings loaded successfully")
except Exception as e:
    print(f" Settings import failed: {e}")
    class FallbackSettings:
        gemini_api_key = os.environ.get('GEMINI_API_KEY', '')
        gemini_model = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-image-preview')
    settings = FallbackSettings()

class GeminiClient:
    """Clean Gemini client implementation."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.gemini_model
        print(" Initializing clean Gemini client...")

        # Try direct client initialization
        try:
            self.client = genai.Client(api_key=settings.gemini_api_key)
            print(" Basic Gemini client initialized")
        except Exception as e:
            print(f" Basic client failed: {e}")
            raise

    def generate_diagram(self, prompt: str, ea_data: Dict[str, Any]) -> Optional[str]:
        """Generate diagram using Gemini."""
        try:
            formatted_prompt = self._format_ea_prompt(prompt, ea_data)

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=formatted_prompt
            )

            return response.text
        except Exception as e:
            print(f"Error generating diagram: {e}")
            return None

    def _format_ea_prompt(self, user_prompt: str, ea_data: Dict[str, Any]) -> str:
        """Format EA data into prompt."""
        prompt = f"Create a visual diagram: {user_prompt}\n\nEA Data:\n"

        # Add basic EA data
        for layer, data in ea_data.items():
            if isinstance(data, dict):
                prompt += f"\n{layer.upper()}:\n"
                for category, items in data.items():
                    if items:
                        prompt += f"- {category}: {len(items) if isinstance(items, list) else str(items)[:100]}\n"

        prompt += "\nCreate a clear, professional diagram suitable for executive presentation."
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