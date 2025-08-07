"""
Azure DevOps MCP Server
Exposes Azure DevOps operations as MCP tools for AI agents.
"""
import asyncio
import json
from typing import Any, Dict, List, Optional, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolRequest

from devops_gateway.connection import get_connection
from devops_gateway.work_items import _run_wiql, _wit
from utils.settings import settings
from mcp_server.batch_operations import BatchOperations


class AzureDevOpsMCPServer:
    """MCP Server exposing Azure DevOps APIs as tools."""
    
    def __init__(self):
        self.server = Server("azure-devops")
        self.connection = get_connection()
        self.batch_ops = BatchOperations()
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP server handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            return [
                # Work Item Operations
                Tool(
                    name="get_work_items",
                    description="Execute WIQL query to retrieve work items",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "wiql_query": {
                                "type": "string",
                                "description": "WIQL query to execute"
                            },
                            "project": {
                                "type": "string", 
                                "description": "Project name (optional, uses default if not specified)"
                            }
                        },
                        "required": ["wiql_query"]
                    }
                ),
                Tool(
                    name="create_work_item",
                    description="Create a new work item",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "work_item_type": {
                                "type": "string",
                                "description": "Type of work item (Epic, Feature, User Story, Task, Bug)"
                            },
                            "title": {
                                "type": "string",
                                "description": "Work item title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Work item description"
                            },
                            "parent_id": {
                                "type": "integer",
                                "description": "Parent work item ID (optional)"
                            },
                            "project": {
                                "type": "string",
                                "description": "Project name (optional, uses default if not specified)"
                            },
                            "additional_fields": {
                                "type": "object",
                                "description": "Additional fields to set (optional)"
                            }
                        },
                        "required": ["work_item_type", "title"]
                    }
                ),
                Tool(
                    name="update_work_item",
                    description="Update an existing work item",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "work_item_id": {
                                "type": "integer",
                                "description": "Work item ID to update"
                            },
                            "fields": {
                                "type": "object",
                                "description": "Fields to update (e.g., {'System.Title': 'New Title', 'System.State': 'Active'})"
                            },
                            "project": {
                                "type": "string",
                                "description": "Project name (optional)"
                            }
                        },
                        "required": ["work_item_id", "fields"]
                    }
                ),
                # Pull Request Operations
                Tool(
                    name="get_pull_requests",
                    description="Get pull requests from repositories",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {
                                "type": "string",
                                "description": "Project name"
                            },
                            "repository": {
                                "type": "string", 
                                "description": "Repository name (optional, searches all repos if not specified)"
                            },
                            "status": {
                                "type": "string",
                                "description": "PR status: all, active, abandoned, completed (default: all)"
                            },
                            "days_back": {
                                "type": "integer",
                                "description": "Number of days to look back (default: 7)"
                            }
                        },
                        "required": ["project"]
                    }
                ),
                # Project and Repository Operations
                Tool(
                    name="get_projects",
                    description="List all accessible projects",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_repositories",
                    description="List repositories in a project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {
                                "type": "string",
                                "description": "Project name"
                            }
                        },
                        "required": ["project"]
                    }
                ),
                Tool(
                    name="get_readme",
                    description="Get README content from a repository",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {
                                "type": "string",
                                "description": "Project name"
                            },
                            "repository": {
                                "type": "string",
                                "description": "Repository name"
                            },
                            "branch": {
                                "type": "string",
                                "description": "Branch name (default: main)"
                            }
                        },
                        "required": ["project", "repository"]
                    }
                ),
                # Batch Operations for Efficiency
                Tool(
                    name="batch_project_overview",
                    description="Get comprehensive overview of multiple projects efficiently",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "projects": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of project names to analyze"
                            }
                        },
                        "required": ["projects"]
                    }
                ),
                Tool(
                    name="batch_work_item_queries",
                    description="Execute multiple WIQL queries in parallel for efficiency",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "queries": {
                                "type": "object",
                                "description": "Dictionary mapping query names to WIQL strings"
                            }
                        },
                        "required": ["queries"]
                    }
                ),
                Tool(
                    name="batch_pull_requests",
                    description="Get pull requests from multiple repositories efficiently",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_repo_pairs": {
                                "type": "array",
                                "items": {
                                    "type": "object", 
                                    "properties": {
                                        "project": {"type": "string"},
                                        "repository": {"type": "string"}
                                    },
                                    "required": ["project", "repository"]
                                },
                                "description": "List of project/repository pairs"
                            },
                            "days_back": {
                                "type": "integer",
                                "description": "Number of days to look back (default: 7)"
                            }
                        },
                        "required": ["project_repo_pairs"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
            """Handle tool calls."""
            return await self._handle_tool_call(name, arguments)
    
    async def _handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Handle tool calls and return results."""
        try:
            # Work Item Operations
            if name == "get_work_items":
                result = await self._get_work_items(**arguments)
            elif name == "create_work_item":
                result = await self._create_work_item(**arguments)
            elif name == "update_work_item":
                result = await self._update_work_item(**arguments)
            # Pull Request Operations
            elif name == "get_pull_requests":
                result = await self._get_pull_requests(**arguments)
            # Project Operations
            elif name == "get_projects":
                result = await self._get_projects(**arguments)
            elif name == "get_repositories":
                result = await self._get_repositories(**arguments)
            elif name == "get_readme":
                result = await self._get_readme(**arguments)
            # Batch Operations
            elif name == "batch_project_overview":
                result = await self._batch_project_overview(**arguments)
            elif name == "batch_work_item_queries":
                result = await self._batch_work_item_queries(**arguments)
            elif name == "batch_pull_requests":
                result = await self._batch_pull_requests(**arguments)
            else:
                result = {"error": f"Unknown tool: {name}"}
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {"error": str(e), "tool": name, "arguments": arguments}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
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
            
            # Try different README file names
            readme_files = ["README.md", "readme.md", "README.txt", "readme.txt", "README"]
            readme_content = None
            readme_file = None
            
            for filename in readme_files:
                try:
                    # Get file content
                    item = git_client.get_item(
                        repository_id=repository,
                        path=filename,
                        project=project,
                        version_descriptor_version_type="branch",
                        version_descriptor_version=branch
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
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)


async def main():
    """Main entry point for the MCP server."""
    server = AzureDevOpsMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())