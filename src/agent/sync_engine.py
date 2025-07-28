"""
Deterministic sync/ops layer that processes structured plans.
Follows FEEDBACK.md architecture - never lets LLM touch APIs directly.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json

from .plan_schema import StructuredPlan, EpicSpec, FeatureSpec, StorySpec, TaskSpec, PlanDiff
from devops_gateway.work_items import (
    list_epics, create_work_item, _run_wiql, _wit
)
from devops_gateway.wiki import push_markdown_to_azure_wiki
from utils.settings import settings
from rich import print as rprint


class SyncEngine:
    """
    Deterministic engine that reads structured plans and syncs to Azure DevOps.
    Idempotent, diff-first, uses external_key for stable references.
    """
    
    def __init__(self):
        self.hub_project = settings.azdo_project  # For now, use configured project
    
    def load_plan(self, plan_path: Path) -> StructuredPlan:
        """Load structured plan from file."""
        with open(plan_path, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)
        return StructuredPlan(**plan_data)
    
    def find_work_item_by_external_key(self, external_key: str, project: str = None) -> Optional[Dict]:
        """
        Find work item by external_key stored in tags or custom field.
        Returns work item dict if found, None otherwise.
        """
        project = project or self.hub_project
        query = f"""
        SELECT [System.Id], [System.Title], [System.WorkItemType], [System.Tags], [System.State]
        FROM WorkItems
        WHERE [System.TeamProject] = '{project}'
          AND [System.Tags] CONTAINS 'external_key:{external_key}'
        """
        results = _run_wiql(query)
        return results[0] if results else None
    
    def add_external_key_tag(self, work_item_id: int, external_key: str):
        """Add external_key as a tag to work item for future lookups."""
        from azure.devops.v7_0.work_item_tracking.models import JsonPatchOperation
        
        # Get current tags
        wit = _wit()
        wi = wit.get_work_item(id=work_item_id, fields=["System.Tags"])
        current_tags = wi.fields.get("System.Tags", "") or ""
        
        # Add external_key tag if not present
        external_tag = f"external_key:{external_key}"
        if external_tag not in current_tags:
            new_tags = f"{current_tags}; {external_tag}".strip("; ")
            update = [JsonPatchOperation(op="replace", path="/fields/System.Tags", value=new_tags)]
            wit.update_work_item(document=update, id=work_item_id)
    
    def generate_diff(self, plan: StructuredPlan) -> PlanDiff:
        """
        Compare structured plan against current Azure DevOps state.
        Returns diff showing what changes would be made.
        """
        diff = PlanDiff(plan_id=plan.plan_id)
        
        # Check each epic in the plan
        for epic_spec in plan.epics:
            existing_epic = self.find_work_item_by_external_key(epic_spec.external_key)
            
            if not existing_epic:
                diff.epics_to_create.append(epic_spec)
            elif existing_epic["fields"]["System.Title"] != epic_spec.title:
                diff.epics_to_update.append({
                    "spec": epic_spec,
                    "current": existing_epic
                })
            
            # Check features within each epic
            for feature_spec in epic_spec.features:
                existing_feature = self.find_work_item_by_external_key(feature_spec.external_key)
                
                if not existing_feature:
                    diff.features_to_create.append(feature_spec)
                elif existing_feature["fields"]["System.Title"] != feature_spec.title:
                    diff.features_to_update.append({
                        "spec": feature_spec,
                        "current": existing_feature
                    })
        
        return diff
    
    def preview_changes(self, plan: StructuredPlan) -> str:
        """
        Generate human-readable preview of changes.
        Used for diff-first approval workflow.
        """
        diff = self.generate_diff(plan)
        
        if not diff.has_changes():
            return "✅ No changes needed - plan matches current Azure DevOps state"
        
        preview = [f"📋 Plan: {plan.plan_id}", f"🎯 Goal: {plan.business_goal}", ""]
        
        if diff.epics_to_create:
            preview.append("🆕 **Epics to Create:**")
            for epic in diff.epics_to_create:
                preview.append(f"  • {epic.title} ({epic.external_key})")
                preview.append(f"    {epic.description[:100]}...")
        
        if diff.epics_to_update:
            preview.append("📝 **Epics to Update:**")
            for item in diff.epics_to_update:
                spec, current = item["spec"], item["current"]
                preview.append(f"  • {current['fields']['System.Title']} → {spec.title}")
        
        if diff.features_to_create:
            preview.append("🆕 **Features to Create:**")
            for feature in diff.features_to_create:
                preview.append(f"  • {feature.title} ({feature.external_key})")
                preview.append(f"    Target projects: {', '.join(feature.target_projects)}")
        
        if diff.features_to_update:
            preview.append("📝 **Features to Update:**")
            for item in diff.features_to_update:
                spec, current = item["spec"], item["current"]
                preview.append(f"  • {current['fields']['System.Title']} → {spec.title}")
        
        return "\n".join(preview)
    
    def sync_plan(self, plan: StructuredPlan, dry_run: bool = False) -> Dict:
        """
        Apply structured plan to Azure DevOps.
        If dry_run=True, only shows what would happen.
        """
        diff = self.generate_diff(plan)
        
        if dry_run:
            return {
                "status": "dry_run",
                "preview": self.preview_changes(plan),
                "changes": diff.model_dump()
            }
        
        results = {
            "plan_id": plan.plan_id,
            "epics_created": [],
            "epics_updated": [],
            "features_created": [],
            "features_updated": []
        }
        
        # Create new epics
        for epic_spec in diff.epics_to_create:
            wi = create_work_item(
                "Epic",
                epic_spec.title,
                epic_spec.description
            )
            self.add_external_key_tag(wi["id"], epic_spec.external_key)
            results["epics_created"].append({
                "external_key": epic_spec.external_key,
                "work_item_id": wi["id"],
                "title": epic_spec.title
            })
            rprint(f"✅ Created Epic: {epic_spec.title} (#{wi['id']}, {epic_spec.external_key})")
        
        # Update existing epics
        for item in diff.epics_to_update:
            spec, current = item["spec"], item["current"]
            # TODO: Implement work item updates
            rprint(f"📝 Would update Epic #{current['id']}: {current['fields']['System.Title']} → {spec.title}")
        
        # Create new features
        for feature_spec in diff.features_to_create:
            # Find parent epic
            parent_epic = self.find_work_item_by_external_key(
                next(epic.external_key for epic in plan.epics 
                     if feature_spec in epic.features)
            )
            
            if parent_epic:
                wi = create_work_item(
                    "Feature",
                    feature_spec.title,
                    feature_spec.description,
                    parent_id=parent_epic["id"]
                )
                self.add_external_key_tag(wi["id"], feature_spec.external_key)
                results["features_created"].append({
                    "external_key": feature_spec.external_key,
                    "work_item_id": wi["id"],
                    "title": feature_spec.title,
                    "parent_epic_id": parent_epic["id"]
                })
                rprint(f"✅ Created Feature: {feature_spec.title} (#{wi['id']}, {feature_spec.external_key})")
        
        return results
    
    def sync_plan_from_file(self, plan_path: Path, dry_run: bool = False) -> Dict:
        """Load plan from file and sync to Azure DevOps."""
        plan = self.load_plan(plan_path)
        return self.sync_plan(plan, dry_run=dry_run)


def sync_command(plan_path: str, dry_run: bool = False, approve: bool = False) -> None:
    """
    CLI command for syncing plans.
    Implements diff-first workflow with approval.
    """
    engine = SyncEngine()
    path = Path(plan_path)
    
    if not path.exists():
        rprint(f"❌ Plan file not found: {plan_path}")
        return
    
    plan = engine.load_plan(path)
    
    # Always show preview first
    preview = engine.preview_changes(plan)
    rprint(preview)
    
    if dry_run:
        rprint("\n🔍 Dry run mode - no changes applied")
        return
    
    diff = engine.generate_diff(plan)
    if not diff.has_changes():
        rprint("\n✅ No sync needed")
        return
    
    # Require approval for actual changes
    if not approve:
        rprint("\n⚠️  Use --approve to apply these changes")
        return
    
    # Apply changes
    rprint("\n🚀 Applying changes...")
    results = engine.sync_plan(plan, dry_run=False)
    
    # Save results summary
    summary_path = path.parent / f"{plan.plan_id}-sync-results.json"
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    rprint(f"\n✅ Sync complete! Results saved to {summary_path}")