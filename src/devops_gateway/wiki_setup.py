"""
Wiki setup utilities to ensure PM-Agent wiki structure exists.
"""
from .wiki import push_markdown_to_azure_wiki

def ensure_pm_agent_wiki_structure():
    """
    Ensure the basic PM-Agent wiki structure exists.
    Creates the main PM-Agent page and Interactions folder if they don't exist.
    """
    
    # Create main PM-Agent page
    main_page_content = """# PM-Agent Dashboard

LLM-powered Program/Project Manager agent for Azure DevOps.

This page will be automatically updated with your plans and interactions.

## Getting Started

Use the CLI to create your first plan:

```bash
python -m src.cli.main plan-new "Your business goal here"
```

*This page was auto-created by PM-Agent.*
"""
    
    success = push_markdown_to_azure_wiki(main_page_content, "PM-Agent")
    if not success:
        print("⚠️  Could not create main PM-Agent page")
        return False
    
    # Create Interactions folder page
    interactions_content = """# PM-Agent Interactions

This folder contains transcripts of all PM-Agent interactions.

Each interaction is logged with:
- Full conversation transcript
- Generated plan details
- Sync results and status

*This page was auto-created by PM-Agent.*
"""
    
    success = push_markdown_to_azure_wiki(interactions_content, "PM-Agent/Interactions")
    if not success:
        print("⚠️  Could not create PM-Agent/Interactions page")
        return False
    
    print("✅ PM-Agent wiki structure created successfully")
    return True

def test_wiki_access():
    """
    Test basic wiki access and permissions.
    """
    test_content = "# Wiki Test\n\nTesting PM-Agent wiki access."
    success = push_markdown_to_azure_wiki(test_content, "PM-Agent-Test")
    
    if success:
        print("✅ Wiki access test successful")
        return True
    else:
        print("❌ Wiki access test failed - check permissions and settings")
        return False