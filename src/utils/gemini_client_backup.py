"""
Gemini client for diagram generation.
Uses Google's generative AI library for image generation capabilities.
"""

from google import genai
from google.genai import types
from typing import Dict, Any, Optional
import certifi
import requests
import os
import urllib3
import ssl
import httpx

# CROWDSTRIKE SSL WORKAROUND
print(" Applying CrowdStrike SSL workaround...")

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CrowdStrike-specific SSL bypass
import platform
if platform.system() == "Windows":
    print("🪟 Windows detected - applying CrowdStrike SSL fixes...")

    # Disable all SSL verification methods
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['SSL_VERIFY'] = 'false'
    os.environ['PYTHONIOENCODING'] = 'utf-8'

    # Create unverified SSL context
    ssl._create_default_https_context = ssl._create_unverified_context

    # Simple SSL configuration without urllib3 manipulation
    print(" Basic SSL bypass configuration applied")

try:
    from .settings import settings
    print(f" Settings loaded successfully")
except Exception as e:
    print(f" Settings import failed: {e}")
    # Define fallback settings
    class FallbackSettings:
        gemini_api_key = os.environ.get('GEMINI_API_KEY', '')
        gemini_model = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-image-preview')
        gemini_disable_ssl_verify = True
    settings = FallbackSettings()

class GeminiClient:
    """Client for interacting with Gemini models for diagram generation."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.gemini_model

        print(" Initializing Gemini client with CrowdStrike SSL bypass...")

        # CrowdStrike environments often block custom SSL configurations
        # We'll try multiple approaches in order of likelihood to work

        success = False

        # Approach 1: Try to use system's CrowdStrike-managed certificates
        if not success:
            print(" Approach 1: Using system certificates...")
            try:
                # Use default client but with system cert store
                self.client = genai.Client(api_key=settings.gemini_api_key)
                print(" Basic client initialized - testing...")

                # Quick test to see if it works
                test_success = self._test_client_connection()
                if test_success:
                    print(" System certificates working!")
                    success = True
                else:
                    print(" System certificates failed SSL check")

            except Exception as e:
                print(f" System certificates failed: {e}")

        # Approach 2: Custom httpx with unverified SSL
        if not success:
            print(" Approach 2: Custom httpx with unverified SSL...")
            try:
                # Create httpx client that ignores SSL completely
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                custom_httpx_client = httpx.Client(
                    verify=ssl_context,
                    trust_env=False,
                    timeout=httpx.Timeout(30.0)
                )

                http_options = types.HttpOptions(client=custom_httpx_client)

                self.client = genai.Client(
                    api_key=settings.gemini_api_key,
                    http_options=http_options
                )
                print(" Custom httpx client initialized")
                success = True

            except Exception as e:
                print(f" Custom httpx failed: {e}")

        # Approach 3: Environment variable override
        if not success:
            print(" Approach 3: Environment variable override...")
            try:
                # Set environment variables and try again
                os.environ['HTTPX_VERIFY'] = 'false'
                os.environ['SSL_CERT_FILE'] = ''

                self.client = genai.Client(api_key=settings.gemini_api_key)
                print(" Environment override client initialized")
                success = True

            except Exception as e:
                print(f" Environment override failed: {e}")

        if not success:
            print(" All SSL bypass approaches failed")
            print(" CrowdStrike may be blocking all HTTPS modifications")
            print(" Contact your IT team about Google AI API access")
            raise Exception("Cannot initialize Gemini client in CrowdStrike environment")

        print(" Gemini client successfully initialized!")

    def generate_diagram(self, prompt: str, ea_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate a diagram using Gemini's drawing capabilities.

        Args:
            prompt: Description of what diagram to generate
            ea_data: Enterprise Architecture data to visualize

        Returns:
            Base64 encoded image data or None if generation fails
        """
        try:
            # Format the EA data into a readable prompt
            formatted_prompt = self._format_ea_prompt(prompt, ea_data)

            # Generate content with Gemini using new SDK
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=formatted_prompt
            )

            # Return the text response as Gemini Flash 2.5 image preview
            # might return SVG or drawing instructions
            return response.text

        except Exception as e:
            print(f"Error generating diagram with Gemini: {e}")
            return None

    def _format_ea_prompt(self, user_prompt: str, ea_data: Dict[str, Any]) -> str:
        """
        Format EA data into a comprehensive prompt for diagram generation.

        Args:
            user_prompt: User's description of desired diagram
            ea_data: EA discovery data

        Returns:
            Formatted prompt for Gemini
        """
        prompt = f"""Create a visual diagram based on this request: {user_prompt}

Enterprise Architecture Data:
"""

        # Add business layer information
        if "business" in ea_data:
            business = ea_data["business"]
            if "processes" in business and business["processes"]:
                prompt += "\nBUSINESS PROCESSES:\n"
                for process in business["processes"]:
                    if isinstance(process, dict):
                        prompt += f"- {process.get('name', 'Unknown')}: {process.get('description', '')}\n"
                    else:
                        prompt += f"- {process}\n"

            if "capabilities" in business and business["capabilities"]:
                prompt += "\nBUSINESS CAPABILITIES:\n"
                for capability in business["capabilities"]:
                    if isinstance(capability, dict):
                        prompt += f"- {capability.get('name', 'Unknown')}: {capability.get('description', '')}\n"
                    else:
                        prompt += f"- {capability}\n"

        # Add application layer information
        if "application" in ea_data:
            application = ea_data["application"]
            if "applications" in application and application["applications"]:
                prompt += "\nAPPLICATIONS:\n"
                for app in application["applications"]:
                    if isinstance(app, dict):
                        prompt += f"- {app.get('name', 'Unknown')}: {app.get('description', '')}\n"
                    else:
                        prompt += f"- {app}\n"

            if "interfaces" in application and application["interfaces"]:
                prompt += "\nINTEGRATIONS:\n"
                for interface in application["interfaces"]:
                    if isinstance(interface, dict):
                        from_sys = interface.get('from_system', 'Unknown')
                        to_sys = interface.get('to_system', 'Unknown')
                        prompt += f"- {from_sys} → {to_sys}\n"
                    else:
                        prompt += f"- {interface}\n"

        # Add data layer information
        if "data" in ea_data:
            data = ea_data["data"]
            if "entities" in data and data["entities"]:
                prompt += "\nDATA ENTITIES:\n"
                for entity in data["entities"]:
                    if isinstance(entity, dict):
                        prompt += f"- {entity.get('name', 'Unknown')}: {entity.get('description', '')}\n"
                    else:
                        prompt += f"- {entity}\n"

            if "flows" in data and data["flows"]:
                prompt += "\nDATA FLOWS:\n"
                for flow in data["flows"]:
                    if isinstance(flow, dict):
                        from_sys = flow.get('from_system', 'Unknown')
                        to_sys = flow.get('to_system', 'Unknown')
                        prompt += f"- {from_sys} → {to_sys}\n"
                    else:
                        prompt += f"- {flow}\n"

        # Add infrastructure layer information
        if "infrastructure" in ea_data:
            infrastructure = ea_data["infrastructure"]
            if "components" in infrastructure and infrastructure["components"]:
                prompt += "\nINFRASTRUCTURE:\n"
                for component in infrastructure["components"]:
                    if isinstance(component, dict):
                        prompt += f"- {component.get('name', 'Unknown')}: {component.get('description', component.get('purpose', ''))}\n"
                    else:
                        prompt += f"- {component}\n"

        prompt += """

Please create a clear, professional diagram that visualizes this enterprise architecture.
Use standard EA diagram conventions with:
- Clear boxes/shapes for different components
- Arrows showing relationships and data flows
- Appropriate colors and styling
- Labels and legends as needed
- Professional layout and spacing

The diagram should be suitable for executive presentation and technical documentation.
"""

        return prompt

    def _test_client_connection(self) -> bool:
        """Test if the Gemini client can make a simple request."""
        try:
            # Try a minimal request to test connectivity
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Test"
            )
            return True
        except Exception as e:
            print(f" Client connection test failed: {e}")
            return False

    def _test_ssl_connection(self):
        """Test SSL connection to Google APIs with fallback options."""
        if settings.gemini_disable_ssl_verify:
            print("  SSL verification disabled - skipping connection test")
            print(" This is less secure but may be needed in corporate environments")
            return

        try:
            print("Testing SSL connection to Google APIs...")
            response = requests.get(
                "https://generativelanguage.googleapis.com",
                verify=certifi.where(),
                timeout=10
            )
            print(f" SSL connection successful (status: {response.status_code})")
        except requests.exceptions.SSLError as e:
            print(f" SSL connection failed: {e}")
            print("\n SSL Connection Troubleshooting:")
            print("1. Try updating certificates: pip install --upgrade certifi")
            print("2. For corporate environments, add to your .env:")
            print("   GEMINI_DISABLE_SSL_VERIFY=true")
            print("3. Contact your IT team about SSL certificate issues")

            # Try without SSL verification as a test
            try:
                print("\n Testing connection without SSL verification...")
                response = requests.get(
                    "https://generativelanguage.googleapis.com",
                    verify=False,
                    timeout=10
                )
                print(f" Connection works without SSL verification (status: {response.status_code})")
                print(" Consider setting GEMINI_DISABLE_SSL_VERIFY=true in your .env")
            except Exception as test_e:
                print(f" Connection fails even without SSL verification: {test_e}")

            raise
        except requests.exceptions.RequestException as e:
            print(f" Network connection issue: {e}")
            # Don't raise - might still work with genai client
        except Exception as e:
            print(f" Unexpected connection test error: {e}")
            # Don't raise - might still work with genai client

# Global client instance
_client: Optional[GeminiClient] = None

def get_gemini_client() -> GeminiClient:
    """Get the global Gemini client instance."""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client