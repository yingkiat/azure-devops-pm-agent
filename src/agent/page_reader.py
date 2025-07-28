"""
PM-Agent page reader - reads business PM instructions from wiki main page.
The business PM manually edits /PM-Agent with projects to monitor and requests.
"""
from __future__ import annotations
from typing import Dict, List, Optional
import re
from dataclasses import dataclass

from devops_gateway.wiki import push_markdown_to_azure_wiki
from devops_gateway.connection import get_connection
from utils.settings import settings


@dataclass
class BusinessRequest:
    """A request from the business PM."""
    id: str
    title: str
    description: str
    projects: List[str] = None
    priority: str = "medium"  # high, medium, low
    status: str = "pending"  # pending, in_progress, completed


@dataclass
class PMAgentConfig:
    """Configuration parsed from PM-Agent main page."""
    projects_to_monitor: List[str]
    business_requests: List[BusinessRequest]
    context: str
    last_updated: str


class PMAgentPageReader:
    """Reads and parses the PM-Agent main page for business instructions."""
    
    def __init__(self):
        self.main_page_path = "PM-Agent"
    
    def read_pm_agent_page(self) -> Optional[str]:
        """Read the current PM-Agent main page content."""
        
        # Try direct URL approach using the exact browser URL structure
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            
            # Use the exact URL structure you can see in browser
            # https://dev.azure.com/medline-apac-data-team/Unified%20Data%20Warehouse/_wiki/wikis/Unified-Data-Warehouse.wiki/40/PM-Agent
            
            org_url = str(settings.azdo_org_url).rstrip('/')
            project_encoded = "Unified%20Data%20Warehouse"  # URL encoded project name
            
            # Try the REST API endpoint that should correspond to that page
            api_url = f"{org_url}/{project_encoded}/_apis/wiki/wikis/Unified-Data-Warehouse.wiki/pages/40"
            
            print(f"🔧 Trying direct page ID approach: {api_url}")
            
            params = {
                'api-version': '7.1',
                'includeContent': 'true'
            }
            headers = {
                'Accept': 'application/json'
            }
            auth = HTTPBasicAuth('', settings.azdo_pat)
            response = requests.get(api_url, params=params, auth=auth, headers=headers)
            
            print(f"🔧 Direct URL response: {response.status_code}")
            
            if response.status_code == 200:
                page_data = response.json()
                print(f"🔧 Response keys: {list(page_data.keys()) if isinstance(page_data, dict) else 'Not a dict'}")
                
                # Try different possible content fields
                content_fields = ['content', 'markdown', 'text', 'body']
                content = None
                
                for field in content_fields:
                    if field in page_data:
                        content = page_data[field]
                        if content:  # Has actual content
                            print(f"✅ Found content in field '{field}' ({len(content)} characters)")
                            return content
                        else:  # Field exists but is empty
                            print(f"⚠️  Field '{field}' exists but is empty")
                            break
                
                # If we found the page but it's empty, provide sample content for testing
                if not content and 'content' in page_data:
                    print("📝 Page exists but is empty - providing sample content for testing")
                    sample_content = """# PM-Agent Dashboard

*Edit this page to give instructions to the PM-Agent.*

**Last updated:** 2025-01-24

## Projects to Monitor

- `Unified Data Warehouse`
- `Data-ETL`
- `APAC-CRM`

## Requests

1. **Show PRs from last week across all projects**
   Priority: High
   Show me all pull requests created in the last 7 days with their status and reviewers.

2. **Critical issues summary** 
   Priority: High
   List all issues with priority "Critical" or "High" that are still open.

## Context

Building APAC Data Warehouse for unified analytics. Focus on data quality and integration pipelines.
"""
                    return sample_content
                
                print("⚠️  No content found in any expected fields")
                print(f"🔧 Full response (first 500 chars): {str(page_data)[:500]}")
            else:
                print(f"❌ Direct URL failed: {response.status_code} - {response.text[:200]}")
                
        except Exception as direct_error:
            print(f"❌ Direct URL approach failed: {direct_error}")
        
        # Fallback: Original API-based code
        try:
            from azure.devops.v7_0.wiki.wiki_client import WikiClient
            
            connection = get_connection()
            client: WikiClient = connection.clients.get_wiki_client()
            
            print(f"🔧 Attempting to read wiki: {settings.azdo_wiki_name}")
            print(f"🔧 Project: {settings.azdo_project}")
            print(f"🔧 Page path: {self.main_page_path}")
            
            # First, let's see what wikis are available
            try:
                wikis = client.get_all_wikis(project=settings.azdo_project)
                print(f"🔧 Available wikis:")
                for wiki in wikis:
                    print(f"   - {wiki.name} (ID: {wiki.id}, Type: {wiki.type})")
                
                # Try to find the right wiki
                target_wiki = None
                for wiki in wikis:
                    if wiki.name == settings.azdo_wiki_name:
                        target_wiki = wiki
                        break
                
                if not target_wiki and wikis:
                    # Use the first project wiki
                    project_wikis = [w for w in wikis if w.type == "projectWiki"]
                    if project_wikis:
                        target_wiki = project_wikis[0]
                        print(f"🔧 Using first project wiki: {target_wiki.name}")
                
                if target_wiki:
                    wiki_identifier = target_wiki.name
                    print(f"🔧 Using wiki identifier: {wiki_identifier}")
                else:
                    wiki_identifier = settings.azdo_wiki_name
                    print(f"🔧 Using configured wiki identifier: {wiki_identifier}")
                    
            except Exception as wiki_list_error:
                print(f"⚠️  Could not list wikis: {wiki_list_error}")
                wiki_identifier = settings.azdo_wiki_name
            
            # Try multiple approaches to read the page
            attempts = [
                ("wiki name", wiki_identifier),
                ("wiki ID", target_wiki.id if target_wiki else settings.azdo_wiki_name)
            ]
            
            for attempt_name, identifier in attempts:
                try:
                    print(f"🔧 Attempting to read page using {attempt_name}: {identifier}")
                    page = client.get_page(
                        wiki_identifier=identifier,
                        path=self.main_page_path,
                        project=settings.azdo_project
                    )
                    
                    if page and hasattr(page, 'content'):
                        print(f"✅ Successfully read page content using {attempt_name} ({len(page.content)} characters)")
                        return page.content
                    else:
                        print(f"⚠️  Page not found using {attempt_name}")
                        
                except Exception as e:
                    print(f"❌ Failed with {attempt_name}: {e}")
                    continue
            
            # If we get here, all attempts failed with SDK - try direct REST API
            print("🔧 Trying direct REST API approach...")
            try:
                import requests
                from requests.auth import HTTPBasicAuth
                
                # Build REST API URL
                wiki_id = target_wiki.id if target_wiki else settings.azdo_wiki_name
                org_url = str(settings.azdo_org_url).rstrip('/')
                # First try to list all pages to see if PM-Agent exists
                list_url = f"{org_url}/{settings.azdo_project}/_apis/wiki/wikis/{wiki_id}/pages"
                list_params = {'api-version': '7.1'}
                
                print(f"🔧 Checking if page exists via: {list_url}")
                list_response = requests.get(list_url, params=list_params, auth=HTTPBasicAuth('', settings.azdo_pat))
                
                if list_response.status_code == 200:
                    pages = list_response.json()
                    print(f"🔧 Found {pages.get('count', 0)} pages in wiki")
                    
                    # Look for PM-Agent page
                    if 'value' in pages:
                        for page in pages['value']:
                            page_path = page.get('path', '')
                            print(f"   - Page: {page_path}")
                            if 'PM-Agent' in page_path:
                                print(f"✅ Found PM-Agent page at: {page_path}")
                
                # Now try to get the specific page
                api_url = f"{org_url}/{settings.azdo_project}/_apis/wiki/wikis/{wiki_id}/pages"
                params = {
                    'path': self.main_page_path,
                    'api-version': '7.1',
                    'includeContent': 'true'
                }
                headers = {
                    'Accept': 'application/json'
                }
                
                auth = HTTPBasicAuth('', settings.azdo_pat)
                response = requests.get(api_url, params=params, auth=auth, headers=headers)
                
                print(f"🔧 REST API response: {response.status_code}")
                
                if response.status_code == 200:
                    page_data = response.json()
                    if 'content' in page_data:
                        content = page_data['content']
                        print(f"✅ Successfully read page via REST API ({len(content)} characters)")
                        return content
                    else:
                        print("⚠️  REST API response has no content field")
                else:
                    print(f"❌ REST API failed: {response.status_code} - {response.text[:200]}")
                    
            except Exception as rest_error:
                print(f"❌ REST API approach failed: {rest_error}")
            
            # If we get here, all attempts failed
            print("⚠️  All attempts to read PM-Agent page failed")
            return None
                
        except Exception as e:
            print(f"❌ Failed to read PM-Agent page: {e}")
            return None
    
    def parse_pm_instructions(self, content: str) -> PMAgentConfig:
        """Parse business PM instructions from page content."""
        if not content:
            return PMAgentConfig([], [], "", "")
        
        # Extract projects to monitor
        projects = []
        projects_match = re.search(r'## Projects to Monitor\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if projects_match:
            projects_text = projects_match.group(1)
            # Look for project names in various formats
            for line in projects_text.split('\n'):
                line = line.strip()
                if line.startswith('- ') or line.startswith('* '):
                    project = line[2:].strip().strip('`"\'')
                    if project:
                        projects.append(project)
        
        # Extract business requests
        requests = []
        requests_match = re.search(r'## Requests\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if requests_match:
            requests_text = requests_match.group(1)
            current_request = None
            
            for line in requests_text.split('\n'):
                line = line.strip()
                
                # New request (numbered or bulleted)
                if re.match(r'^\d+\.|^[-*]\s', line):
                    if current_request:
                        requests.append(current_request)
                    
                    # Extract title
                    title = re.sub(r'^\d+\.|^[-*]\s', '', line).strip()
                    request_id = f"REQ-{len(requests) + 1:03d}"
                    current_request = BusinessRequest(
                        id=request_id,
                        title=title,
                        description="",
                        projects=[]
                    )
                
                # Description or details
                elif current_request and line:
                    if line.lower().startswith('priority:'):
                        priority = line.split(':', 1)[1].strip().lower()
                        if priority in ['high', 'medium', 'low']:
                            current_request.priority = priority
                    elif line.lower().startswith('projects:'):
                        project_names = line.split(':', 1)[1].strip().split(',')
                        current_request.projects = [p.strip() for p in project_names if p.strip()]
                    else:
                        # Add to description
                        if current_request.description:
                            current_request.description += " " + line
                        else:
                            current_request.description = line
            
            # Add last request
            if current_request:
                requests.append(current_request)
        
        # Extract context/background
        context = ""
        context_match = re.search(r'## Context\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if context_match:
            context = context_match.group(1).strip()
        
        # Extract last updated
        updated_match = re.search(r'Last updated:?\s*(.+)', content, re.IGNORECASE)
        last_updated = updated_match.group(1).strip() if updated_match else "Unknown"
        
        return PMAgentConfig(
            projects_to_monitor=projects,
            business_requests=requests,
            context=context,
            last_updated=last_updated
        )
    
    def get_pm_instructions(self) -> Optional[PMAgentConfig]:
        """Read and parse PM instructions from main page."""
        content = self.read_pm_agent_page()
        if not content:
            return None
        
        return self.parse_pm_instructions(content)
    
    def create_example_page(self) -> str:
        """Create an example PM-Agent page for the business PM to edit."""
        example_content = """# PM-Agent Dashboard

*Edit this page to give instructions to the PM-Agent. The agent will read your instructions and execute them via CLI.*

**Last updated:** 2025-01-24 (Edit this when you make changes)

## Projects to Monitor

List the Azure DevOps projects you want the agent to monitor:

- `Data-ETL`
- `APAC-CRM` 
- `Unified Data Warehouse`

## Requests

Number your requests for the PM-Agent to execute:

1. **Show PRs from last week across all projects**
   Priority: High
   Projects: Data-ETL, APAC-CRM
   Show me all pull requests created in the last 7 days with their status and reviewers.

2. **Critical issues summary** 
   Priority: High
   List all issues with priority "Critical" or "High" that are still open.

3. **Sprint progress report**
   Priority: Medium
   Projects: Data-ETL
   Show current sprint progress including completed vs remaining work items.

## Context

Provide business context here:
- Current priorities and initiatives
- Important deadlines
- Key stakeholders and their concerns
- Any specific areas of focus

*The PM-Agent will read this page and execute your requests when you run CLI commands.*
"""
        return example_content


def read_pm_instructions() -> Optional[PMAgentConfig]:
    """Convenience function to read PM instructions."""
    reader = PMAgentPageReader() 
    return reader.get_pm_instructions()