"""
Wiki-based PM-Agent interface for Azure DevOps.
Creates main PM-Agent page with plan summaries and interaction transcript sub-pages.
"""
from __future__ import annotations
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import json

from .plan_schema import StructuredPlan, EpicSpec, FeatureSpec
from .sync_engine import SyncEngine  
from devops_gateway.wiki import push_markdown_to_azure_wiki
from utils.settings import settings
from rich import print as rprint


class WikiInterface:
    """
    Manages wiki-based interface for PM-Agent interactions.
    Main page: /PM-Agent - plan summaries and status
    Sub-pages: /PM-Agent/Interactions/{timestamp} - conversation transcripts
    """
    
    def __init__(self):
        self.main_page_path = "/PM-Agent"
        self.interactions_path = "/PM-Agent/Interactions"
        self.sync_engine = SyncEngine()
    
    def format_plan_summary(self, plan: StructuredPlan, sync_status: Optional[Dict] = None) -> str:
        """Format a structured plan for wiki display."""
        lines = [
            f"## Plan: {plan.plan_id}",
            f"**Created:** {plan.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Goal:** {plan.business_goal}",
            ""
        ]
        
        # Sync status
        if sync_status:
            if sync_status.get("status") == "synced":
                lines.append("🟢 **Status:** Synced to Azure DevOps")
                lines.append(f"**Epics Created:** {len(sync_status.get('epics_created', []))}")
                lines.append(f"**Features Created:** {len(sync_status.get('features_created', []))}")
            elif sync_status.get("status") == "pending":
                lines.append("🟡 **Status:** Pending approval")
            else:
                lines.append("⚪ **Status:** Draft")
        else:
            lines.append("⚪ **Status:** Draft")
        
        lines.append("")
        
        # Epic summaries
        if plan.epics:
            lines.append("### 📋 Epics")
            for i, epic in enumerate(plan.epics, 1):
                lines.append(f"{i}. **{epic.title}** (`{epic.external_key}`)")
                lines.append(f"   - {epic.description}")
                lines.append(f"   - Features: {len(epic.features)}")
                if epic.business_value:
                    lines.append(f"   - Value: {epic.business_value}")
                lines.append("")
        
        # Hub-spoke architecture info
        if plan.hub_project or plan.spoke_projects:
            lines.append("### 🏗️ Architecture")
            if plan.hub_project:
                lines.append(f"**Hub Project:** {plan.hub_project}")
            if plan.spoke_projects:
                lines.append(f"**Spoke Projects:** {', '.join(plan.spoke_projects)}")
            lines.append("")
        
        return "\n".join(lines)
    
    def create_main_page(self, plans: List[StructuredPlan], interaction_logs: List[Dict] = None, silent: bool = False) -> str:
        """
        Create/update the main PM-Agent wiki page.
        Shows real overview of work items from Azure DevOps plus plan status.
        """
        current_time = datetime.utcnow()
        content = [
            "# PM-Agent Dashboard",
            "",
            "LLM-powered Program/Project Manager agent for Azure DevOps.",
            "",
            f"**Last Updated:** {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')} (Build {current_time.strftime('%Y%m%d-%H%M%S')})",
            f"**Auto-refresh:** Dashboard updates automatically after plan generation and sync operations",
            ""
        ]
        
        # Get real work item data from Azure DevOps
        try:
            from devops_gateway.work_items import list_epics, list_features_and_stories, list_orphan_features
            
            # Get current work items
            epics = list_epics()
            orphan_features = list_orphan_features()
            
            content.extend([
                "## 📊 Work Item Overview",
                "",
                f"| Type | Count | Status |",
                f"| --- | --- | --- |",
                f"| 📋 Epics | {len(epics)} | [View All](../../../_workitems?_a=query&wiql=SELECT%20%5BSystem.Id%5D%2C%20%5BSystem.Title%5D%2C%20%5BSystem.State%5D%20FROM%20WorkItems%20WHERE%20%5BSystem.WorkItemType%5D%20%3D%20%27Epic%27) |"
            ])
            
            # Count features under epics
            total_features = 0
            for epic in epics:
                features = list_features_and_stories(epic['id'])
                total_features += len(features)
            
            content.append(f"| 🎯 Features | {total_features + len(orphan_features)} | [View All](../../../_workitems?_a=query&wiql=SELECT%20%5BSystem.Id%5D%2C%20%5BSystem.Title%5D%2C%20%5BSystem.State%5D%20FROM%20WorkItems%20WHERE%20%5BSystem.WorkItemType%5D%20IN%20%28%27Feature%27%2C%27User%20Story%27%29) |")
            
            if orphan_features:
                content.append(f"| ⚠️ Orphaned Features | {len(orphan_features)} | Need parent Epic assignment |")
            
            content.extend([
                "",
                "## 📋 Active Epics",
                ""
            ])
            
            if not epics:
                content.append("*No epics found. Create your first plan to get started.*")
            else:
                # Show detailed epic information
                for epic in epics[:10]:  # Show top 10 epics
                    epic_id = epic['id']
                    epic_title = epic['fields']['System.Title']
                    epic_state = epic['fields']['System.State']
                    
                    # Get features for this epic
                    features = list_features_and_stories(epic_id)
                    
                    # Check if this epic has external_key (PM-Agent created)
                    epic_tags = epic['fields'].get('System.Tags', '') or ''
                    external_key = None
                    if 'external_key:' in epic_tags:
                        for tag in epic_tags.split(';'):
                            if tag.strip().startswith('external_key:'):
                                external_key = tag.strip().replace('external_key:', '')
                                break
                    
                    content.extend([
                        f"### 📋 {epic_title}",
                        "",
                        f"**ID:** #{epic_id} | **State:** {epic_state} | **Features:** {len(features)}",
                    ])
                    
                    if external_key:
                        content.append(f"**PM-Agent Key:** `{external_key}` | **Status:** 🤖 AI-Generated")
                    else:
                        content.append(f"**Status:** 👤 Manually Created")
                    
                    content.append("")
                    
                    if features:
                        content.append("**Features:**")
                        for feature in features[:5]:  # Show top 5 features per epic
                            feature_title = feature['fields']['System.Title']
                            feature_state = feature['fields']['System.State']
                            feature_type = feature['fields']['System.WorkItemType']
                            content.append(f"- {feature_title} (#{feature['id']}, {feature_type}, {feature_state})")
                        
                        if len(features) > 5:
                            content.append(f"- *... and {len(features) - 5} more features*")
                        content.append("")
                    else:
                        content.append("*No features assigned to this epic.*")
                        content.append("")
                
                if len(epics) > 10:
                    content.append(f"*... and {len(epics) - 10} more epics. [View all epics](../../../_workitems)*")
            
            # Show orphaned work items if any
            if orphan_features:
                content.extend([
                    "",
                    "## ⚠️ Orphaned Features",
                    "",
                    "*These features need to be assigned to an Epic:*",
                    ""
                ])
                
                for feature in orphan_features[:5]:
                    feature_title = feature['fields']['System.Title']
                    feature_type = feature['fields']['System.WorkItemType']
                    content.append(f"- {feature_title} (#{feature['id']}, {feature_type})")
                
                if len(orphan_features) > 5:
                    content.append(f"- *... and {len(orphan_features) - 5} more orphaned features*")
        
        except Exception as e:
            content.extend([
                "## ⚠️ Work Item Data Unavailable",
                "",
                f"Could not retrieve current work items: {e}",
                ""
            ])
        
        # Plan Generation Status
        content.extend([
            "",
            "## 🤖 PM-Agent Plans",
            ""
        ])
        
        if not plans:
            content.append("*No AI-generated plans yet.*")
        else:
            content.extend([
                "| Plan ID | Created | Goal | Status | Actions |",
                "| --- | --- | --- | --- | --- |"
            ])
            
            # Sort plans by creation date (newest first)
            sorted_plans = sorted(plans, key=lambda p: p.created_at, reverse=True)
            
            for plan in sorted_plans[:5]:  # Show last 5 plans
                sync_status = self._get_plan_sync_status(plan)
                status_icon = "🟢" if sync_status.get("status") == "synced" else "🟡"
                status_text = "Synced" if sync_status.get("status") == "synced" else "Draft"
                
                goal_short = plan.business_goal[:40] + "..." if len(plan.business_goal) > 40 else plan.business_goal
                created_date = plan.created_at.strftime('%m/%d %H:%M')
                
                preview_cmd = f"`preview outputs/{plan.plan_id}.json`"
                sync_cmd = f"`sync outputs/{plan.plan_id}.json --approve`"
                
                content.append(f"| `{plan.plan_id}` | {created_date} | {goal_short} | {status_icon} {status_text} | {preview_cmd}<br>{sync_cmd} |")
            
            if len(sorted_plans) > 5:
                content.append(f"| *... and {len(sorted_plans) - 5} more plans* | | | | |")
        
        # Recent interactions
        if interaction_logs:
            content.extend([
                "",
                "## 💬 Recent Interactions",
                "",
                "| Timestamp | Goal | Plan Generated | Transcript |",
                "| --- | --- | --- | --- |"
            ])
            
            for log in interaction_logs[-5:]:  # Show last 5 interactions
                timestamp = log.get('timestamp', 'Unknown')[:16]  # Short timestamp
                goal = log.get('business_goal', 'No goal specified')[:30]
                if len(goal) > 30:
                    goal += "..."
                plan_id = log.get('plan_id', 'N/A')
                session_id = log.get('session_id', 'unknown')
                
                plan_link = f"`{plan_id}`" if plan_id != 'N/A' else "❌"
                transcript_link = f"[View](/PM-Agent/Interactions/{session_id})"
                
                content.append(f"| {timestamp} | {goal} | {plan_link} | {transcript_link} |")
        
        # Quick actions and instructions
        content.extend([
            "",
            "## 🚀 Quick Actions",
            "",
            "```bash",
            "# Create a new plan",
            'python -m src.cli.main plan-new "Your business goal here"',
            "",
            "# Preview what changes a plan will make",
            "python -m src.cli.main preview outputs/PLAN-ID.json",
            "",
            "# Apply a plan to Azure DevOps",
            "python -m src.cli.main sync outputs/PLAN-ID.json --approve",
            "",
            "# Update this dashboard manually",
            "python -m src.cli.main update-dashboard",
            "```",
            "",
            "## 🔗 Quick Links",
            "",
            "- [📋 Azure DevOps Work Items](../../../_workitems)",
            "- [📊 Azure DevOps Boards](../../../_boards)", 
            "- [📈 Azure DevOps Analytics](../../../_analytics)",
            "- [💬 All Interactions](/PM-Agent/Interactions)",
            ""
        ])
        
        wiki_content = "\n".join(content)
        
        # Push to Azure DevOps wiki
        success = push_markdown_to_azure_wiki(wiki_content, self.main_page_path)
        if not silent:
            if success:
                rprint(f"✅ Updated PM-Agent dashboard: {self.main_page_path}")
            else:
                rprint(f"⚠️  Dashboard updated locally but wiki update failed")
        
        return wiki_content
    
    def create_interaction_transcript(self, session_id: str, interaction_data: Dict) -> str:
        """
        Create a sub-page for interaction transcript.
        Documents the actual CLI interaction like a terminal session.
        """
        page_path = f"{self.interactions_path}/{session_id}"
        
        content = [
            f"# CLI Interaction: {session_id}",
            "",
            f"**Timestamp:** {interaction_data.get('timestamp', datetime.utcnow().isoformat())}",
            f"**User:** {interaction_data.get('user', 'PM-Agent User')}",
            f"**Session Duration:** {interaction_data.get('duration', 'N/A')}",
            ""
        ]
        
        # CLI Command and Output Section
        content.extend([
            "## 🖥️ CLI Session",
            "",
            "```bash"
        ])
        
        # Show the actual command that was run
        business_goal = interaction_data.get('business_goal', 'Unknown Goal')
        content.extend([
            f"# Command executed",
            f'python -m src.cli.main plan-new "{business_goal}"',
            "",
            "# Output:",
            f"🎯 Business Goal: {business_goal}",
            "🤖 Generating structured plan..."
        ])
        
        # Show the results
        if 'generated_plan' in interaction_data:
            plan_data = interaction_data['generated_plan']
            plan_id = plan_data.get('plan_id', 'Unknown')
            file_path = plan_data.get('file_path', 'Unknown')
            
            content.extend([
                f"✅ Structured plan created: {file_path}",
                f"📋 Plan ID: {plan_id}",
            ])
            
            # Show epic count if available
            if 'plan_object' in plan_data:
                plan = StructuredPlan(**plan_data['plan_object'])
                content.append(f"🏗️  Epics: {len(plan.epics)}")
        
        # Show wiki creation results
        content.extend([
            f"✅ Created interaction transcript: /PM-Agent/Interactions/{session_id}",
            "📊 Dashboard updated automatically",
            "",
            "🔍 Next steps:",
            f"  1. Review plan: python -m src.cli.main preview outputs/{plan_id}.json", 
            f"  2. Apply changes: python -m src.cli.main sync outputs/{plan_id}.json --approve",
            "```",
            ""
        ])
        
        # Plan Details Section
        if 'generated_plan' in interaction_data and 'plan_object' in interaction_data['generated_plan']:
            plan = StructuredPlan(**interaction_data['generated_plan']['plan_object'])
            
            content.extend([
                "## 📋 Generated Plan Details",
                "",
                f"**Business Goal:** {plan.business_goal}",
                f"**Plan ID:** `{plan.plan_id}`",
                f"**Created:** {plan.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
                f"**Hub Project:** {plan.hub_project or 'Not specified'}",
                f"**Spoke Projects:** {', '.join(plan.spoke_projects) if plan.spoke_projects else 'None'}",
                "",
                "### 📊 Epic Summary",
                ""
            ])
            
            for epic in plan.epics:
                content.extend([
                    f"#### 📋 {epic.title} (`{epic.external_key}`)",
                    f"**Description:** {epic.description}",
                    f"**Business Value:** {epic.business_value or 'Not specified'}",
                    f"**Success Metrics:** {', '.join(epic.success_metrics) if epic.success_metrics else 'None'}",
                    f"**Features:** {len(epic.features)}",
                    ""
                ])
                
                if epic.features:
                    content.append("**Features:**")
                    for feature in epic.features:
                        content.extend([
                            f"",
                            f"  🎯 **{feature.title}** (`{feature.external_key}`)",
                            f"      *Description:* {feature.description}",
                        ])
                        
                        if feature.target_projects:
                            content.append(f"      *Target Projects:* {', '.join(feature.target_projects)}")
                        
                        if feature.acceptance_criteria:
                            content.append(f"      *Acceptance Criteria:*")
                            for ac in feature.acceptance_criteria:
                                content.append(f"        • {ac}")
                        
                        if feature.metrics:
                            content.append(f"      *Metrics:* {', '.join(feature.metrics)}")
                        
                        # Show stories per project
                        if feature.stories_per_project:
                            content.append(f"      *User Stories:*")
                            for project, story in feature.stories_per_project.items():
                                content.extend([
                                    f"",
                                    f"        📝 **{project}:** {story.title} (`{story.external_key}`)",
                                    f"            *Template:* {story.story_template}",
                                ])
                                
                                if story.acceptance_criteria:
                                    content.append(f"            *Story Acceptance Criteria:*")
                                    for sac in story.acceptance_criteria:
                                        content.append(f"              • {sac}")
                                
                                if story.tasks:
                                    content.append(f"            *Tasks:*")
                                    for task in story.tasks:
                                        days_text = f" ({task.estimated_days} days)" if task.estimated_days else ""
                                        content.extend([
                                            f"              ✅ **{task.title}**{days_text} (`{task.external_key}`)",
                                            f"                 {task.description}",
                                        ])
                                content.append("")
                    content.append("")
        
        # File Information
        content.extend([
            "## 📁 Generated Files",
            "",
            "| File | Description | Status |",
            "| --- | --- | --- |"
        ])
        
        if 'generated_plan' in interaction_data:
            plan_data = interaction_data['generated_plan']
            file_path = plan_data.get('file_path', 'Unknown')
            plan_id = plan_data.get('plan_id', 'Unknown')
            content.append(f"| `{file_path}` | Structured plan JSON | ✅ Created |")
        
        content.extend([
            f"| `/PM-Agent/Interactions/{session_id}` | This interaction transcript | ✅ Created |",
            "",
        ])
        
        # Next Actions
        content.extend([
            "## 🚀 Next Actions",
            "",
            "1. **Review the plan:** Open the generated JSON file to review the structured plan",
            "2. **Preview changes:** Use the preview command to see what will be created in Azure DevOps", 
            "3. **Apply changes:** Use the sync command with --approve to create work items",
            "4. **Monitor progress:** Check the PM-Agent dashboard for updated status",
            "",
            "## 🔗 Quick Links",
            "",
            f"- [🏠 PM-Agent Dashboard]({self.main_page_path})",
            "- [📋 Azure DevOps Work Items](../../../_workitems)",
            "- [📊 Azure DevOps Boards](../../../_boards)",
            ""
        ])
        
        wiki_content = "\n".join(content)
        
        # Push to Azure DevOps wiki
        success = push_markdown_to_azure_wiki(wiki_content, page_path)
        if success:
            rprint(f"✅ Created interaction transcript: {page_path}")
        else:
            rprint(f"⚠️  Interaction transcript created locally but wiki update failed")
        
        return wiki_content
    
    def _get_plan_sync_status(self, plan: StructuredPlan) -> Optional[Dict]:
        """Check if plan has been synced by looking for sync results file."""
        outputs_dir = Path("outputs")
        results_file = outputs_dir / f"{plan.plan_id}-sync-results.json"
        
        if results_file.exists():
            try:
                with open(results_file, 'r') as f:
                    results = json.load(f)
                return {**results, "status": "synced"}
            except:
                pass
        
        return {"status": "draft"}
    
    def update_dashboard(self, silent: bool = False) -> str:
        """
        Update the main dashboard with all available plans.
        Scans plans directory for structured plans.
        If silent=True, only shows errors.
        """
        outputs_dir = Path("outputs")
        plans = []
        
        if outputs_dir.exists():
            for plan_file in outputs_dir.glob("PLAN-*.json"):
                try:
                    plan = self.sync_engine.load_plan(plan_file)
                    plans.append(plan)
                except Exception as e:
                    if not silent:
                        rprint(f"⚠️  Failed to load plan {plan_file}: {e}")
        
        return self.create_main_page(plans, silent=silent)
    
    def auto_update_dashboard(self) -> bool:
        """
        Automatically update dashboard (silent mode).
        Returns True if successful, False if failed.
        """
        try:
            self.update_dashboard(silent=True)
            return True
        except Exception as e:
            # Log the error but don't show to user
            print(f"Dashboard auto-update failed: {e}")
            return False


# Utility functions for CLI integration
def update_wiki_dashboard():
    """CLI command to update the PM-Agent wiki dashboard."""
    interface = WikiInterface()
    return interface.update_dashboard()

def create_interaction_log(business_goal: str, plan_path: Path, conversation: List[Dict] = None) -> str:
    """Create interaction transcript after plan generation."""
    interface = WikiInterface()
    session_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    
    # Load plan details
    plan_data = {"file_path": str(plan_path)}
    try:
        plan = interface.sync_engine.load_plan(plan_path)
        plan_data.update({
            "plan_id": plan.plan_id,
            "plan_object": plan.model_dump()
        })
    except Exception as e:
        rprint(f"⚠️  Could not load plan details: {e}")
    
    interaction_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "business_goal": business_goal,
        "generated_plan": plan_data,
        "conversation": conversation or []
    }
    
    interface.create_interaction_transcript(session_id, interaction_data)
    interface.auto_update_dashboard()  # Silently refresh main page
    
    return session_id