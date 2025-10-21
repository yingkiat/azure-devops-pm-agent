"""
Wiki Reporter for AI-driven Azure DevOps insights.
Creates diary-style entries in Azure DevOps wiki for centralized PM visibility.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json

from devops_gateway.wiki import push_markdown_to_azure_wiki
from utils.settings import settings
from utils.config import get_config


class AIWikiReporter:
    """
    Diary-style wiki reporter for AI orchestration results.
    Appends new entries rather than updating existing pages to avoid conflicts.
    """
    
    def __init__(self):
        self.config = get_config()
        self.base_path = self.config.wiki_reports_path
        self.current_month_path = None
        self._update_current_month_path()
    
    def _update_current_month_path(self):
        """Update the current month path based on today's date."""
        current_date = datetime.now()
        year_month = current_date.strftime('%Y-%m-%B')
        self.current_month_path = self.config.get_wiki_path("monthly_report", year_month)
    
    def create_ai_report_entry(self, ai_result: Dict[str, Any]) -> Optional[str]:
        """
        Create a new AI report entry in the wiki.
        Returns the wiki path if successful, None if failed.
        """
        try:
            # Generate entry content
            entry_content = self._format_ai_result(ai_result)
            
            # Create unique page path with timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            session_id = ai_result.get("session_id", timestamp)
            year_month = datetime.now().strftime('%Y-%m-%B')
            entry_name = f"{timestamp}-{session_id[:8]}"
            page_path = self.config.get_wiki_path("daily_entry", year_month, entry_name)
            
            # Push to wiki
            success = push_markdown_to_azure_wiki(entry_content, page_path)
            
            if success:
                return page_path
            else:
                print(f"  Failed to create wiki entry at {page_path}")
                return None
                
        except Exception as e:
            print(f" Wiki reporting error: {e}")
            return None
    
    def _format_ai_result(self, ai_result: Dict[str, Any]) -> str:
        """Format AI orchestration result into markdown for wiki display."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        user_request = ai_result.get("user_request", "Unknown request")
        success = ai_result.get("success", False)
        
        # Handle manual wiki pushes differently
        if ai_result.get("manual_push"):
            return self._format_manual_push(ai_result, timestamp)
        
        # Start building content for automatic results
        lines = [
            f"# AI Analysis Report - {timestamp}",
            "",
            f"**Request:** {user_request}",
            f"**Status:** {' Completed' if success else ' Failed'}",
            f"**Session ID:** {ai_result.get('session_id', 'N/A')}",
            ""
        ]
        
        # Add intent classification if available
        if "classified_intent" in ai_result:
            intent = ai_result["classified_intent"]
            lines.extend([
                "##  Intent Analysis",
                f"- **Intent Type:** {intent.get('intent', 'N/A')}",
                f"- **Confidence:** {intent.get('confidence', 0):.2f}",
                f"- **Description:** {intent.get('description', 'N/A')}",
                ""
            ])
        
        # Add execution results if available
        if "execution_result" in ai_result and ai_result["execution_result"].get("results"):
            lines.append("##  Execution Results")
            
            results = ai_result["execution_result"]["results"]
            successful_steps = [r for r in results if r.get("success", False)]
            failed_steps = [r for r in results if not r.get("success", False)]
            
            lines.append(f"- **Total Steps:** {len(results)}")
            lines.append(f"- **Successful:** {len(successful_steps)}")
            lines.append(f"- **Failed:** {len(failed_steps)}")
            lines.append("")
            
            # Show key data found
            total_items = 0
            for result in successful_steps:
                data = result.get("data", {})
                if "work_items" in data:
                    count = data.get("count", len(data["work_items"]))
                    total_items += count
                elif "projects" in data:
                    count = len(data["projects"])
                    lines.append(f"- **Projects Found:** {count}")
                elif "repositories" in data:
                    count = len(data["repositories"])
                    lines.append(f"- **Repositories Found:** {count}")
            
            if total_items > 0:
                lines.append(f"- **Work Items Found:** {total_items}")
            
            lines.append("")
        
        # Add business intelligence if available
        if "business_intelligence" in ai_result:
            bi_data = ai_result["business_intelligence"]
            lines.extend(self._format_business_intelligence(bi_data))
        
        # Add context stats if available
        if "context_stats" in ai_result:
            stats = ai_result["context_stats"]
            lines.extend([
                "##  Context & Learning",
                f"- **Conversations Tracked:** {stats.get('conversation_entries', 0)}",
                f"- **Projects Known:** {stats.get('known_projects', 0)}",
                f"- **Total Interactions:** {stats.get('total_interactions', 0)}",
                ""
            ])
        
        # Add raw execution details in collapsible section
        if ai_result.get("execution_result", {}).get("results"):
            lines.extend([
                "##  Detailed Execution Log",
                "<details>",
                "<summary>Click to expand execution details</summary>",
                "",
                "| Step | Tool | Status | Purpose |",
                "|------|------|---------|---------|"
            ])
            
            for result in ai_result["execution_result"]["results"]:
                step = result.get("step", "N/A")
                tool = result.get("tool", "N/A")
                status = "" if result.get("success", False) else ""
                purpose = result.get("purpose", "N/A")[:50]
                lines.append(f"| {step} | {tool} | {status} | {purpose} |")
            
            lines.extend(["", "</details>", ""])
        
        # Add footer
        lines.extend([
            "---",
            f"*Generated by AI Orchestrator at {timestamp}*",
            "",
            "** Quick Actions:**",
            "- Run similar analysis: `python -m src.cli.ai_cli chat`",
            f"- Repeat this query: `python -m src.cli.ai_cli ask \"{user_request}\"`"
        ])
        
        return "\n".join(lines)
    
    def _format_business_intelligence(self, bi_data: Dict[str, Any]) -> List[str]:
        """Format business intelligence data for wiki display."""
        lines = ["##  Business Intelligence"]
        
        # Executive summary
        if bi_data.get("executive_summary"):
            lines.extend([
                f"**Executive Summary:** {bi_data['executive_summary']}",
                ""
            ])
        
        # Project insights
        projects = bi_data.get("projects", [])
        if projects:
            lines.append("###  Project Health Analysis")
            lines.append("")
            
            for project in projects:
                name = project.get("project_name", "Unknown Project")
                health_score = project.get("health_score", 0)
                
                # Health emoji based on score
                if health_score >= 0.8:
                    health_emoji = "🟢"
                    health_status = "Healthy"
                elif health_score >= 0.6:
                    health_emoji = "🟡"
                    health_status = "At Risk"
                else:
                    health_emoji = ""
                    health_status = "Needs Attention"
                
                lines.append(f"#### {health_emoji} {name} - {health_status} ({health_score:.1f}/1.0)")
                
                # Key metrics
                metrics = project.get("key_metrics", {})
                if metrics:
                    lines.extend([
                        f"- **Work Items:** {metrics.get('total_work_items', 0)}",
                        f"- **Repositories:** {metrics.get('repositories', 0)}",
                        f"- **Recent Activity:** {metrics.get('recent_activity', 0)} items",
                        ""
                    ])
                
                # Top recommendations
                recommendations = project.get("recommendations", [])[:3]
                if recommendations:
                    lines.append("**Top Recommendations:**")
                    for rec in recommendations:
                        lines.append(f"- {rec}")
                    lines.append("")
        
        # Team insights
        team_insights = bi_data.get("team_insights", {})
        if team_insights and team_insights.get("workload_distribution"):
            lines.append("###  Team Workload")
            workload = team_insights["workload_distribution"]
            
            # Show top contributors
            sorted_workload = sorted(workload.items(), key=lambda x: x[1], reverse=True)[:5]
            for member, count in sorted_workload:
                lines.append(f"- **{member}:** {count} items")
            lines.append("")
        
        # Strategic recommendations
        overall_recs = bi_data.get("overall_recommendations", [])[:5]
        if overall_recs:
            lines.append("###  Strategic Recommendations")
            for rec in overall_recs:
                lines.append(f"- {rec}")
            lines.append("")
        
        return lines
    
    def _format_manual_push(self, ai_result: Dict[str, Any], timestamp: str) -> str:
        """Format manually pushed conversation content for wiki."""
        user_request = ai_result.get("user_request", "Manual wiki push")
        conversation_content = ai_result.get("conversation_content", [])
        
        lines = [
            f"# Conversation Documentation - {timestamp}",
            "",
            f"**Manually Saved:** {user_request}",
            f"**Content:** {len(conversation_content)} conversation exchange(s)",
            f"**Session ID:** {ai_result.get('session_id', 'N/A')}",
            ""
        ]
        
        if not conversation_content:
            lines.extend([
                "## No Content Available",
                "No conversation exchanges were found to document.",
                ""
            ])
        else:
            lines.extend([
                "## Conversation Exchanges",
                ""
            ])
            
            for i, exchange in enumerate(conversation_content, 1):
                exchange_time = exchange.get('timestamp', 'Unknown time')
                if 'T' in exchange_time:
                    # Format ISO timestamp to readable format
                    try:
                        dt = datetime.fromisoformat(exchange_time.replace('Z', '+00:00'))
                        exchange_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                lines.extend([
                    f"### Exchange {i} - {exchange_time}",
                    f"**User Request:** {exchange['user_request']}",
                    f"**AI Response:** {exchange['ai_response']}",
                    f"**Intent:** {exchange.get('intent', 'Unknown')}",
                    f"**Status:** {' Success' if exchange.get('success') else ' Failed'}",
                    ""
                ])
                
                # Add technical details if available
                if exchange.get('full_result') and exchange.get('success'):
                    full_result = exchange['full_result']
                    if isinstance(full_result, dict) and 'execution_result' in full_result:
                        exec_result = full_result['execution_result']
                        if isinstance(exec_result, dict) and exec_result.get('results'):
                            lines.append("**Technical Details:**")
                            for result in exec_result['results']:
                                if isinstance(result, dict) and result.get('success'):
                                    tool = result.get('tool', 'unknown')
                                    purpose = result.get('purpose', 'No purpose specified')
                                    lines.append(f"- **{tool}:** {purpose}")
                            lines.append("")
        
        # Add footer
        lines.extend([
            "---",
            f"*Manually documented at {timestamp}*",
            "",
            "** Quick Actions:**",
            "- Continue analysis: `python -m src.cli.ai_cli chat`",
            "- Run new query: `python -m src.cli.ai_cli ask \"your question\"`",
            "- Push more content: `python -m src.cli.ai_cli ask \"push [description] to wiki\"`"
        ])
        
        return "\n".join(lines)
    
    def create_monthly_index(self) -> Optional[str]:
        """
        Create or update the monthly index page with links to all reports.
        This provides a centralized view for PMs.
        """
        try:
            current_date = datetime.now()
            month_name = current_date.strftime("%B %Y")
            
            content = [
                f"# AI Reports - {month_name}",
                "",
                "This page contains all AI-generated Azure DevOps insights for this month.",
                "",
                "##  Quick Stats",
                f"- **Month:** {month_name}",
                f"- **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                "",
                "##  Recent Reports",
                "",
                "*Reports appear as separate diary entries. Each entry captures a specific analysis or query result.*",
                "",
                "##  How to Use",
                "",
                "To generate new insights:",
                "1. **Natural Language:** `python -m src.cli.ai_cli ask \"your question\"`",
                "2. **Interactive Mode:** `python -m src.cli.ai_cli chat`",
                "3. **Project Health:** `python -m src.cli.ai_cli ask \"Analyze project health\"`",
                "",
                "---",
                f"*Auto-generated index for {month_name}*"
            ]
            
            success = push_markdown_to_azure_wiki("\n".join(content), self.current_month_path)
            
            if success:
                return self.current_month_path
            else:
                print(f"  Failed to create monthly index at {self.current_month_path}")
                return None
                
        except Exception as e:
            print(f" Monthly index creation error: {e}")
            return None


def create_wiki_entry_from_ai_result(ai_result: Dict[str, Any]) -> Optional[str]:
    """
    Convenience function to create a wiki entry from AI orchestration result.
    Returns the wiki path if successful.
    """
    reporter = AIWikiReporter()
    return reporter.create_ai_report_entry(ai_result)