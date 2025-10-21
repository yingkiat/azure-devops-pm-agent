"""
EA Discovery Engine - Enhanced with Matrix Output

Uses ea_discovery prompt to extract EA objects from system descriptions
and maintains a live App-Capability matrix with CRUD operations.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List

from utils.openai_client import client
from shared.storage import get_storage


class EADiscovery:
    """Discovers and extracts EA objects from system descriptions and maintains EA matrix."""

    def __init__(self, storage_type: str = None):
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts" / "ea"
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "ea"

        # Initialize storage for EA matrix
        self.storage = get_storage(
            storage_type=storage_type,
            table_name="ea_matrix",
            schema_file=str(self.data_dir / "entities_schema.yaml")
        )

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def discover_from_file(self, input_file: str, output_file: str = None) -> Dict[str, Any]:
        """
        Discover EA objects from a system description file.

        Args:
            input_file: Path to text file containing system description
            output_file: Optional output file for results

        Returns:
            EA discovery results
        """
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        system_description = input_path.read_text(encoding='utf-8')

        print(f"Reading system description from: {input_file}")
        print(f"Description length: {len(system_description)} characters")

        results = self.discover(system_description)

        if output_file:
            self.save_discovery(results, output_file)

        return results

    def discover_and_update_matrix(self, text_input: str) -> Dict[str, Any]:
        """
        Enhanced discovery that updates the EA matrix and provides exploration insights.

        Args:
            text_input: Natural language description of EA changes

        Returns:
            Dict containing discovery results, matrix changes, and data exploration
        """
        # Load current matrix and schema for AI context
        current_data = self.storage.load_data()
        schema = self._load_schema()
        data_context = self.storage.get_data_context()

        try:
            # Call AI with enhanced prompt for matrix operations
            ai_response = self._call_ai_with_matrix_context(
                text_input=text_input,
                current_schema=schema,
                existing_data_sample=current_data.head(10).to_string() if not current_data.empty else "No existing data",
                full_data_context=data_context
            )

            # Check for error in AI response
            if 'error' in ai_response:
                return ai_response

            # Apply matrix changes
            if 'changes' in ai_response:
                changes = ai_response['changes']

                # Apply inserts and updates
                if 'inserts' in changes and changes['inserts']:
                    self.storage.upsert_rows(changes['inserts'])

                if 'updates' in changes and changes['updates']:
                    self.storage.upsert_rows(changes['updates'])

                # Apply deletes
                if 'deletes' in changes and changes['deletes']:
                    for delete_condition in changes['deletes']:
                        self.storage.delete_rows(delete_condition)

            return ai_response

        except Exception as e:
            return {"error": str(e)}

    def discover(self, system_description: str, existing_model: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Discover EA objects from a system description.

        Args:
            system_description: Text description of the system
            existing_model: Optional existing ArchiMate model context for entity resolution

        Returns:
            Dict containing discovered EA objects across all layers
        """
        prompt_file = self.prompts_dir / "ea_discovery.md"

        if not prompt_file.exists():
            raise FileNotFoundError(f"EA discovery prompt not found: {prompt_file}")

        prompt_template = prompt_file.read_text(encoding='utf-8')

        # Prepare existing model context
        if existing_model is None:
            existing_model = {"elements": [], "element_names": [], "relationships": []}

        element_names_str = ", ".join(existing_model.get("element_names", [])) if existing_model.get("element_names") else "None"
        relationships_str = json.dumps(existing_model.get("relationships", []), indent=2) if existing_model.get("relationships") else "None"

        # Replace ALL template variables (both old and new format)
        prompt = prompt_template.replace("{{SYSTEM_DESCRIPTION}}", system_description)
        prompt = prompt.replace("{{EXISTING_ELEMENT_NAMES}}", element_names_str)
        prompt = prompt.replace("{{EXISTING_RELATIONSHIPS}}", relationships_str)

        # Replace old matrix-aware template variables (for backward compatibility)
        prompt = prompt.replace("{text_input}", system_description)
        prompt = prompt.replace("{current_schema}", "")
        prompt = prompt.replace("{existing_data_sample}", "No existing data")
        prompt = prompt.replace("{full_data_context}", "No data context")

        print("Discovering EA objects across all layers...")

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an enterprise architect. Discover and extract EA objects from the system description across all layers and return structured JSON. CRITICAL: Always return valid JSON in the specified format. Never ask for more input. Work with the information provided, even if minimal."
                },
                {"role": "user", "content": prompt}
            ]

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.2,
                max_tokens=8000  # Increased to handle large discoveries with many elements
            )
            content = response.choices[0].message.content.strip()

            # Extract JSON from response (handle code blocks)
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                # Handle code blocks without json marker
                start = content.find("```") + 3
                end = content.find("```", start)
                if end > start:
                    content = content[start:end].strip()

            # Clean up common JSON formatting issues
            content = self._cleanup_json(content)

            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Raw response (first 1000 chars): {content[:1000]}")
                return {"error": "Failed to parse JSON response", "raw_content": content[:2000]}

        except Exception as e:
            print(f"Error during EA discovery: {e}")
            return {"error": str(e)}

    def save_discovery(self, discovery: Dict[str, Any], output_file: str) -> None:
        """Save discovery results to a JSON file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(discovery, f, indent=2, ensure_ascii=False)

        print(f"Discovery saved to: {output_path}")

    def format_summary(self, discovery: Dict[str, Any]) -> str:
        """Format discovery results for display."""
        if "error" in discovery:
            return f"Discovery Error: {discovery['error']}"

        summary = "EA DISCOVERY RESULTS\n"
        summary += "=" * 50 + "\n\n"

        layer_icons = {
            "business": "[BUS]",
            "application": "[APP]",
            "data": "[DATA]",
            "infrastructure": "[INFRA]",
            "security": "[SEC]"
        }

        for layer_name, layer_data in discovery.items():
            if not isinstance(layer_data, dict):
                continue

            icon = layer_icons.get(layer_name, "[LAYER]")
            summary += f"{icon} {layer_name.upper()} LAYER\n"
            summary += "-" * 30 + "\n"

            for category, items in layer_data.items():
                if not items:
                    continue

                summary += f"\n* {category.title()}:\n"

                # Handle both string values and list values
                if isinstance(items, str):
                    summary += f"  1. {items}\n"
                elif isinstance(items, list):
                    for i, item in enumerate(items, 1):
                        if isinstance(item, dict):
                            name = item.get('name', f'Item {i}')
                            summary += f"  {i}. {name}\n"
                            if 'description' in item:
                                summary += f"     {item['description']}\n"
                        else:
                            summary += f"  {i}. {item}\n"
                else:
                    summary += f"  1. {str(items)}\n"

            summary += "\n"

        return summary

    def _load_schema(self) -> Dict[str, Any]:
        """Load EA schema configuration."""
        schema_file = self.data_dir / "entities_schema.yaml"
        if schema_file.exists():
            with open(schema_file, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def _call_ai_with_matrix_context(
        self,
        text_input: str,
        current_schema: Dict[str, Any],
        existing_data_sample: str,
        full_data_context: str
    ) -> Dict[str, Any]:
        """
        Call AI with enhanced prompt for matrix-aware discovery.
        """
        prompt_file = self.prompts_dir / "ea_discovery.md"

        if not prompt_file.exists():
            raise FileNotFoundError(f"EA discovery prompt not found: {prompt_file}")

        prompt_template = prompt_file.read_text(encoding='utf-8')

        # Replace template variables safely
        prompt = prompt_template.replace("{text_input}", text_input)
        prompt = prompt.replace("{current_schema}", yaml.dump(current_schema, default_flow_style=False) if current_schema else "No schema defined")
        prompt = prompt.replace("{existing_data_sample}", existing_data_sample)
        prompt = prompt.replace("{full_data_context}", full_data_context)

        print("Discovering EA objects with matrix update...")

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an Enterprise Architecture analyst. Discover EA objects, update the matrix, and provide exploration insights. CRITICAL: You MUST return valid JSON in the exact format specified. If the existing data is empty, treat it as a fresh start and extract EA objects from the text input. Never ask for more details - always return JSON."
                },
                {"role": "user", "content": prompt}
            ]

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.2,
                max_tokens=8000  # Increased to handle large discoveries with many elements
            )
            content = response.choices[0].message.content.strip()

            # Extract JSON from response
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()

            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Raw response: {content[:500]}...")
                return {"error": "Failed to parse JSON response", "raw_content": content}

        except Exception as e:
            print(f"Error during EA discovery: {e}")
            return {"error": str(e)}

    def format_matrix_results(self, results: Dict[str, Any]) -> str:
        """Format matrix discovery results for display."""
        if "error" in results:
            return f"Discovery Error: {results['error']}"

        output = "=== EA DISCOVERY RESULTS ===\n\n"

        # Changes Applied
        if 'changes' in results:
            changes = results['changes']
            output += " CHANGES APPLIED:\n"

            if 'inserts' in changes and changes['inserts']:
                for insert in changes['inserts']:
                    app = insert.get('app_name', 'Unknown App')
                    cap = insert.get('capability', 'Unknown Capability')
                    maturity = insert.get('maturity', 'N/A')
                    output += f" Added: {app} -> {cap} (maturity: {maturity})\n"

            if 'updates' in changes and changes['updates']:
                for update in changes['updates']:
                    app = update.get('app_name', 'Unknown App')
                    cap = update.get('capability', 'Unknown Capability')
                    output += f"  Updated: {app} -> {cap}\n"

            if 'deletes' in changes and changes['deletes']:
                for delete in changes['deletes']:
                    output += f" Deleted: rows matching {delete}\n"

            output += "\n"

        # Data Exploration
        if 'exploration' in results:
            exploration = results['exploration']
            output += " DATA EXPLORATION:\n"

            for key, value in exploration.items():
                if value:
                    icon = {"gap_analysis": "", "sunset_risks": "", "maturity_trends": "", "overlaps": ""}.get(key, "")
                    output += f"{icon} {key.replace('_', ' ').title()}:\n   {value}\n\n"

        # Recommendations
        if 'recommendations' in results and results['recommendations']:
            output += " RECOMMENDATIONS:\n"
            for i, rec in enumerate(results['recommendations'], 1):
                output += f"   {i}. {rec}\n"

        return output

    def get_matrix_summary(self) -> str:
        """Get a summary of the current EA matrix."""
        df = self.storage.load_data()

        if df.empty:
            return "EA Matrix is empty. Use 'ea-discover' to add applications and capabilities."

        summary = f"EA MATRIX SUMMARY\n"
        summary += "=" * 30 + "\n"
        summary += f"Total Records: {len(df)}\n"

        if 'app_name' in df.columns:
            summary += f"Applications: {df['app_name'].nunique()}\n"

        if 'capability' in df.columns:
            summary += f"Capabilities: {df['capability'].nunique()}\n"

        if 'domain' in df.columns:
            summary += f"Domains: {df['domain'].nunique()}\n"

        if 'lifecycle_status' in df.columns:
            lifecycle_counts = df['lifecycle_status'].value_counts()
            summary += "\nLifecycle Status:\n"
            for status, count in lifecycle_counts.items():
                summary += f"  {status}: {count}\n"

        if 'maturity' in df.columns:
            avg_maturity = df['maturity'].mean()
            summary += f"\nAverage Maturity: {avg_maturity:.1f}/5\n"

        return summary

    def _cleanup_json(self, content: str) -> str:
        """
        Clean up common JSON formatting issues from LLM responses.
        This is a last resort before JSON parsing.
        """
        import re

        # Remove any trailing commas before closing braces/brackets
        content = re.sub(r',(\s*[}\]])', r'\1', content)

        # Remove // style comments (not valid in JSON)
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)

        # Remove /* */ style comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Fix common truncation pattern: incomplete array/object at end
        # Count opening/closing braces and brackets
        open_braces = content.count('{')
        close_braces = content.count('}')
        open_brackets = content.count('[')
        close_brackets = content.count(']')

        # If truncated, try to close gracefully
        if open_braces > close_braces:
            content += '}' * (open_braces - close_braces)
        if open_brackets > close_brackets:
            content += ']' * (open_brackets - close_brackets)

        return content.strip()