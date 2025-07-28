"""
Structured plan schema following FEEDBACK.md recommendations.
LLM layer emits these structured plans, sync layer processes them.
"""
from __future__ import annotations
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class TaskSpec(BaseModel):
    external_key: str = Field(default_factory=lambda: f"TS-{uuid.uuid4().hex[:8].upper()}")
    title: str
    description: str = ""
    estimated_days: Optional[float] = None


class StorySpec(BaseModel):
    external_key: str = Field(default_factory=lambda: f"US-{uuid.uuid4().hex[:8].upper()}")
    title: str
    description: str = ""
    story_template: str = ""  # Template with {project} placeholder
    tasks: List[TaskSpec] = []
    acceptance_criteria: List[str] = []


class FeatureSpec(BaseModel):
    external_key: str = Field(default_factory=lambda: f"FE-{uuid.uuid4().hex[:8].upper()}")
    title: str
    description: str = ""
    target_projects: List[str] = []  # Hub-spoke: which projects get stories
    stories_per_project: Dict[str, StorySpec] = {}  # Project -> Story mapping
    acceptance_criteria: List[str] = []
    metrics: List[str] = []  # lead_time, defect_leakage, etc.


class EpicSpec(BaseModel):
    external_key: str = Field(default_factory=lambda: f"EP-{uuid.uuid4().hex[:8].upper()}")
    title: str
    description: str = ""
    features: List[FeatureSpec] = []
    business_value: str = ""
    success_metrics: List[str] = []


class StructuredPlan(BaseModel):
    """
    The canonical plan format that LLM emits and sync layer processes.
    Versioned, diffable, and reviewable by humans.
    """
    plan_id: str = Field(default_factory=lambda: f"PLAN-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}")
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    business_goal: str
    epics: List[EpicSpec] = []
    hub_project: str = ""  # Where epics/features live
    spoke_projects: List[str] = []  # Where stories/tasks get fanned out
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PlanDiff(BaseModel):
    """
    Represents changes between current Azure DevOps state and proposed plan.
    Used for diff-first workflow approval.
    """
    plan_id: str
    epics_to_create: List[EpicSpec] = []
    epics_to_update: List[Dict] = []  # {epic_spec, current_state}
    features_to_create: List[FeatureSpec] = []
    features_to_update: List[Dict] = []
    work_items_to_delete: List[int] = []
    
    def has_changes(self) -> bool:
        return bool(
            self.epics_to_create or 
            self.epics_to_update or 
            self.features_to_create or 
            self.features_to_update or 
            self.work_items_to_delete
        )