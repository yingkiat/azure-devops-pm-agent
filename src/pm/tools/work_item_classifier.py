"""
Dynamic Work Item Type Classification for Azure DevOps PM Agent.

This module provides intelligent work item type classification and hierarchical planning
capabilities for natural language requests. It supports the full Azure DevOps Agile
process template with automatic Epic → Feature → User Story → Task breakdown.

Key Features:
- Dynamic work item type detection (Epic, Feature, User Story, Task, Bug, Issue)
- Hierarchical planning for complex requests 
- AI-powered analysis with pattern-matching fallbacks
- Confidence scoring and reasoning for all classifications
- Extensible architecture for custom work item types

Usage:
    classifier = WorkItemClassifier()
    recommendation = await classifier.classify_work_item_type("Create epic for dashboard", "CREATE")
    plan = await classifier.plan_hierarchical_work_items("Complex request", "CREATE", recommendation)

Architecture:
    - Primary AI classification using Azure OpenAI
    - Fallback pattern matching using keyword detection
    - Hierarchical breakdown for complex requests
    - Confidence scoring and reasoning for transparency
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from utils.openai_client import client
from utils.settings import settings


class WorkItemType(Enum):
    """Azure DevOps Agile process template work item types."""
    EPIC = "Epic"
    FEATURE = "Feature" 
    USER_STORY = "User Story"
    TASK = "Task"
    BUG = "Bug"
    ISSUE = "Issue"
    TEST_CASE = "Test Case"


class ComplexityLevel(Enum):
    """Request complexity levels for hierarchical planning."""
    SIMPLE = "simple"       # Single work item
    MODERATE = "moderate"   # 2-3 work items
    COMPLEX = "complex"     # Full hierarchy needed
    STRATEGIC = "strategic" # Epic-level planning


@dataclass
class WorkItemTypeRecommendation:
    """Recommendation for work item type with reasoning."""
    work_item_type: WorkItemType
    confidence: float
    reasoning: str
    scope_indicators: List[str]
    complexity_level: ComplexityLevel
    

@dataclass 
class HierarchicalPlan:
    """Multi-level work item hierarchy plan."""
    primary_work_item: 'WorkItemPlan'
    child_items: List['WorkItemPlan']
    total_estimated_effort: str
    complexity_level: ComplexityLevel
    

@dataclass
class WorkItemPlan:
    """Individual work item in a hierarchical plan."""
    title: str
    description: str
    work_item_type: WorkItemType
    target_repository: str
    parent_id: Optional[str]
    estimated_effort: str
    acceptance_criteria: List[str]
    dependencies: List[str]
    confidence: float
    reasoning: str


class WorkItemClassifier:
    """
    Intelligent work item type classification and hierarchical planning.
    
    This class provides the core intelligence for determining appropriate work item types
    from natural language requests and generating hierarchical work item breakdowns.
    
    The classifier uses a multi-layered approach:
    1. AI-powered analysis using Azure OpenAI for semantic understanding
    2. Pattern matching fallback using keyword detection and scoring
    3. Hierarchical planning for complex requests requiring multiple work items
    4. Confidence scoring and detailed reasoning for transparency
    
    Attributes:
        type_patterns (Dict): Mapping of work item types to detection patterns
    """
    
    def __init__(self):
        # Language patterns for different work item types
        self.type_patterns = {
            WorkItemType.EPIC: {
                "keywords": ["epic", "initiative", "program", "portfolio", "strategic", "large", "major"],
                "scope_indicators": ["across multiple", "entire system", "platform", "organization-wide"],
                "typical_effort": "months"
            },
            WorkItemType.FEATURE: {
                "keywords": ["feature", "capability", "functionality", "module", "component"],
                "scope_indicators": ["new functionality", "user capability", "system feature"],
                "typical_effort": "weeks"
            },
            WorkItemType.USER_STORY: {
                "keywords": ["user story", "story", "user can", "as a user", "user needs"],
                "scope_indicators": ["user perspective", "user value", "customer journey"],
                "typical_effort": "days"
            },
            WorkItemType.TASK: {
                "keywords": ["task", "do", "implement", "create", "update", "configure", "setup"],
                "scope_indicators": ["specific action", "technical task", "implementation step"],
                "typical_effort": "hours"
            },
            WorkItemType.BUG: {
                "keywords": ["bug", "fix", "broken", "error", "issue", "defect", "not working"],
                "scope_indicators": ["something is wrong", "unexpected behavior", "system fault"],
                "typical_effort": "varies"
            },
            WorkItemType.ISSUE: {
                "keywords": ["issue", "problem", "concern", "blocker", "impediment"],
                "scope_indicators": ["blocking work", "needs resolution", "process issue"],
                "typical_effort": "varies"
            }
        }
    
    async def classify_work_item_type(self, request_text: str, intent: str) -> WorkItemTypeRecommendation:
        """Classify the appropriate work item type for a request."""
        
        classification_prompt = f"""
Analyze this request and determine the most appropriate Azure DevOps work item type:

REQUEST: "{request_text}"
INTENT: {intent}

Available Work Item Types:
- Epic: Large strategic initiatives spanning months, multiple features
- Feature: Significant new functionality, typically 2-4 weeks of work
- User Story: Specific user value, 1-5 days of work, user perspective
- Task: Individual actionable work item, hours to days
- Bug: Defect or error that needs fixing
- Issue: Problem or impediment that blocks progress

Analyze:
1. Scope and complexity (individual task vs large initiative)
2. Time horizon (hours, days, weeks, months)
3. User value vs technical work
4. Language cues ("epic for", "fix the", "user can", etc.)

Respond in JSON format:
{{
    "work_item_type": "Epic|Feature|User Story|Task|Bug|Issue",
    "confidence": 0.95,
    "reasoning": "Why this type was selected based on scope and language",
    "scope_indicators": ["indicator1", "indicator2"],
    "complexity_level": "simple|moderate|complex|strategic"
}}

Examples:
- "Create epic for user authentication system" → Epic (explicit, large scope)
- "Add login button to homepage" → Task (small, specific action)
- "Users should be able to reset passwords" → User Story (user value)
- "Fix memory leak in API service" → Bug (defect fixing)
- "Research best React framework" → Task (investigation work)
"""

        try:
            response = client.chat.completions.create(
                model=settings.azure_openai_deployment,
                messages=[{"role": "user", "content": classification_prompt}],
                temperature=0.1
            )
            
            classification_text = response.choices[0].message.content
            
            # Extract JSON from response
            start_idx = classification_text.find('{')
            end_idx = classification_text.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                classification_json = json.loads(classification_text[start_idx:end_idx])
                
                return WorkItemTypeRecommendation(
                    work_item_type=WorkItemType(classification_json["work_item_type"]),
                    confidence=classification_json["confidence"],
                    reasoning=classification_json["reasoning"],
                    scope_indicators=classification_json["scope_indicators"],
                    complexity_level=ComplexityLevel(classification_json["complexity_level"])
                )
                
        except Exception as e:
            print(f"Error in work item classification: {e}")
        
        # Fallback to pattern matching
        return self._fallback_classification(request_text, intent)
    
    def _fallback_classification(self, request_text: str, intent: str) -> WorkItemTypeRecommendation:
        """Fallback classification using keyword matching."""
        request_lower = request_text.lower()
        
        # Score each work item type based on keyword matches
        type_scores = {}
        for work_item_type, patterns in self.type_patterns.items():
            score = 0
            matched_indicators = []
            
            # Check keywords
            for keyword in patterns["keywords"]:
                if keyword in request_lower:
                    score += 1
                    matched_indicators.append(f"keyword: {keyword}")
            
            # Check scope indicators  
            for indicator in patterns["scope_indicators"]:
                if indicator.lower() in request_lower:
                    score += 2  # Scope indicators worth more
                    matched_indicators.append(f"scope: {indicator}")
            
            if score > 0:
                type_scores[work_item_type] = (score, matched_indicators)
        
        if type_scores:
            # Get highest scoring type
            best_type = max(type_scores, key=lambda t: type_scores[t][0])
            score, indicators = type_scores[best_type]
            
            return WorkItemTypeRecommendation(
                work_item_type=best_type,
                confidence=min(0.8, score * 0.2),  # Conservative confidence
                reasoning=f"Pattern matching: {', '.join(indicators)}",
                scope_indicators=indicators,
                complexity_level=ComplexityLevel.SIMPLE if score <= 2 else ComplexityLevel.MODERATE
            )
        
        # Ultimate fallback
        return WorkItemTypeRecommendation(
            work_item_type=WorkItemType.TASK,
            confidence=0.3,
            reasoning="Default classification - no clear patterns matched",
            scope_indicators=[],
            complexity_level=ComplexityLevel.SIMPLE
        )
    
    async def plan_hierarchical_work_items(self, request_text: str, intent: str, primary_recommendation: WorkItemTypeRecommendation) -> HierarchicalPlan:
        """Generate hierarchical work item plan for complex requests."""
        
        if primary_recommendation.complexity_level in [ComplexityLevel.SIMPLE]:
            # Single work item, no hierarchy needed
            work_item = WorkItemPlan(
                title=self._generate_title(request_text, primary_recommendation.work_item_type),
                description=request_text,
                work_item_type=primary_recommendation.work_item_type,
                target_repository="",  # To be filled by repository intelligence
                parent_id=None,
                estimated_effort="TBD",
                acceptance_criteria=[],
                dependencies=[],
                confidence=primary_recommendation.confidence,
                reasoning=primary_recommendation.reasoning
            )
            
            return HierarchicalPlan(
                primary_work_item=work_item,
                child_items=[],
                total_estimated_effort="TBD",
                complexity_level=primary_recommendation.complexity_level
            )
        
        # Complex request - generate hierarchy
        hierarchy_prompt = f"""
Generate a hierarchical work item breakdown for this complex request:

REQUEST: "{request_text}"
PRIMARY TYPE: {primary_recommendation.work_item_type.value}
COMPLEXITY: {primary_recommendation.complexity_level.value}

Create a logical hierarchy following Azure DevOps patterns:
- Epic → Features → User Stories → Tasks
- Feature → User Stories → Tasks  
- User Story → Tasks

Generate realistic breakdown with:
1. Primary work item (the main Epic/Feature)
2. Child work items that break down the work logically
3. Acceptance criteria for user-facing items
4. Realistic effort estimates

Respond in JSON format:
{{
    "primary_work_item": {{
        "title": "Main work item title",
        "description": "Detailed description",
        "work_item_type": "Epic|Feature|User Story|Task",
        "estimated_effort": "3-5 weeks",
        "acceptance_criteria": ["criteria1", "criteria2"],
        "dependencies": []
    }},
    "child_items": [
        {{
            "title": "Child work item title",
            "description": "Child description",
            "work_item_type": "Feature|User Story|Task", 
            "estimated_effort": "1-2 weeks",
            "acceptance_criteria": ["criteria1"],
            "dependencies": ["dependency if any"]
        }}
    ],
    "total_estimated_effort": "6-10 weeks"
}}

Keep breakdown realistic - don't over-engineer. Focus on logical decomposition.
"""

        try:
            response = client.chat.completions.create(
                model=settings.azure_openai_deployment,
                messages=[{"role": "user", "content": hierarchy_prompt}],
                temperature=0.2
            )
            
            hierarchy_text = response.choices[0].message.content
            
            # Extract JSON
            start_idx = hierarchy_text.find('{')
            end_idx = hierarchy_text.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                hierarchy_json = json.loads(hierarchy_text[start_idx:end_idx])
                
                # Create primary work item
                primary_data = hierarchy_json["primary_work_item"]
                primary_work_item = WorkItemPlan(
                    title=primary_data["title"],
                    description=primary_data["description"],
                    work_item_type=WorkItemType(primary_data["work_item_type"]),
                    target_repository="",  # Filled by repository intelligence
                    parent_id=None,
                    estimated_effort=primary_data["estimated_effort"],
                    acceptance_criteria=primary_data.get("acceptance_criteria", []),
                    dependencies=primary_data.get("dependencies", []),
                    confidence=primary_recommendation.confidence,
                    reasoning=primary_recommendation.reasoning
                )
                
                # Create child work items
                child_items = []
                for child_data in hierarchy_json.get("child_items", []):
                    child_item = WorkItemPlan(
                        title=child_data["title"],
                        description=child_data["description"],
                        work_item_type=WorkItemType(child_data["work_item_type"]),
                        target_repository="",  # Filled by repository intelligence
                        parent_id="PRIMARY",  # Will be actual ID after creation
                        estimated_effort=child_data["estimated_effort"],
                        acceptance_criteria=child_data.get("acceptance_criteria", []),
                        dependencies=child_data.get("dependencies", []),
                        confidence=0.8,  # Child items have slightly lower confidence
                        reasoning=f"Child of {primary_work_item.title}"
                    )
                    child_items.append(child_item)
                
                return HierarchicalPlan(
                    primary_work_item=primary_work_item,
                    child_items=child_items,
                    total_estimated_effort=hierarchy_json.get("total_estimated_effort", "TBD"),
                    complexity_level=primary_recommendation.complexity_level
                )
                
        except Exception as e:
            print(f"Error generating hierarchical plan: {e}")
        
        # Fallback to single item plan
        return await self.plan_hierarchical_work_items(request_text, intent, 
                                                     WorkItemTypeRecommendation(
                                                         work_item_type=primary_recommendation.work_item_type,
                                                         confidence=0.5,
                                                         reasoning="Fallback due to hierarchy generation error",
                                                         scope_indicators=[],
                                                         complexity_level=ComplexityLevel.SIMPLE
                                                     ))
    
    def _generate_title(self, request_text: str, work_item_type: WorkItemType) -> str:
        """Generate appropriate title based on work item type."""
        request_cleaned = request_text.strip().rstrip('.')
        
        if work_item_type == WorkItemType.EPIC:
            if not request_cleaned.lower().startswith('epic'):
                return f"Epic: {request_cleaned}"
            return request_cleaned
        elif work_item_type == WorkItemType.BUG:
            if not any(word in request_cleaned.lower() for word in ['fix', 'bug', 'error']):
                return f"Fix: {request_cleaned}"
            return request_cleaned
        elif work_item_type == WorkItemType.USER_STORY:
            if not request_cleaned.lower().startswith('as a'):
                return f"User Story: {request_cleaned}"
            return request_cleaned
        else:
            return request_cleaned.capitalize()