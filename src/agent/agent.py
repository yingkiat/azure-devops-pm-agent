"""
Refactored LLM planner - emits structured plans instead of direct API calls.
Follows FEEDBACK.md two-layer architecture.
"""
from __future__ import annotations
import json, datetime
from pathlib import Path
from utils.openai_client import chat
from utils.json_fence import extract
from utils.settings import settings
from .plan_schema import StructuredPlan, EpicSpec, FeatureSpec, StorySpec, TaskSpec

SYSTEM_PROMPT = """
You are a senior Azure DevOps PM (Agile process). Convert the BUSINESS GOAL into a structured plan.
Return ONLY JSON with this .exact structure:
{
  "business_goal": "the goal text",
  "hub_project": "Portfolio-Hub", 
  "spoke_projects": ["Data-ETL", "APAC-CRM"],
  "epics": [
    {
      "title": "Epic Title",
      "description": "Epic description", 
      "business_value": "Why this epic matters",
      "success_metrics": ["metric1", "metric2"],
      "features": [
        {
          "title": "Feature Title",
          "description": "Feature description",
          "target_projects": ["Data-ETL", "APAC-CRM"],
          "acceptance_criteria": ["AC1", "AC2"],
          "metrics": ["lead_time", "defect_leakage"],
          "stories_per_project": {
            "Data-ETL": {
              "title": "Story for Data-ETL team",
              "description": "Story description",
              "story_template": "As Data-ETL team, implement {project} integration",
              "tasks": [
                {"title": "Task 1", "description": "Task desc", "estimated_days": 2},
                {"title": "Task 2", "description": "Task desc", "estimated_days": 1}
              ],
              "acceptance_criteria": ["Story AC1", "Story AC2"]
            },
            "APAC-CRM": {
              "title": "Story for APAC-CRM team", 
              "description": "Story description",
              "story_template": "As APAC-CRM team, implement {project} integration",
              "tasks": [
                {"title": "Task 1", "description": "Task desc", "estimated_days": 3}
              ],
              "acceptance_criteria": ["Story AC1"]
            }
          }
        }
      ]
    }
  ]
}

Guidelines: 6±2 epics; features ≤1 quarter; stories ≤2 sprints; tasks ≤3 days.
"""

def draft_structured_plan(goal: str) -> StructuredPlan:
    """
    LLM generates a structured plan - no direct Azure DevOps API calls.
    Returns a validated StructuredPlan that the sync layer will process.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Business goal:\n{goal.strip()}"},
    ]
    rsp = chat(messages, temperature=0.35)
    raw_plan = json.loads(extract(rsp.choices[0].message.content))
    
    # Convert raw JSON to validated StructuredPlan
    return StructuredPlan(**raw_plan)

def save_structured_plan(plan: StructuredPlan) -> Path:
    """Save structured plan to timestamped file."""
    path = Path("outputs") / f"{plan.plan_id}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(plan.model_dump_json(indent=2))
    return path

# Legacy function for backward compatibility
def draft_plan(goal: str) -> dict:
    """Legacy function - converts new structured plan to old format"""
    structured = draft_structured_plan(goal)
    return structured.model_dump()

def save_plan(plan: dict) -> Path:
    """Legacy function - handles both old and new formats"""
    if "plan_id" in plan:
        # New structured format
        structured = StructuredPlan(**plan)
        return save_structured_plan(structured)
    else:
        # Old format - keep existing behavior
        ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        path = Path("outputs") / f"plan-{ts}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(plan, indent=2))
        return path