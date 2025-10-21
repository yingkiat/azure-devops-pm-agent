# Interactive Multi-Stage AI Workflow

## Overview

The Azure DevOps PM Agent now features a sophisticated **interactive multi-stage workflow** that intelligently handles work item creation with human approval gates, preventing accidental work item creation while enabling powerful AI-driven planning.

## Architecture Components

### 1. Smart Intent Routing (`src/ai_orchestrator/orchestrator.py`)

The system intelligently routes requests based on intent:

```python
# Query requests - Direct execution (fast)
"Show me critical bugs" → DISCOVERY/QUERY → Direct MCP execution

# Creation requests - Interactive approval (safe)
"Create epic for dashboard" → CREATE → Interactive multi-stage workflow
```

**Key Decision Logic:**
```python
creation_intents = ["CREATE", "CREATE_WORK_ITEM", "CREATE_EPIC", "CREATE_FEATURE"]
if any(keyword in classified_intent.intent.upper() for keyword in creation_intents):
    return await self._handle_interactive_creation(user_request, classified_intent)
```

### 2. Dynamic Work Item Classification (`src/ai_orchestrator/work_item_classifier.py`)

#### WorkItemType Enum
```python
class WorkItemType(Enum):
    EPIC = "Epic"
    FEATURE = "Feature" 
    USER_STORY = "User Story"
    TASK = "Task"
    BUG = "Bug"
    ISSUE = "Issue"
    TEST_CASE = "Test Case"
```

#### Classification Process
1. **AI-Powered Analysis**: Uses Azure OpenAI to analyze request complexity and scope
2. **Pattern Matching Fallback**: Keyword-based classification when AI unavailable
3. **Confidence Scoring**: 0.0-1.0 confidence with reasoning
4. **Complexity Assessment**: Simple → Moderate → Complex → Strategic

#### Hierarchical Planning
```python
@dataclass
class HierarchicalPlan:
    primary_work_item: WorkItemPlan
    child_items: List[WorkItemPlan]
    total_estimated_effort: str
    complexity_level: ComplexityLevel
```

**Example Breakdown:**
```
Epic: User Authentication System
├── Feature: Login UI Components (frontend-web)
├── Feature: Authentication API (backend-api)
└── Task: Security Testing (testing-framework)
```

### 3. Repository Intelligence (`src/ai_orchestrator/repository_intelligence.py`)

#### Repository Context Analysis
```python
@dataclass
class RepositoryContext:
    name: str
    project: str
    tech_stack: List[str]
    purpose: str
    keywords: List[str]
    readme_content: str
    recent_work_items: List[Dict[str, Any]]
    confidence_score: float
```

#### Intelligence Features
- **README Parsing**: Extracts technology stack and purpose
- **Historical Pattern Learning**: Analyzes past work item assignments
- **Keyword Matching**: Maps request terms to repository expertise
- **Confidence Scoring**: Relevance score 0.0-1.0 for repository selection

### 4. Interactive Approval System (`src/ai_orchestrator/interactive_planner.py`)

#### Approval Flow
1. **Proposal Generation**: Creates detailed work item proposals
2. **Rich Formatting**: User-friendly approval interface
3. **Interactive Options**:
   - `[y]` - Approve and execute
   - `[n]` - Reject proposal  
   - `[preview]` - Show detailed content
   - `[edit]` - Request modifications (extensible)

#### Proposal Structure
```python
@dataclass
class ExecutionProposal:
    request_text: str
    intent: str
    hierarchical_plan: HierarchicalPlan
    execution_summary: str
    estimated_timeline: str
    confidence_score: float
```

## Multi-Stage Process Flow

### Stage 1: Intent Classification & Enhancement
```python
async def classify_intent(self, user_request: str) -> ClassifiedIntent
```
- Analyzes natural language request
- Classifies into CREATE, QUERY, ANALYSIS, UPDATE, DISCOVERY
- Enhances with domain knowledge
- Returns confidence and reasoning

### Stage 2: Work Item Analysis  
```python
async def classify_work_item_type(self, request_text: str, intent: str) -> WorkItemTypeRecommendation
```
- Determines appropriate work item type (Epic, Feature, etc.)
- Analyzes complexity and scope
- Generates hierarchical breakdown for complex requests
- Provides effort estimation

### Stage 3: Repository Intelligence
```python
async def analyze_request_repositories(self, intent: str, request_text: str, projects: List[str]) -> List[RepositoryContext]
```
- Analyzes all available repositories
- Scores relevance to the request
- Extracts technology stack and purpose
- Learns from historical patterns

### Stage 4: Proposal Generation
```python
async def plan_work_items(self, request_text: str, intent: str, projects: List[str]) -> ExecutionProposal
```
- Combines work item analysis + repository intelligence
- Creates comprehensive execution proposal
- Estimates timeline and effort
- Provides risk assessment

### Stage 5: Interactive Approval
```python
def format_proposal_for_approval(self, proposal: ExecutionProposal) -> str
```
- Presents rich, formatted proposal
- Shows work item hierarchy
- Displays repository assignments
- Provides clear approval options

### Stage 6: Controlled Execution
```python
async def execute_approved_proposal(self, proposal: ExecutionProposal) -> Dict[str, Any]
```
- Creates work items in Azure DevOps
- Maintains parent-child relationships
- Provides detailed execution feedback
- Handles partial failures gracefully

## Safety Features

### 1. Approval Gates
- **Explicit Approval Required**: No work items created without human confirmation
- **Clear Proposals**: Rich formatting shows exactly what will be created
- **Cancellation Support**: Ctrl+C or explicit rejection stops execution
- **Preview Mode**: Detailed view before approval

### 2. Error Handling
- **Graceful Failures**: Partial execution with clear error reporting  
- **Fallback Classification**: Pattern matching when AI unavailable
- **Recovery Options**: Smart defaults for unclear scenarios
- **Context Preservation**: Maintains conversation state during errors

### 3. Learning System
- **Pattern Recognition**: Learns successful repository assignments
- **User Preferences**: Remembers common project and intent patterns
- **Historical Context**: Maintains conversation history for better decisions
- **Performance Tracking**: Monitors classification accuracy

## Configuration

### Environment Variables
```bash
# Azure DevOps
AZDO_ORG_URL=https://dev.azure.com/your-org/
AZDO_PROJECT=Your-Primary-Project
AZDO_PROJECTS=Project1,Project2,Project3  # Multiple projects
AZDO_PAT=your-personal-access-token

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-openai-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### User Preferences (`data/context/user_preferences.json`)
```json
{
    "preferred_projects": ["Data Platform", "Web App"],
    "common_intents": {
        "CREATE": 25,
        "QUERY": 45,
        "ANALYSIS": 30
    },
    "repository_patterns": {
        "dashboard": "frontend-web",
        "API": "backend-api"
    }
}
```

## Usage Examples

### Query Requests (Direct Execution)
```bash
python -m src.cli.ai_cli ask "Show me all projects"
python -m src.cli.ai_cli ask "Find critical bugs assigned to John"
python -m src.cli.ai_cli ask "What's our sprint progress?"
```

### Creation Requests (Interactive Approval)
```bash
# Simple creation
python -m src.cli.ai_cli ask "Create epic for user dashboard"

# Complex hierarchical creation  
python -m src.cli.ai_cli ask "Epic for complete user authentication system"

# Bug reporting
python -m src.cli.ai_cli ask "Add bug for memory leak in auth service"
```

### Interactive Chat Mode
```bash
python -m src.cli.ai_cli chat

🎯 What would you like to know? Create epic for data platform
[Displays interactive approval workflow]
💬 Your decision: y
✅ Creating Epic #123: Data Platform Initiative
```

## Extension Points

### 1. Custom Work Item Types
Add new work item types in `work_item_classifier.py`:
```python
class WorkItemType(Enum):
    EPIC = "Epic"
    CUSTOM_TYPE = "Custom Type"  # Add here
```

### 2. Repository Intelligence Plugins
Extend repository analysis in `repository_intelligence.py`:
```python
async def _analyze_repository_context(self, project: str, repository: str):
    # Add custom analysis logic
    # e.g., package.json parsing, Dockerfile analysis
```

### 3. Custom Approval Workflows  
Extend approval options in `interactive_planner.py`:
```python
def format_proposal_for_approval(self, proposal: ExecutionProposal):
    # Add custom approval options
    # e.g., schedule creation, assign reviewers
```

## Testing

### Unit Tests
```bash
# Test work item classification
python -c "from src.ai_orchestrator.work_item_classifier import WorkItemClassifier; ..."

# Test repository intelligence
python tests/test_repository_intelligence.py

# Test interactive planning
python tests/test_interactive_planner.py
```

### Integration Tests
```bash
# Full workflow test
python -m src.cli.ai_cli ask "Create task for testing" --dry-run

# Context persistence test
python tests/test_context_persistence.py
```

## Performance Considerations

### AI Model Usage
- **Classification**: Single API call per request
- **Repository Analysis**: Cached results for 1 hour
- **Proposal Generation**: Optimized prompts with context limits

### Caching Strategy
- **Repository Contexts**: Cached in memory + disk
- **User Preferences**: Persistent across sessions  
- **Classification Patterns**: Learning-based optimization

### Scalability
- **Async Processing**: All AI calls are asynchronous
- **Batch Operations**: Repository analysis uses batch APIs
- **Context Limits**: Automatic truncation for large conversations

## Troubleshooting

### Common Issues

1. **AI Classification Failures**: Falls back to pattern matching
2. **Repository Analysis Errors**: Uses default repository assignments
3. **Approval Timeout**: Maintains proposal state for retry
4. **Partial Execution**: Clear error reporting with recovery options

### Debug Mode
```bash
python -m src.cli.ai_cli ask "create epic" --show-plan --show-raw
```

### Logging
All components log to `data/logs/` with structured JSON format:
```json
{
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "INFO",
    "component": "work_item_classifier",
    "message": "Epic classification completed",
    "confidence": 0.92,
    "user_request": "Create epic for dashboard"
}
```