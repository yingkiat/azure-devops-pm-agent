"""
Configuration management for Azure DevOps PM Agent.
Consolidates hard-coded paths and settings into a single configurable location.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import os


class PMAgentConfig:
    """Configuration for the PM Agent system."""
    
    def __init__(self):
        # Base directories
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / "data"
        self.outputs_dir = self.project_root / "outputs"
        self.prompts_dir = self.project_root / "prompts"
        
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)
        
        # Context and storage paths
        self.context_dir = self.data_dir / "ai"
        self.id_mappings_file = self.data_dir / "pm" / "id_mappings.json"
        
        # Wiki configuration
        self.wiki_base_path = "/PM-Agent"
        self.wiki_reports_path = f"{self.wiki_base_path}/AI-Reports"
        self.wiki_interactions_path = f"{self.wiki_base_path}/Interactions"
        
        # AI configuration
        self.max_conversation_history = 100
        self.default_wiql_limit = 200
        self.batch_operation_timeout = 300  # seconds
        
        # File naming patterns
        self.plan_file_pattern = "PLAN-{timestamp}.json"
        self.bi_file_pattern = "BI-{session_id}.json"
    
    def get_plan_file_path(self, plan_id: str) -> Path:
        """Get path for a plan file."""
        return self.outputs_dir / f"{plan_id}.json"
    
    def get_bi_file_path(self, session_id: str) -> Path:
        """Get path for a business intelligence file."""
        return self.outputs_dir / f"BI-{session_id}.json"
    
    def get_context_file_path(self, context_type: str) -> Path:
        """Get path for a context file."""
        return self.context_dir / f"{context_type}.json"
    
    def get_wiki_path(self, path_type: str, *args) -> str:
        """Get wiki path for different types of content."""
        if path_type == "base":
            return self.wiki_base_path
        elif path_type == "reports":
            return self.wiki_reports_path
        elif path_type == "interactions":
            return self.wiki_interactions_path
        elif path_type == "monthly_report":
            year_month = args[0] if args else ""
            return f"{self.wiki_reports_path}/{year_month}"
        elif path_type == "daily_entry":
            year_month, timestamp = args[0], args[1] if len(args) >= 2 else ""
            return f"{self.wiki_reports_path}/{year_month}/{timestamp}"
        else:
            return self.wiki_base_path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "project_root": str(self.project_root),
            "data_dir": str(self.data_dir),
            "outputs_dir": str(self.outputs_dir),
            "context_dir": str(self.context_dir),
            "wiki_base_path": self.wiki_base_path,
            "wiki_reports_path": self.wiki_reports_path,
            "max_conversation_history": self.max_conversation_history,
            "default_wiql_limit": self.default_wiql_limit
        }


# Global configuration instance
_config: Optional[PMAgentConfig] = None

def get_config() -> PMAgentConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = PMAgentConfig()
    return _config

def reload_config():
    """Reload the configuration (useful for testing)."""
    global _config
    _config = PMAgentConfig()