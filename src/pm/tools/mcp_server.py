"""
Azure DevOps MCP Server with EA and PM Extensions
Exposes Azure DevOps, EA discovery, and PM business intelligence as MCP tools.
"""
import asyncio
import json
from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp.types import Tool, TextContent

from devops_gateway.connection import get_connection
from devops_gateway.work_items import _run_wiql, _wit
from utils.settings import settings

# Handle both relative and direct imports
try:
    from .batch_operations import BatchOperations
except ImportError:
    from batch_operations import BatchOperations


# Initialize FastMCP server
mcp = FastMCP("azure-devops-pm-ea")

class AzureDevOpsMCPServer:
    """MCP Server exposing Azure DevOps APIs as tools."""

    def __init__(self):
        self._connection = None  # Lazy-loaded on first use
        self._batch_ops = None   # Lazy-loaded on first use
        self._register_tools()

    @property
    def connection(self):
        """Lazy-load Azure DevOps connection only when needed."""
        if self._connection is None:
            self._connection = get_connection()
        return self._connection

    @property
    def batch_ops(self):
        """Lazy-load BatchOperations only when needed."""
        if self._batch_ops is None:
            self._batch_ops = BatchOperations()
        return self._batch_ops

    def get_available_tools(self) -> List[str]:
        """Dynamically get list of all MCP tools."""
        return [
            # Azure DevOps work item operations
            "get_work_items",
            "create_work_item",
            "update_work_item",
            "get_pull_requests",
            "get_projects",
            "get_repositories",
            "get_readme",
            "batch_project_overview",
            "batch_work_item_queries",
            "batch_pull_requests",
            # EA (Enterprise Architecture) tools
            "ea_discover",
            "ea_generate_archi",
            "ea_generate_mermaid",
            # PM (Project Management) tools
            "classify_pm_request",
            "execute_business_intel"
        ]
    
    def _register_tools(self):
        """Register MCP tools."""

        @mcp.tool()
        async def get_work_items(wiql_query: str, project: str = None) -> str:
            """Execute WIQL query to retrieve work items."""
            result = await self._get_work_items(wiql_query, project)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def create_work_item(work_item_type: str, title: str, description: str = "",
                                  parent_id: int = None, project: str = None,
                                  additional_fields: dict = None) -> str:
            """Create a new work item."""
            result = await self._create_work_item(work_item_type, title, description,
                                                 parent_id, project, additional_fields)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def update_work_item(work_item_id: int, fields: dict, project: str = None) -> str:
            """Update an existing work item."""
            result = await self._update_work_item(work_item_id, fields, project)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def get_pull_requests(project: str, repository: str = None,
                                   status: str = "all", days_back: int = 7) -> str:
            """Get pull requests from repositories."""
            result = await self._get_pull_requests(project, repository, status, days_back)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def get_projects() -> str:
            """List all accessible projects."""
            result = await self._get_projects()
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def get_repositories(project: str) -> str:
            """List repositories in a project."""
            result = await self._get_repositories(project)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def get_readme(project: str, repository: str, branch: str = "main") -> str:
            """Get README content from a repository."""
            result = await self._get_readme(project, repository, branch)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def batch_project_overview(projects: list) -> str:
            """Get comprehensive overview of multiple projects efficiently."""
            result = await self._batch_project_overview(projects)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def batch_work_item_queries(queries: dict) -> str:
            """Execute multiple WIQL queries in parallel for efficiency."""
            result = await self._batch_work_item_queries(queries)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def batch_pull_requests(project_repo_pairs: list, days_back: int = 7) -> str:
            """Get pull requests from multiple repositories efficiently."""
            result = await self._batch_pull_requests(project_repo_pairs, days_back)
            return json.dumps(result, indent=2)

        # Store methods on the mcp instance for tool access
        mcp._server_instance = self
    
    async def _get_work_items(self, wiql_query: str, project: str = None) -> Dict[str, Any]:
        """Execute WIQL query and return work items."""
        try:
            # Use existing _run_wiql function
            work_items = _run_wiql(wiql_query)
            
            return {
                "success": True,
                "count": len(work_items),
                "work_items": work_items,
                "query": wiql_query,
                "project": project or settings.azdo_project
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": wiql_query
            }
    
    async def _create_work_item(self, work_item_type: str, title: str, 
                               description: str = "", parent_id: int = None,
                               project: str = None, additional_fields: Dict = None) -> Dict[str, Any]:
        """Create a new work item."""
        try:
            from devops_gateway.work_items import create_work_item
            
            # Create the work item
            work_item = create_work_item(work_item_type, title, description, parent_id)
            
            # Apply additional fields if provided
            if additional_fields:
                from azure.devops.v7_0.work_item_tracking.models import JsonPatchOperation
                wit = _wit()
                updates = []
                
                for field_name, field_value in additional_fields.items():
                    updates.append(JsonPatchOperation(
                        op="add", 
                        path=f"/fields/{field_name}", 
                        value=field_value
                    ))
                
                if updates:
                    work_item = wit.update_work_item(document=updates, id=work_item["id"])
            
            return {
                "success": True,
                "work_item": {
                    "id": work_item["id"],
                    "title": title,
                    "type": work_item_type,
                    "url": f"{settings.azdo_org_url}/{project or settings.azdo_project}/_workitems/edit/{work_item['id']}"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "attempted": {
                    "type": work_item_type,
                    "title": title
                }
            }
    
    async def _update_work_item(self, work_item_id: int, fields: Dict[str, Any], project: str = None) -> Dict[str, Any]:
        """Update an existing work item."""
        try:
            from azure.devops.v7_0.work_item_tracking.models import JsonPatchOperation
            wit = _wit()
            
            # Build update operations
            updates = []
            for field_name, field_value in fields.items():
                updates.append(JsonPatchOperation(
                    op="replace", 
                    path=f"/fields/{field_name}", 
                    value=field_value
                ))
            
            # Apply updates
            work_item = wit.update_work_item(document=updates, id=work_item_id)
            
            return {
                "success": True,
                "work_item": {
                    "id": work_item_id,
                    "updated_fields": fields,
                    "url": f"{settings.azdo_org_url}/{project or settings.azdo_project}/_workitems/edit/{work_item_id}"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "work_item_id": work_item_id
            }
    
    async def _get_pull_requests(self, project: str, repository: str = None, 
                                status: str = "all", days_back: int = 7) -> Dict[str, Any]:
        """Get pull requests from repositories."""
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            from datetime import datetime, timedelta, timezone
            
            git_client = self.connection.clients.get_git_client()
            prs = []
            
            # Get repositories
            if repository:
                # Get specific repository
                repo = git_client.get_repository(repository_id=repository, project=project)
                repos = [repo]
            else:
                # Get all repositories in project
                repos = git_client.get_repositories(project=project)
            
            cutoff_date = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=days_back)
            
            for repo in repos:
                repo_id = repo.id if hasattr(repo, 'id') else repo['id']
                repo_name = repo.name if hasattr(repo, 'name') else repo['name']
                
                # Use REST API for better status filtering
                api_url = f"{settings.azdo_org_url}/{project}/_apis/git/repositories/{repo_id}/pullrequests"
                params = {
                    'api-version': '7.1',
                    'searchCriteria.status': status,
                    '$top': 100
                }
                headers = {'Accept': 'application/json'}
                auth = HTTPBasicAuth('', settings.azdo_pat)
                
                response = requests.get(api_url, params=params, auth=auth, headers=headers)
                
                if response.status_code == 200:
                    pr_data = response.json()
                    repo_prs = pr_data.get('value', [])
                    
                    for pr in repo_prs:
                        pr_created = pr.get('creationDate', '')
                        pr_date = datetime.fromisoformat(pr_created.replace('Z', '+00:00'))
                        
                        if pr_date >= cutoff_date:
                            prs.append({
                                "id": pr.get('pullRequestId'),
                                "title": pr.get('title', 'No title'),
                                "status": pr.get('status', 'unknown'),
                                "created_by": pr.get('createdBy', {}).get('displayName', 'Unknown'),
                                "created_date": pr_created[:10],
                                "target_branch": pr.get('targetRefName', 'refs/heads/main').replace('refs/heads/', ''),
                                "source_branch": pr.get('sourceRefName', '').replace('refs/heads/', ''),
                                "project": project,
                                "repository": repo_name,
                                "url": f"{settings.azdo_org_url}/{project}/_git/{repo_name}/pullrequest/{pr.get('pullRequestId')}"
                            })
            
            return {
                "success": True,
                "count": len(prs),
                "pull_requests": prs,
                "filters": {
                    "project": project,
                    "repository": repository,
                    "status": status,
                    "days_back": days_back
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "filters": {
                    "project": project,
                    "repository": repository
                }
            }
    
    async def _get_projects(self) -> Dict[str, Any]:
        """List all accessible projects."""
        try:
            core_client = self.connection.clients.get_core_client()
            projects = core_client.get_projects()
            
            project_list = []
            for project in projects:
                project_list.append({
                    "id": project.id,
                    "name": project.name,
                    "description": project.description or "",
                    "state": project.state,
                    "url": f"{settings.azdo_org_url}/{project.name}"
                })
            
            return {
                "success": True,
                "count": len(project_list),
                "projects": project_list
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_repositories(self, project: str) -> Dict[str, Any]:
        """List repositories in a project."""
        try:
            git_client = self.connection.clients.get_git_client()
            repos = git_client.get_repositories(project=project)
            
            repo_list = []
            for repo in repos:
                repo_list.append({
                    "id": repo.id,
                    "name": repo.name,
                    "url": repo.remote_url,
                    "default_branch": repo.default_branch,
                    "size": repo.size,
                    "project": project
                })
            
            return {
                "success": True,
                "count": len(repo_list),
                "repositories": repo_list,
                "project": project
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project": project
            }
    
    async def _get_readme(self, project: str, repository: str, branch: str = "main") -> Dict[str, Any]:
        """Get README content from a repository."""
        try:
            git_client = self.connection.clients.get_git_client()
            
            # First, get the repository ID if we were passed a name
            repo_id = repository
            try:
                repos = git_client.get_repositories(project=project)
                for repo in repos:
                    if repo.name == repository:
                        repo_id = repo.id
                        break
            except Exception:
                # If that fails, assume repository parameter is already an ID
                pass
            
            # Try different README file names
            readme_files = ["README.md", "readme.md", "README.txt", "readme.txt", "README"]
            readme_content = None
            readme_file = None
            
            for filename in readme_files:
                try:
                    # Get file content using repository ID
                    item = git_client.get_item(
                        repository_id=repo_id,
                        path=filename,
                        project=project,
                        include_content=True
                    )
                    
                    if item and hasattr(item, 'content'):
                        readme_content = item.content
                        readme_file = filename
                        break
                        
                except Exception:
                    continue  # Try next filename
            
            if readme_content:
                return {
                    "success": True,
                    "content": readme_content,
                    "filename": readme_file,
                    "project": project,
                    "repository": repository,
                    "branch": branch
                }
            else:
                return {
                    "success": False,
                    "error": "README file not found",
                    "tried_files": readme_files,
                    "project": project,
                    "repository": repository
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project": project,
                "repository": repository
            }
    
    async def _batch_project_overview(self, projects: List[str]) -> Dict[str, Any]:
        """Get comprehensive overview of multiple projects efficiently."""
        try:
            result = await self.batch_ops.batch_project_overview(projects)
            return {
                "success": result.success,
                "projects_analyzed": len(projects),
                "execution_time": result.execution_time,
                "project_overviews": result.results,
                "errors": result.errors
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "projects_requested": projects
            }
    
    async def _batch_work_item_queries(self, queries: Dict[str, str]) -> Dict[str, Any]:
        """Execute multiple WIQL queries in parallel for efficiency."""
        try:
            result = await self.batch_ops.batch_work_item_queries(queries)
            return {
                "success": result.success,
                "queries_executed": len(queries),
                "execution_time": result.execution_time,
                "query_results": result.results,
                "errors": result.errors
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "queries_requested": list(queries.keys())
            }
    
    async def _batch_pull_requests(self, project_repo_pairs: List[Dict[str, str]], days_back: int = 7) -> Dict[str, Any]:
        """Get pull requests from multiple repositories efficiently."""
        try:
            # Convert to list of tuples for batch operations
            pairs = [(pair["project"], pair["repository"]) for pair in project_repo_pairs]
            
            result = await self.batch_ops.batch_pull_requests(pairs, days_back)
            return {
                "success": result.success,
                "repositories_queried": len(pairs),
                "execution_time": result.execution_time,
                "pull_request_results": result.results,
                "errors": result.errors,
                "days_back": days_back
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_repo_pairs": project_repo_pairs
            }
    
def main():
    """Main entry point for the MCP server."""
    # Initialize the server instance to register tools
    server = AzureDevOpsMCPServer()

    # Run the FastMCP server (this is synchronous)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()