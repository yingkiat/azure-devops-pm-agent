"""
Batch operations for efficient Azure DevOps API usage.
Combines multiple related operations to reduce API calls and improve performance.
"""
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from devops_gateway.connection import get_connection
from devops_gateway.work_items import _run_wiql
from utils.settings import settings
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, timezone


@dataclass
class BatchResult:
    """Result from a batch operation."""
    success: bool
    results: Dict[str, Any]
    errors: List[str]
    execution_time: float


class BatchOperations:
    """Performs efficient batch operations on Azure DevOps."""
    
    def __init__(self):
        self.connection = get_connection()
        self.executor = ThreadPoolExecutor(max_workers=5)  # Limit concurrent API calls
    
    async def batch_project_overview(self, projects: List[str]) -> BatchResult:
        """
        Get comprehensive overview of multiple projects in parallel.
        Returns work items, repositories, and recent activity for each project.
        """
        start_time = datetime.utcnow()
        results = {}
        errors = []
        
        try:
            # Create tasks for parallel execution
            tasks = []
            for project in projects:
                tasks.append(self._get_project_overview(project))
            
            # Execute in parallel
            project_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(project_results):
                project = projects[i]
                if isinstance(result, Exception):
                    errors.append(f"Project {project}: {str(result)}")
                    results[project] = {"error": str(result)}
                else:
                    results[project] = result
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return BatchResult(
                success=len(errors) == 0,
                results=results,
                errors=errors,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return BatchResult(
                success=False,
                results={},
                errors=[str(e)],
                execution_time=execution_time
            )
    
    async def _get_project_overview(self, project: str) -> Dict[str, Any]:
        """Get overview data for a single project."""
        overview = {"project": project}
        
        try:
            # Get work items summary - use simpler query without GROUP BY for compatibility
            summary_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
            ORDER BY [System.ChangedDate] DESC
            """
            
            work_items_summary = _run_wiql(summary_query)
            overview["work_items_summary"] = work_items_summary
            
            # Get repositories
            git_client = self.connection.clients.get_git_client()
            repos = git_client.get_repositories(project=project)
            overview["repositories"] = [
                {
                    "name": repo.name,
                    "id": repo.id,
                    "default_branch": repo.default_branch
                }
                for repo in repos
            ]
            
            # Get recent work items (last 7 days)
            recent_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.CreatedDate]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
              AND [System.CreatedDate] >= @Today - 7
            ORDER BY [System.CreatedDate] DESC
            """
            
            recent_items = _run_wiql(recent_query)
            overview["recent_work_items"] = recent_items[:10]  # Limit to 10 most recent
            
            return overview
            
        except Exception as e:
            raise Exception(f"Failed to get overview for {project}: {e}")
    
    async def batch_pull_requests(self, project_repo_pairs: List[Tuple[str, str]], 
                                 days_back: int = 7) -> BatchResult:
        """
        Get pull requests from multiple project/repository combinations efficiently.
        """
        start_time = datetime.utcnow()
        results = {}
        errors = []
        
        try:
            # Create tasks for parallel PR fetching
            tasks = []
            for project, repo in project_repo_pairs:
                tasks.append(self._get_prs_for_repo(project, repo, days_back))
            
            # Execute in parallel
            pr_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(pr_results):
                project, repo = project_repo_pairs[i]
                key = f"{project}/{repo}"
                
                if isinstance(result, Exception):
                    errors.append(f"{key}: {str(result)}")
                    results[key] = {"error": str(result)}
                else:
                    results[key] = result
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return BatchResult(
                success=len(errors) == 0,
                results=results,
                errors=errors,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return BatchResult(
                success=False,
                results={},
                errors=[str(e)],
                execution_time=execution_time
            )
    
    async def _get_prs_for_repo(self, project: str, repository: str, days_back: int) -> Dict[str, Any]:
        """Get pull requests for a specific repository."""
        try:
            # Use REST API for consistency with existing implementation
            api_url = f"{settings.azdo_org_url}/{project}/_apis/git/repositories/{repository}/pullrequests"
            params = {
                'api-version': '7.1',
                'searchCriteria.status': 'all',
                '$top': 50
            }
            headers = {'Accept': 'application/json'}
            auth = HTTPBasicAuth('', settings.azdo_pat)
            
            response = requests.get(api_url, params=params, auth=auth, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"API call failed: {response.status_code}")
            
            pr_data = response.json()
            prs = pr_data.get('value', [])
            
            # Filter by date
            cutoff_date = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=days_back)
            filtered_prs = []
            
            for pr in prs:
                pr_created = pr.get('creationDate', '')
                if pr_created:
                    pr_date = datetime.fromisoformat(pr_created.replace('Z', '+00:00'))
                    if pr_date >= cutoff_date:
                        filtered_prs.append({
                            "id": pr.get('pullRequestId'),
                            "title": pr.get('title', ''),
                            "status": pr.get('status', ''),
                            "created_by": pr.get('createdBy', {}).get('displayName', ''),
                            "created_date": pr_created[:10]
                        })
            
            return {
                "project": project,
                "repository": repository,
                "pull_requests": filtered_prs,
                "total_count": len(filtered_prs)
            }
            
        except Exception as e:
            raise Exception(f"Failed to get PRs for {project}/{repository}: {e}")
    
    async def batch_work_item_queries(self, queries: Dict[str, str]) -> BatchResult:
        """
        Execute multiple WIQL queries in parallel.
        queries: Dict mapping query names to WIQL strings
        """
        start_time = datetime.utcnow()
        results = {}
        errors = []
        
        try:
            # Create tasks for parallel query execution
            tasks = []
            query_names = list(queries.keys())
            
            for name, query in queries.items():
                tasks.append(self._execute_wiql_query(name, query))
            
            # Execute in parallel
            query_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(query_results):
                query_name = query_names[i]
                
                if isinstance(result, Exception):
                    errors.append(f"Query '{query_name}': {str(result)}")
                    results[query_name] = {"error": str(result)}
                else:
                    results[query_name] = result
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return BatchResult(
                success=len(errors) == 0,
                results=results,
                errors=errors,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return BatchResult(
                success=False,
                results={},
                errors=[str(e)],
                execution_time=execution_time
            )
    
    async def _execute_wiql_query(self, name: str, query: str) -> Dict[str, Any]:
        """Execute a single WIQL query."""
        try:
            work_items = _run_wiql(query)
            return {
                "query_name": name,
                "query": query,
                "work_items": work_items,
                "count": len(work_items)
            }
        except Exception as e:
            raise Exception(f"Query execution failed: {e}")
    
    async def batch_readme_fetch(self, repo_specs: List[Dict[str, str]]) -> BatchResult:
        """
        Fetch README files from multiple repositories in parallel.
        repo_specs: List of dicts with 'project', 'repository', and optional 'branch' keys
        """
        start_time = datetime.utcnow()
        results = {}
        errors = []
        
        try:
            # Create tasks for parallel README fetching
            tasks = []
            for spec in repo_specs:
                tasks.append(self._fetch_readme(spec))
            
            # Execute in parallel
            readme_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(readme_results):
                spec = repo_specs[i]
                key = f"{spec['project']}/{spec['repository']}"
                
                if isinstance(result, Exception):
                    errors.append(f"{key}: {str(result)}")
                    results[key] = {"error": str(result)}
                else:
                    results[key] = result
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return BatchResult(
                success=len(errors) == 0,
                results=results,
                errors=errors,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return BatchResult(
                success=False,
                results={},
                errors=[str(e)],
                execution_time=execution_time
            )
    
    async def _fetch_readme(self, spec: Dict[str, str]) -> Dict[str, Any]:
        """Fetch README for a single repository."""
        project = spec['project']
        repository = spec['repository']
        branch = spec.get('branch', 'main')
        
        try:
            git_client = self.connection.clients.get_git_client()
            
            # Try different README filenames
            readme_files = ["README.md", "readme.md", "README.txt", "README"]
            
            for filename in readme_files:
                try:
                    item = git_client.get_item(
                        repository_id=repository,
                        path=filename,
                        project=project,
                        version_descriptor_version_type="branch",
                        version_descriptor_version=branch
                    )
                    
                    if item and hasattr(item, 'content'):
                        return {
                            "project": project,
                            "repository": repository,
                            "branch": branch,
                            "filename": filename,
                            "content": item.content,
                            "size": len(item.content)
                        }
                        
                except Exception:
                    continue  # Try next filename
            
            # No README found
            return {
                "project": project,
                "repository": repository,
                "branch": branch,
                "filename": None,
                "content": None,
                "message": "No README file found"
            }
            
        except Exception as e:
            raise Exception(f"Failed to fetch README: {e}")
    
    def __del__(self):
        """Clean up the thread pool executor."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)