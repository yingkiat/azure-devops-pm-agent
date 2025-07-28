"""
Business intelligence executor - processes PM requests and queries Azure DevOps.
Reads instructions from PM-Agent page and executes data gathering requests.
"""
from __future__ import annotations
from typing import Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from .page_reader import PMAgentConfig, BusinessRequest
from .request_classifier import BusinessRequestClassifier
from .id_mapping import get_id_mapping_manager, create_display_id
from devops_gateway.connection import get_connection
from devops_gateway.work_items import _run_wiql
from agent.wiki_interface import WikiInterface
from utils.settings import settings
from rich import print as rprint


@dataclass
class PRInfo:
    """Pull request information."""
    id: int
    title: str
    status: str
    created_by: str
    created_date: str
    target_branch: str
    project: str
    url: str


@dataclass 
class IssueInfo:
    """Issue/Work item information."""
    id: int
    title: str
    type: str
    state: str
    priority: str
    assigned_to: str
    created_date: str
    project: str


class BusinessIntelExecutor:
    """Executes business intelligence requests from PM-Agent page."""
    
    def __init__(self):
        self.connection = get_connection()
        self.classifier = BusinessRequestClassifier()
        self.id_manager = get_id_mapping_manager()
    
    def get_prs_from_projects(self, projects: List[str], days_back: int = 7) -> List[PRInfo]:
        """Get pull requests from specified projects."""
        prs = []
        
        try:
            git_client = self.connection.clients.get_git_client()
            
            for project in projects:
                try:
                    # Get repositories for the project
                    repos = git_client.get_repositories(project=project)
                    
                    for repo in repos:
                        # Handle both dict and object repository formats
                        repo_id = repo.id if hasattr(repo, 'id') else repo['id']
                        repo_name = repo.name if hasattr(repo, 'name') else repo['name']
                        
                        # Use direct REST API call to avoid SDK issues with status parameter
                        import requests
                        from requests.auth import HTTPBasicAuth
                        
                        api_url = f"{settings.azdo_org_url}/{project}/_apis/git/repositories/{repo_id}/pullrequests"
                        params = {
                            'api-version': '7.1',
                            'searchCriteria.status': 'all',
                            '$top': 100
                        }
                        headers = {'Accept': 'application/json'}
                        auth = HTTPBasicAuth('', settings.azdo_pat)
                        
                        response = requests.get(api_url, params=params, auth=auth, headers=headers)
                        
                        if response.status_code == 200:
                            pr_data = response.json()
                            repo_prs = pr_data.get('value', [])
                        else:
                            print(f"⚠️  REST API failed for {repo_name}: {response.status_code}")
                            repo_prs = []
                        
                        print(f"🔧 Found {len(repo_prs)} PRs in repo {repo_name} (project: {project})")
                        
                        from datetime import timezone
                        cutoff_date = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=days_back)
                        print(f"🔧 Cutoff date: {cutoff_date} (looking back {days_back} days)")
                        
                        for pr in repo_prs:
                            # Handle raw JSON response instead of SDK objects
                            pr_id = pr.get('pullRequestId')
                            pr_title = pr.get('title', 'No title')
                            pr_status = pr.get('status', 'unknown')
                            pr_created = pr.get('creationDate', '')
                            pr_created_by = pr.get('createdBy', {}).get('displayName', 'Unknown')
                            pr_target_ref = pr.get('targetRefName', 'refs/heads/main')
                            
                            pr_date = datetime.fromisoformat(pr_created.replace('Z', '+00:00'))
                            print(f"🔧 PR #{pr_id}: {pr_title[:50]}... created {pr_created} (status: {pr_status})")
                            
                            if pr_date >= cutoff_date:
                                # Create ID mapping for this PR
                                local_id = create_display_id(pr_id, 'pull_request', pr_title, project)
                                
                                prs.append(PRInfo(
                                    id=pr_id,
                                    title=pr_title,
                                    status=pr_status,
                                    created_by=pr_created_by,
                                    created_date=pr_created[:10],
                                    target_branch=pr_target_ref.replace('refs/heads/', ''),
                                    project=project,
                                    url=f"{settings.azdo_org_url}/{project}/_git/{repo_name}/pullrequest/{pr_id}"
                                ))
                                
                except Exception as e:
                    rprint(f"⚠️  Could not get PRs from {project}: {e}")
                    
        except Exception as e:
            rprint(f"❌ Failed to get PRs: {e}")
            
        return prs
    
    def get_issues_from_projects(self, projects: List[str], priority_filter: str = None) -> List[IssueInfo]:
        """Get issues/work items from specified projects."""
        issues = []
        
        try:
            for project in projects:
                # Build WIQL query
                query_parts = [
                    "SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State],",
                    "[Microsoft.VSTS.Common.Priority], [System.AssignedTo], [System.CreatedDate]",
                    "FROM WorkItems",
                    f"WHERE [System.TeamProject] = '{project}'"
                ]
                
                if priority_filter:
                    if priority_filter.lower() == 'critical':
                        query_parts.append("AND ([Microsoft.VSTS.Common.Priority] = 1 OR [Microsoft.VSTS.Common.Priority] = 2)")
                    elif priority_filter.lower() == 'high':
                        query_parts.append("AND [Microsoft.VSTS.Common.Priority] = 2")
                
                query_parts.append("AND [System.State] <> 'Closed' AND [System.State] <> 'Done'")
                query_parts.append("ORDER BY [Microsoft.VSTS.Common.Priority], [System.CreatedDate] DESC")
                
                query = " ".join(query_parts)
                
                try:
                    results = _run_wiql(query.replace(f"'{project}'", f"'{project}'"))
                    
                    for item in results:
                        fields = item.get('fields', {})
                        wi_title = fields.get('System.Title', 'No title')
                        wi_id = item['id']
                        
                        # Create ID mapping for this work item
                        local_id = create_display_id(wi_id, 'work_item', wi_title, project)
                        
                        issues.append(IssueInfo(
                            id=wi_id,
                            title=wi_title,
                            type=fields.get('System.WorkItemType', 'Unknown'),
                            state=fields.get('System.State', 'Unknown'),
                            priority=str(fields.get('Microsoft.VSTS.Common.Priority', 'None')),
                            assigned_to=fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
                            created_date=fields.get('System.CreatedDate', '')[:10] if fields.get('System.CreatedDate') else '',
                            project=project
                        ))
                        
                except Exception as e:
                    rprint(f"⚠️  Could not get issues from {project}: {e}")
                    
        except Exception as e:
            rprint(f"❌ Failed to get issues: {e}")
            
        return issues
    
    def execute_request(self, request: BusinessRequest, config: PMAgentConfig) -> Dict[str, Any]:
        """Execute a single business request using LLM-based classification."""
        result = {
            "request_id": request.id,
            "title": request.title,
            "status": "completed",
            "data": {},
            "summary": ""
        }
        
        # Determine which projects to query
        projects = request.projects if request.projects else config.projects_to_monitor
        
        try:
            # Use LLM-based classifier instead of hardcoded text matching
            classified = self.classifier.classify_request(request, projects)
            
            print(f"🤖 '{request.title}' classified as: {classified.request_type}")
            print(f"💭 Reasoning: {classified.reasoning}")
            print(f"🎯 Confidence: {classified.confidence:.2f}")
            print(f"📅 Time range: {classified.time_range_days} days")
            print(f"🔍 Request text: '{request.title} {request.description}'")
            
            if classified.request_type == "pull_requests":
                # Handle PR requests
                prs = self.get_prs_from_projects(projects, classified.time_range_days)
                result["data"]["prs"] = [
                    {
                        "id": pr.id,
                        "local_id": create_display_id(pr.id, 'pull_request', pr.title, pr.project),
                        "title": pr.title,
                        "status": pr.status,
                        "created_by": pr.created_by,
                        "created_date": pr.created_date,
                        "project": pr.project,
                        "url": pr.url
                    }
                    for pr in prs
                ]
                result["summary"] = f"Found {len(prs)} pull requests across {len(projects)} projects"
                
            elif classified.request_type == "work_items":
                # Handle work item/issue requests
                priority_filter = classified.filters.get("priority")
                if priority_filter == "all":
                    priority_filter = None
                    
                issues = self.get_issues_from_projects(projects, priority_filter)
                result["data"]["issues"] = [
                    {
                        "id": issue.id,
                        "local_id": create_display_id(issue.id, 'work_item', issue.title, issue.project),
                        "title": issue.title,
                        "type": issue.type,
                        "state": issue.state,
                        "priority": issue.priority,
                        "assigned_to": issue.assigned_to,
                        "project": issue.project
                    }
                    for issue in issues
                ]
                result["summary"] = f"Found {len(issues)} work items across {len(projects)} projects"
                
            elif classified.request_type == "sprint_progress":
                # Handle sprint/progress requests
                issues = self.get_issues_from_projects(projects, priority_filter=None)
                
                # Group by state for progress reporting
                state_counts = {}
                for issue in issues:
                    state = issue.state
                    state_counts[state] = state_counts.get(state, 0) + 1
                
                result["data"]["sprint_progress"] = {
                    "total_items": len(issues),
                    "state_breakdown": state_counts,
                    "items": [
                        {
                            "id": issue.id,
                            "local_id": create_display_id(issue.id, 'work_item', issue.title, issue.project),
                            "title": issue.title,
                            "type": issue.type,
                            "state": issue.state,
                            "assigned_to": issue.assigned_to,
                            "project": issue.project
                        }
                        for issue in issues[:20]  # Show top 20 items
                    ]
                }
                result["summary"] = f"Found {len(issues)} work items. States: {', '.join([f'{k}: {v}' for k, v in state_counts.items()])}"
                
            else:
                result["status"] = "skipped"
                result["summary"] = f"Unsupported request type: {classified.request_type}"
                
        except Exception as e:
            result["status"] = "failed"
            result["summary"] = f"Error: {e}"
            
        return result
    
    def create_business_report(self, config: PMAgentConfig, results: List[Dict[str, Any]]) -> str:
        """Create a comprehensive business intelligence report."""
        current_time = datetime.utcnow()
        
        content = [
            f"# Business Intelligence Report",
            f"*Generated on {current_time.strftime('%B %d, %Y at %H:%M UTC')}*",
            "",
            "## Overview",
            "",
            f"📊 **Projects Monitored:** {', '.join(config.projects_to_monitor)}",
            f"📅 **PM-Agent Config Last Updated:** {config.last_updated}",
            f"🎯 **Requests Processed:** {len([r for r in results if r['status'] == 'completed'])}/{len(results)}",
            "",
        ]
        
        # Add business context if available
        if config.context and config.context.strip():
            context_preview = config.context.strip()[:200]
            if len(config.context) > 200:
                context_preview += "..."
            content.extend([
                "## Business Context",
                "",
                context_preview,
                "",
            ])
        
        # Add key metrics summary
        pr_count = sum(len(r.get("data", {}).get("prs", [])) for r in results)
        work_item_count = sum(len(r.get("data", {}).get("issues", [])) for r in results)
        sprint_items = sum(r.get("data", {}).get("sprint_progress", {}).get("total_items", 0) for r in results)
        
        content.extend([
            "## Key Metrics",
            "",
            f"🔄 **Pull Requests Found:** {pr_count}",
            f"🔴 **Work Items Found:** {work_item_count}",
            f"📈 **Sprint Items Tracked:** {sprint_items}",
            "",
        ])
        
        # Request results
        content.extend([
            "## Detailed Results",
            ""
        ])
        
        for i, result in enumerate(results, 1):
            status_icon = "✅" if result["status"] == "completed" else "❌" if result["status"] == "failed" else "⏭️"
            
            content.extend([
                f"### {i}. {status_icon} {result['title']}",
                f"**Status:** {result['status'].title()} | **Summary:** {result['summary']}",
                ""
            ])
            
            # Show data if available
            if result["status"] == "completed" and result["data"]:
                if "prs" in result["data"]:
                    prs = result["data"]["prs"]
                    if prs:
                        # Add PR summary
                        completed_prs = len([pr for pr in prs if pr['status'] == 'completed'])
                        active_prs = len([pr for pr in prs if pr['status'] == 'active'])
                        
                        content.extend([
                            f"📋 **Pull Requests Summary:** {completed_prs} completed, {active_prs} active",
                            "",
                            "| ID | Title | Status | Author | Project | Created |",
                            "| --- | --- | --- | --- | --- | --- |"
                        ])
                        
                        for pr in prs[:10]:  # Show top 10
                            status_badge = "🟢" if pr['status'] == 'completed' else "🟡" if pr['status'] == 'active' else "🔴"
                            # Show Azure DevOps ID for user recognition (what they see in DevOps UI)
                            content.append(f"| PR-{pr['id']} | {pr['title'][:45]}... | {status_badge} {pr['status']} | {pr['created_by']} | {pr['project']} | {pr['created_date']} |")
                        
                        if len(prs) > 10:
                            content.append(f"| ... | *and {len(prs) - 10} more PRs* | ... | ... | ... | ... |")
                        content.append("")
                
                if "issues" in result["data"]:
                    issues = result["data"]["issues"]
                    if issues:
                        # Group by priority and state
                        high_priority = len([i for i in issues if i['priority'] in ['1', '2']])
                        open_items = len([i for i in issues if i['state'] not in ['Closed', 'Done', 'Resolved']])
                        
                        content.extend([
                            f"🔴 **Work Items Summary:** {high_priority} high priority, {open_items} open items",
                            "",
                            "| ID | Title | Type | State | Priority | Assigned | Project |",
                            "| --- | --- | --- | --- | --- | --- | --- |"
                        ])
                        
                        for issue in issues[:10]:  # Show top 10
                            priority_icon = "🔴" if issue['priority'] in ['1', '2'] else "🟡" if issue['priority'] == '3' else "🟢"
                            state_icon = "🟢" if issue['state'] in ['Done', 'Closed'] else "🟡" if issue['state'] == 'Active' else "⚪"
                            # Show Azure DevOps ID for user recognition (what they see in DevOps UI)
                            content.append(f"| WI-{issue['id']} | {issue['title'][:35]}... | {issue['type']} | {state_icon} {issue['state']} | {priority_icon} P{issue['priority']} | {issue['assigned_to']} | {issue['project']} |")
                        
                        if len(issues) > 10:
                            content.append(f"| ... | *and {len(issues) - 10} more items* | ... | ... | ... | ... | ... |")
                        content.append("")
                    else:
                        content.extend([
                            "🟢 **No critical issues found** - All clear!",
                            ""
                        ])
                
                if "sprint_progress" in result["data"]:
                    sprint_data = result["data"]["sprint_progress"]
                    
                    # Calculate progress metrics
                    total = sprint_data['total_items']
                    state_breakdown = sprint_data.get('state_breakdown', {})
                    completed = state_breakdown.get('Done', 0) + state_breakdown.get('Closed', 0)
                    in_progress = state_breakdown.get('Active', 0) + state_breakdown.get('In Progress', 0)
                    remaining = total - completed - in_progress
                    
                    progress_pct = (completed / total * 100) if total > 0 else 0
                    
                    content.extend([
                        f"📈 **Sprint Progress Overview:** {progress_pct:.1f}% Complete",
                        "",
                        f"✅ **Completed:** {completed} items",
                        f"🟡 **In Progress:** {in_progress} items", 
                        f"⚪ **Remaining:** {remaining} items",
                        f"📊 **Total:** {total} items",
                        ""
                    ])
                    
                    # Show work items table
                    items = sprint_data.get('items', [])
                    if items:
                        content.extend([
                            "**Current Work Items:**",
                            "",
                            "| ID | Title | Type | State | Assigned | Project |",
                            "| --- | --- | --- | --- | --- | --- |"
                        ])
                        
                        for item in items:
                            state_icon = "✅" if item['state'] in ['Done', 'Closed'] else "🟡" if item['state'] in ['Active', 'In Progress'] else "⚪"
                            # Show Azure DevOps ID for user recognition (what they see in DevOps UI)
                            content.append(f"| WI-{item['id']} | {item['title'][:35]}... | {item['type']} | {state_icon} {item['state']} | {item['assigned_to']} | {item['project']} |")
                        
                        if sprint_data['total_items'] > len(items):
                            content.append(f"| ... | *and {sprint_data['total_items'] - len(items)} more items* | ... | ... | ... | ... |")
                        content.append("")
        
        # Generate actionable next steps based on findings
        content.extend([
            "## Recommended Actions",
            ""
        ])
        
        # Smart recommendations based on data
        recommendations = []
        
        if pr_count > 0:
            completed_prs = sum(len([pr for pr in r.get("data", {}).get("prs", []) if pr['status'] == 'completed']) for r in results)
            if completed_prs == pr_count:
                recommendations.append("✅ All pull requests are completed - consider deploying to production")
            else:
                recommendations.append("🔄 Review and merge pending pull requests to maintain development velocity")
        
        if work_item_count == 0 and any("critical" in r.get("title", "").lower() for r in results):
            recommendations.append("🟢 No critical issues found - system appears stable")
        elif work_item_count > 5:
            recommendations.append("🔴 High number of work items found - consider triaging and prioritizing")
        
        if sprint_items > 0:
            for result in results:
                if "sprint_progress" in result.get("data", {}):
                    sprint_data = result["data"]["sprint_progress"]
                    total = sprint_data['total_items']
                    state_breakdown = sprint_data.get('state_breakdown', {})
                    new_items = state_breakdown.get('New', 0)
                    if new_items > total * 0.5:
                        recommendations.append("📋 Many items are still in 'New' state - consider starting work or assigning owners")
        
        if not recommendations:
            recommendations.append("📊 Continue monitoring project health and update PM-Agent page with new requests as needed")
        
        for i, rec in enumerate(recommendations, 1):
            content.append(f"{i}. {rec}")
        
        content.extend([
            "",
            "## How to Update",
            "",
            "• **Add new requests:** Edit the [PM-Agent page](/PM-Agent) and run `execute-requests`",
            "• **Change monitoring:** Update the projects list in your PM-Agent configuration", 
            "• **Adjust timeframes:** Modify request descriptions (e.g., 'last 2 weeks' instead of 'last week')",
            "",
            "---",
            f"*🤖 Report generated by PM-Agent on {current_time.strftime('%B %d, %Y at %H:%M UTC')} | Next update: Edit PM-Agent page and re-run*"
        ])
        
        return "\n".join(content)


def execute_business_requests(config: PMAgentConfig) -> None:
    """Execute all business requests from PM-Agent configuration."""
    executor = BusinessIntelExecutor()
    results = []
    
    rprint(f"📊 Processing {len(config.business_requests)} requests...")
    
    for request in config.business_requests:
        rprint(f"⚡ Executing: {request.title}")
        result = executor.execute_request(request, config)
        results.append(result)
        
        status_icon = "✅" if result["status"] == "completed" else "❌"
        rprint(f"   {status_icon} {result['summary']}")
    
    # Create comprehensive report
    rprint("📝 Generating business intelligence report...")
    report_content = executor.create_business_report(config, results)
    
    # Save as interaction transcript
    session_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S-BI")
    
    # Save structured BI data to outputs folder
    from pathlib import Path
    import json
    
    bi_data = {
        "bi_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "business_goal": f"Business Intelligence Report - {len(config.business_requests)} requests",
        "config": {
            "projects_to_monitor": config.projects_to_monitor,
            "requests_count": len(config.business_requests),
            "context": config.context
        },
        "results": results,
        "report_content": report_content,
        "summary": {
            "total_requests": len(config.business_requests),
            "completed_requests": len([r for r in results if r["status"] == "completed"]),
            "failed_requests": len([r for r in results if r["status"] == "failed"]),
            "total_prs": sum(len(r.get("data", {}).get("prs", [])) for r in results),
            "total_work_items": sum(len(r.get("data", {}).get("issues", [])) for r in results),
            "total_sprint_items": sum(r.get("data", {}).get("sprint_progress", {}).get("total_items", 0) for r in results)
        }
    }
    
    # Save BI data as JSON
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)
    bi_file_path = outputs_dir / f"BI-{session_id}.json"
    
    with open(bi_file_path, 'w') as f:
        json.dump(bi_data, f, indent=2)
    
    rprint(f"💾 [blue]BI data saved:[/blue] {bi_file_path}")
    
    interface = WikiInterface()
    interaction_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "business_goal": f"Business Intelligence Report - {len(config.business_requests)} requests",
        "user": "Business PM",
        "report_content": report_content,
        "config": {
            "projects": config.projects_to_monitor,
            "requests_count": len(config.business_requests),
            "context": config.context
        }
    }
    
    # Create custom BI report transcript
    page_path = f"{interface.interactions_path}/{session_id}"
    
    try:
        from devops_gateway.wiki import push_markdown_to_azure_wiki
        success = push_markdown_to_azure_wiki(report_content, page_path)
        if success:
            rprint(f"✅ [green]Business intelligence report created:[/green] /PM-Agent/Interactions/{session_id}")
        else:
            rprint(f"⚠️  [yellow]Report generated but wiki update failed[/yellow]")
    except Exception as e:
        rprint(f"❌ [red]Failed to save report: {e}[/red]")
    
    rprint("🎉 [green]Business intelligence analysis complete![/green]")