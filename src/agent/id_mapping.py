"""
ID Mapping System - Creates bidirectional mapping between Azure DevOps auto-generated IDs 
and local logical identifiers for PM-Agent internal reference and operations.

IMPORTANT USAGE:
- Display to users: Always show Azure DevOps IDs (PR-1234, WI-5678) - what they see in DevOps UI
- Internal reference: Use local IDs (pr-auth-feature-001) for PM-Agent operations and planning
- The mapping enables reconciliation between planning system and actual Azure DevOps items
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib
from datetime import datetime

from devops_gateway.work_items import _run_wiql, _wit
from devops_gateway.connection import get_connection
from utils.settings import settings
from rich import print as rprint


@dataclass
class IDMapping:
    """Represents a mapping between local and Azure DevOps IDs."""
    local_id: str           # e.g., "pr-data-platform-001", "wi-user-auth-bug"
    azdo_id: int           # Azure DevOps auto-generated ID like 1234
    azdo_type: str         # "work_item", "pull_request"
    project: str           # Azure DevOps project name
    title: str             # Human-readable title
    created_date: str      # When mapping was created
    last_updated: str      # When mapping was last verified


class IDMappingManager:
    """Manages bidirectional mapping between local IDs and Azure DevOps IDs."""
    
    def __init__(self):
        self.connection = get_connection()
        self.mappings_file = Path("data") / "pm" / "id_mappings.json"
        self.mappings_file.parent.mkdir(exist_ok=True)
        self._mappings: Dict[str, IDMapping] = {}
        self._reverse_mappings: Dict[Tuple[int, str], str] = {}  # (azdo_id, type) -> local_id
        self.load_mappings()
    
    def load_mappings(self) -> None:
        """Load existing mappings from disk."""
        if self.mappings_file.exists():
            try:
                with open(self.mappings_file, 'r') as f:
                    data = json.load(f)
                    
                for mapping_data in data.get('mappings', []):
                    mapping = IDMapping(**mapping_data)
                    self._mappings[mapping.local_id] = mapping
                    self._reverse_mappings[(mapping.azdo_id, mapping.azdo_type)] = mapping.local_id
                    
            except Exception as e:
                rprint(f"  Could not load ID mappings: {e}")
    
    def save_mappings(self) -> None:
        """Save mappings to disk."""
        try:
            data = {
                'last_updated': datetime.utcnow().isoformat(),
                'mappings': [
                    {
                        'local_id': mapping.local_id,
                        'azdo_id': mapping.azdo_id,
                        'azdo_type': mapping.azdo_type,
                        'project': mapping.project,
                        'title': mapping.title,
                        'created_date': mapping.created_date,
                        'last_updated': mapping.last_updated
                    }
                    for mapping in self._mappings.values()
                ]
            }
            
            with open(self.mappings_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            rprint(f"  Could not save ID mappings: {e}")
    
    def generate_local_id(self, title: str, azdo_type: str, project: str = None) -> str:
        """Generate a human-readable local ID from title and context."""
        # Clean title for ID generation
        clean_title = ''.join(c.lower() if c.isalnum() else '-' for c in title)
        clean_title = '-'.join(word for word in clean_title.split('-') if word and len(word) > 1)
        
        # Truncate to reasonable length
        if len(clean_title) > 40:
            clean_title = clean_title[:40].rstrip('-')
        
        # Add type prefix
        type_prefix = {
            'pull_request': 'pr',
            'work_item': 'wi',
            'epic': 'epic',
            'feature': 'feat',
            'bug': 'bug',
            'task': 'task'
        }.get(azdo_type, 'item')
        
        base_id = f"{type_prefix}-{clean_title}"
        
        # Ensure uniqueness with counter suffix if needed
        counter = 1
        local_id = base_id
        while local_id in self._mappings:
            local_id = f"{base_id}-{counter:03d}"
            counter += 1
            
        return local_id
    
    def create_mapping(self, azdo_id: int, azdo_type: str, title: str, project: str, 
                      local_id: str = None) -> IDMapping:
        """Create a new ID mapping."""
        if not local_id:
            local_id = self.generate_local_id(title, azdo_type, project)
        
        # Check if mapping already exists
        if (azdo_id, azdo_type) in self._reverse_mappings:
            existing_local_id = self._reverse_mappings[(azdo_id, azdo_type)]
            return self._mappings[existing_local_id]
        
        mapping = IDMapping(
            local_id=local_id,
            azdo_id=azdo_id,
            azdo_type=azdo_type,
            project=project,
            title=title,
            created_date=datetime.utcnow().isoformat(),
            last_updated=datetime.utcnow().isoformat()
        )
        
        self._mappings[local_id] = mapping
        self._reverse_mappings[(azdo_id, azdo_type)] = local_id
        self.save_mappings()
        
        return mapping
    
    def get_local_id(self, azdo_id: int, azdo_type: str) -> Optional[str]:
        """Get local ID from Azure DevOps ID."""
        return self._reverse_mappings.get((azdo_id, azdo_type))
    
    def get_azdo_id(self, local_id: str) -> Optional[int]:
        """Get Azure DevOps ID from local ID."""
        mapping = self._mappings.get(local_id)
        return mapping.azdo_id if mapping else None
    
    def get_mapping(self, local_id: str) -> Optional[IDMapping]:
        """Get full mapping by local ID."""
        return self._mappings.get(local_id)
    
    def get_display_id(self, azdo_id: int, azdo_type: str, title: str = None, 
                      project: str = None) -> str:
        """
        DEPRECATED: This method was for display but should not be used for user-facing display.
        Use get_local_id() for internal PM-Agent operations only.
        For user display, always show the Azure DevOps ID directly (PR-{azdo_id}, WI-{azdo_id}).
        """
        local_id = self.get_local_id(azdo_id, azdo_type)
        
        if not local_id and title and project:
            # Create mapping on-the-fly for internal reference
            mapping = self.create_mapping(azdo_id, azdo_type, title, project)
            local_id = mapping.local_id
        
        return local_id or f"{azdo_type}-{azdo_id}"
    
    def sync_with_azure_devops(self, projects: List[str] = None) -> Dict[str, int]:
        """
        Sync mappings with current Azure DevOps state.
        Useful for discovering new items and updating titles.
        """
        if not projects:
            projects = [settings.azdo_project]
        
        results = {'updated': 0, 'created': 0, 'errors': 0}
        
        try:
            # Sync work items
            for project in projects:
                query = f"""
                SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State]
                FROM WorkItems
                WHERE [System.TeamProject] = '{project}'
                  AND [System.ChangedDate] >= @today - 30
                ORDER BY [System.Id] DESC
                """
                
                try:
                    work_items = _run_wiql(query)
                    
                    for wi in work_items:
                        azdo_id = wi['id']
                        fields = wi.get('fields', {})
                        title = fields.get('System.Title', 'Untitled')
                        wi_type = fields.get('System.WorkItemType', 'work_item').lower()
                        
                        local_id = self.get_local_id(azdo_id, 'work_item')
                        if not local_id:
                            self.create_mapping(azdo_id, 'work_item', title, project)
                            results['created'] += 1
                        else:
                            # Update title if changed
                            mapping = self._mappings[local_id]
                            if mapping.title != title:
                                mapping.title = title
                                mapping.last_updated = datetime.utcnow().isoformat()
                                results['updated'] += 1
                                
                except Exception as e:
                    rprint(f"  Could not sync work items from {project}: {e}")
                    results['errors'] += 1
            
            # Sync pull requests would go here (similar pattern)
            self.save_mappings()
            
        except Exception as e:
            rprint(f" Failed to sync with Azure DevOps: {e}")
            results['errors'] += 1
        
        return results
    
    def add_external_key_tag(self, azdo_id: int, local_id: str, azdo_type: str = 'work_item'):
        """Add external key tag to Azure DevOps work item for future lookups."""
        if azdo_type != 'work_item':
            return  # Only work items support tags currently
            
        try:
            from azure.devops.v7_0.work_item_tracking.models import JsonPatchOperation
            
            wit = _wit()
            wi = wit.get_work_item(id=azdo_id, fields=["System.Tags"])
            current_tags = wi.fields.get("System.Tags", "") or ""
            
            external_tag = f"external_key:{local_id}"
            if external_tag not in current_tags:
                new_tags = f"{current_tags}; {external_tag}".strip("; ")
                update = [JsonPatchOperation(op="replace", path="/fields/System.Tags", value=new_tags)]
                wit.update_work_item(document=update, id=azdo_id)
                rprint(f" Added external key tag '{local_id}' to work item #{azdo_id}")
                
        except Exception as e:
            rprint(f"  Could not add external key tag: {e}")
    
    def find_by_external_key(self, local_id: str) -> Optional[Dict]:
        """Find Azure DevOps work item by external key tag."""
        try:
            query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.Tags]
            WHERE [System.Tags] CONTAINS 'external_key:{local_id}'
            """
            
            results = _run_wiql(query)
            return results[0] if results else None
                
        except Exception as e:
            rprint(f"  Could not find by external key: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Get mapping statistics."""
        stats = {
            'total_mappings': len(self._mappings),
            'by_type': {},
            'by_project': {}
        }
        
        for mapping in self._mappings.values():
            # Count by type
            azdo_type = mapping.azdo_type
            stats['by_type'][azdo_type] = stats['by_type'].get(azdo_type, 0) + 1
            
            # Count by project
            project = mapping.project
            stats['by_project'][project] = stats['by_project'].get(project, 0) + 1
        
        return stats


# Global instance
_id_mapping_manager = None

def get_id_mapping_manager() -> IDMappingManager:
    """Get singleton ID mapping manager instance."""
    global _id_mapping_manager
    if _id_mapping_manager is None:
        _id_mapping_manager = IDMappingManager()
    return _id_mapping_manager


def create_display_id(azdo_id: int, azdo_type: str, title: str = None, project: str = None) -> str:
    """
    DEPRECATED: This creates internal mapping but should NOT be used for display.
    This function creates the mapping for internal reference but returns local_id.
    For user display, always show Azure DevOps ID directly (PR-{azdo_id}, WI-{azdo_id}).
    """
    return get_id_mapping_manager().get_display_id(azdo_id, azdo_type, title, project)


def map_azdo_to_local_id(azdo_id: int, azdo_type: str, title: str, project: str) -> str:
    """Create mapping and return local ID for internal PM-Agent reference only."""
    manager = get_id_mapping_manager()
    mapping = manager.create_mapping(azdo_id, azdo_type, title, project)
    return mapping.local_id