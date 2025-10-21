
from azure.devops.v7_0.wiki.wiki_client import WikiClient
from azure.devops.v7_0.wiki.models import WikiPageCreateOrUpdateParameters
from .connection import get_connection
from utils.settings import settings

def push_markdown_to_azure_wiki(markdown: str, page_path: str, wiki_name: str = None, max_retries: int = 3):
    """
    Push markdown content to a page in Azure DevOps Wiki.
    If wiki_name is not provided, use the default project wiki.
    Handles wiki creation and path validation with retry logic.
    """
    import time
    
    for attempt in range(max_retries):
        try:
            connection = get_connection()
            client: WikiClient = connection.clients.get_wiki_client()
            
            # Get or create wiki
            if wiki_name is None:
                wiki_name = settings.azdo_wiki_name
            
            # Try to get existing wiki first
            try:
                wikis = client.get_all_wikis(project=settings.azdo_project)
                target_wiki = None
                
                for wiki in wikis:
                    if wiki.name == wiki_name:
                        target_wiki = wiki
                        break
                
                if not target_wiki:
                    # If no specific wiki found, use the first project wiki
                    project_wikis = [w for w in wikis if w.type == "projectWiki"]
                    if project_wikis:
                        target_wiki = project_wikis[0]
                        wiki_name = target_wiki.name
                
                if not target_wiki:
                    raise Exception(f"No wiki found in project {settings.azdo_project}")
                    
            except Exception as e:
                raise Exception(f"Failed to find wiki: {e}")
            
            # Clean page path (remove leading/trailing slashes, handle special chars)
            clean_path = page_path.strip("/")
            if not clean_path:
                clean_path = "PM-Agent"
            
            # For main dashboard, skip parent creation to avoid recursion
            if clean_path != "PM-Agent":
                # Ensure parent pages exist before creating child pages
                path_parts = clean_path.split("/")
                for i in range(1, len(path_parts)):
                    parent_path = "/".join(path_parts[:i])
                    if parent_path and parent_path != "PM-Agent":  # Skip if parent is main page
                        try:
                            # Try to get the parent page to see if it exists
                            client.get_page(
                                wiki_identifier=wiki_name,
                                path=parent_path,
                                project=settings.azdo_project
                            )
                        except:
                            # Try to create parent, but don't fail if it doesn't work
                            try:
                                parent_content = f"# {path_parts[i-1]}\n\nThis page was auto-created for PM-Agent organization."
                                parent_params = WikiPageCreateOrUpdateParameters(content=parent_content)
                                client.create_or_update_page(
                                    parameters=parent_params,
                                    wiki_identifier=wiki_name,
                                    path=parent_path,
                                    project=settings.azdo_project,
                                    version=None
                                )
                            except:
                                pass  # Ignore parent creation failures
            
            # Get current page ETag for proper versioning (fixes silent update failures)
            current_etag = None
            try:
                current_page = client.get_page(
                    wiki_identifier=wiki_name,
                    path=clean_path,
                    project=settings.azdo_project
                )
                if current_page and hasattr(current_page, 'response') and current_page.response:
                    current_etag = current_page.response.headers.get('ETag')
                    print(f" Retrieved ETag for {clean_path}: {current_etag}")
                elif hasattr(current_page, 'etag'):
                    current_etag = current_page.etag
                    print(f" Retrieved ETag (direct) for {clean_path}: {current_etag}")
            except Exception as e:
                print(f" No existing page found for {clean_path}, creating new: {e}")
            
            params = WikiPageCreateOrUpdateParameters(content=markdown)
            
            # Create or update the page with proper ETag versioning
            result = client.create_or_update_page(
                parameters=params,
                wiki_identifier=wiki_name,
                path=clean_path,
                project=settings.azdo_project,
                version=current_etag
            )
            
            print(f" Wiki update result for {clean_path}: {result is not None}")
            print(f" Content length: {len(markdown)} characters")
            print(f" Wiki: {wiki_name}, Project: {settings.azdo_project}")
            
            # Verify the update actually worked by checking new ETag
            if result and hasattr(result, 'response') and result.response:
                new_etag = result.response.headers.get('ETag')
                print(f" New ETag after update: {new_etag}")
                if new_etag and new_etag != current_etag:
                    print(f" ETag changed - update successful!")
                elif new_etag == current_etag:
                    print(f"  ETag unchanged - content may be identical")
                else:
                    print(f"  Could not verify ETag change")
            
            # Small delay to let Azure DevOps process the update
            import time
            time.sleep(0.5)
            
            return True
            
        except Exception as e:
            # Check if it's a 500 error but the page might have been created anyway
            if "500 error" in str(e) or "too many 500" in str(e):
                # Try to verify if the page was actually created despite the error
                try:
                    connection = get_connection()
                    client: WikiClient = connection.clients.get_wiki_client()
                    if wiki_name is None:
                        wiki_name = settings.azdo_wiki_name
                    
                    clean_path = page_path.strip("/")
                    if not clean_path:
                        clean_path = "PM-Agent"
                    
                    verification = client.get_page(
                        wiki_identifier=wiki_name,
                        path=clean_path,
                        project=settings.azdo_project
                    )
                    if verification:
                        print(f" Wiki page exists despite 500 error: {clean_path}")
                        return True
                except:
                    pass  # Verification failed, continue with retry logic
            
            if attempt < max_retries - 1:
                # Wait before retrying (exponential backoff)
                wait_time = (2 ** attempt) * 1  # 1, 2, 4 seconds
                print(f"Wiki update attempt {attempt + 1} failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                # Final attempt - check one more time if page exists
                try:
                    connection = get_connection()
                    client: WikiClient = connection.clients.get_wiki_client()
                    if wiki_name is None:
                        wiki_name = settings.azdo_wiki_name
                    
                    clean_path = page_path.strip("/")
                    if not clean_path:
                        clean_path = "PM-Agent"
                    
                    verification = client.get_page(
                        wiki_identifier=wiki_name,
                        path=clean_path,
                        project=settings.azdo_project
                    )
                    if verification:
                        print(f" Wiki page exists despite errors: {clean_path}")
                        return True
                except:
                    pass
                
                print(f"Wiki update failed after {max_retries} attempts: {e}")
                return False
    
    return False
from .work_items import create_work_item


import json
from typing import List, Dict, Any

def extract_epics_from_plan(plan_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract epics from the plan JSON structure.
    Assumes epics are under a key like 'epics' or similar.
    """
    # Try common keys, fallback to searching for epic-like items
    if 'epics' in plan_json:
        return plan_json['epics']
    # Fallback: look for items with type 'epic'
    if 'items' in plan_json:
        return [item for item in plan_json['items'] if item.get('type', '').lower() == 'epic']
    # Fallback: return empty
    return []

def format_epics_for_wiki(epics: List[Dict[str, Any]]) -> str:
    """
    Format a list of epics into a markdown summary for business users.
    """
    if not epics:
        return "No epics proposed in this plan."
    lines = ["# Proposed Epics\n"]
    for idx, epic in enumerate(epics, 1):
        title = epic.get('title') or epic.get('name') or f"Epic {idx}"
        desc = epic.get('description', '').strip()
        lines.append(f"## {idx}. {title}")
        if desc:
            lines.append(f"{desc}\n")
        else:
            lines.append("(No description provided)\n")
    return '\n'.join(lines)

def save_plan_to_wiki(plan_json: Dict[str, Any], wiki_path: str) -> None:
    """
    Save the formatted epics summary to a wiki file (markdown).
    """
    epics = extract_epics_from_plan(plan_json)
    summary = format_epics_for_wiki(epics)
    # Optionally write to local file
    if wiki_path:
        with open(wiki_path, 'w', encoding='utf-8') as f:
            f.write(summary)
    # Always push to Azure DevOps wiki
    page_path = settings.azdo_wiki_page
    push_markdown_to_azure_wiki(summary, page_path)

def create_epics_in_azure_devops(plan_json: Dict[str, Any]) -> list:
    """
    Create epics in Azure DevOps from the plan JSON.
    Returns a list of created work item dicts.
    """
    epics = extract_epics_from_plan(plan_json)
    created = []
    for epic in epics:
        title = epic.get('title') or epic.get('name') or "Untitled Epic"
        description = epic.get('description', '')
        wi = create_work_item("Epic", title, description)
        created.append(wi)
    return created
    """
    Save the formatted epics summary to a wiki file (markdown).
    """
    epics = extract_epics_from_plan(plan_json)
    summary = format_epics_for_wiki(epics)
    with open(wiki_path, 'w', encoding='utf-8') as f:
        f.write(summary)

# Example usage (to be replaced with actual integration)
# with open('plans/plan-20250722-135928.json') as f:
#     plan = json.load(f)
# save_plan_to_wiki(plan, 'wiki_output.md')
