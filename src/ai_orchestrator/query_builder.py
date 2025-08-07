"""
Smart WIQL Query Builder
Constructs optimized WIQL queries based on natural language intent and Azure DevOps best practices.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import re


@dataclass
class QueryContext:
    """Context information for building queries."""
    projects: List[str] = None
    person: str = None
    timeframe_days: int = 7
    work_item_types: List[str] = None
    states: List[str] = None
    priority_level: str = None  # "critical", "high", "medium", "low", "all"
    include_closed: bool = False


class SmartWIQLBuilder:
    """
    Builds optimized WIQL queries from natural language intent.
    Uses Azure DevOps domain knowledge for accurate field references.
    """
    
    def __init__(self):
        self.priority_mappings = {
            "critical": "[Microsoft.VSTS.Common.Priority] <= 1",
            "high": "[Microsoft.VSTS.Common.Priority] <= 2", 
            "medium": "[Microsoft.VSTS.Common.Priority] = 3",
            "low": "[Microsoft.VSTS.Common.Priority] = 4",
            "all": ""
        }
        
        self.work_item_type_aliases = {
            "bugs": ["Bug"],
            "stories": ["User Story"], 
            "features": ["Feature"],
            "epics": ["Epic"],
            "tasks": ["Task"],
            "issues": ["Bug", "Issue"],  # Ambiguous - could be bugs or general items
            "backlog": ["Epic", "Feature", "User Story"],
            "work": ["Epic", "Feature", "User Story", "Task", "Bug"]
        }
        
        self.state_aliases = {
            "open": ["New", "Active"],
            "active": ["Active"],
            "closed": ["Closed", "Done", "Resolved"],
            "done": ["Done", "Closed"],
            "new": ["New"],
            "in_progress": ["Active", "In Progress"],
            "all": []  # No filter
        }
    
    def build_work_items_query(self, context: QueryContext, intent_description: str = "") -> str:
        """Build a WIQL query for work items based on context and intent."""
        
        # Start with base SELECT
        select_fields = [
            "[System.Id]",
            "[System.Title]", 
            "[System.WorkItemType]",
            "[System.State]",
            "[System.AssignedTo]",
            "[System.CreatedDate]",
            "[Microsoft.VSTS.Common.Priority]"
        ]
        
        # Add conditional fields based on intent
        if "story points" in intent_description.lower() or "effort" in intent_description.lower():
            select_fields.append("[Microsoft.VSTS.Scheduling.StoryPoints]")
            select_fields.append("[Microsoft.VSTS.Scheduling.Effort]")
        
        if "changed" in intent_description.lower() or "updated" in intent_description.lower():
            select_fields.append("[System.ChangedDate]")
        
        query_parts = [
            f"SELECT {', '.join(select_fields)}",
            "FROM WorkItems",
            "WHERE"
        ]
        
        where_conditions = []
        
        # Project filter (always include for performance)
        if context.projects:
            if len(context.projects) == 1:
                where_conditions.append(f"[System.TeamProject] = '{context.projects[0]}'")
            else:
                project_list = "', '".join(context.projects)
                where_conditions.append(f"[System.TeamProject] IN ('{project_list}')")
        else:
            # Use a placeholder that will be replaced
            where_conditions.append("[System.TeamProject] = @project")
        
        # Work item type filter
        if context.work_item_types:
            if len(context.work_item_types) == 1:
                where_conditions.append(f"[System.WorkItemType] = '{context.work_item_types[0]}'")
            else:
                type_list = "', '".join(context.work_item_types)
                where_conditions.append(f"[System.WorkItemType] IN ('{type_list}')")
        
        # State filter
        if context.states:
            if len(context.states) == 1:
                where_conditions.append(f"[System.State] = '{context.states[0]}'")
            else:
                state_list = "', '".join(context.states)
                where_conditions.append(f"[System.State] IN ('{state_list}')")
        elif not context.include_closed:
            # Default: exclude closed items
            where_conditions.append("[System.State] NOT IN ('Closed', 'Done', 'Resolved', 'Removed')")
        
        # Priority filter
        if context.priority_level and context.priority_level in self.priority_mappings:
            priority_condition = self.priority_mappings[context.priority_level]
            if priority_condition:
                where_conditions.append(priority_condition)
        
        # Person assignment filter
        if context.person:
            # Use CONTAINS for flexible name matching
            where_conditions.append(f"[System.AssignedTo] CONTAINS '{context.person}'")
        
        # Time-based filter
        if context.timeframe_days and context.timeframe_days > 0:
            if "created" in intent_description.lower() or "new" in intent_description.lower():
                where_conditions.append(f"[System.CreatedDate] >= @Today - {context.timeframe_days}")
            elif "updated" in intent_description.lower() or "changed" in intent_description.lower():
                where_conditions.append(f"[System.ChangedDate] >= @Today - {context.timeframe_days}")
        
        # Combine all conditions
        query_parts.append(" AND ".join(where_conditions))
        
        # Add ORDER BY for better results
        if "recent" in intent_description.lower() or context.timeframe_days:
            query_parts.append("ORDER BY [System.CreatedDate] DESC")
        elif context.priority_level:
            query_parts.append("ORDER BY [Microsoft.VSTS.Common.Priority], [System.CreatedDate] DESC")
        else:
            query_parts.append("ORDER BY [System.ChangedDate] DESC")
        
        return " ".join(query_parts)
    
    def build_summary_query(self, context: QueryContext) -> str:
        """Build a query for summary/reporting purposes - simplified without GROUP BY."""
        query_parts = [
            "SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], [System.AssignedTo]",
            "FROM WorkItems",
            "WHERE"
        ]
        
        where_conditions = []
        
        # Project filter
        if context.projects:
            if len(context.projects) == 1:
                where_conditions.append(f"[System.TeamProject] = '{context.projects[0]}'")
            else:
                project_list = "', '".join(context.projects)
                where_conditions.append(f"[System.TeamProject] IN ('{project_list}')")
        else:
            where_conditions.append("[System.TeamProject] = @project")
        
        # Work item type filter
        if context.work_item_types:
            if len(context.work_item_types) == 1:
                where_conditions.append(f"[System.WorkItemType] = '{context.work_item_types[0]}'")
            else:
                type_list = "', '".join(context.work_item_types)
                where_conditions.append(f"[System.WorkItemType] IN ('{type_list}')")
        
        # Exclude closed items for summary unless specifically requested
        if not context.include_closed:
            where_conditions.append("[System.State] NOT IN ('Closed', 'Done', 'Resolved', 'Removed')")
        
        query_parts.append(" AND ".join(where_conditions))
        query_parts.append("ORDER BY [System.ChangedDate] DESC")
        
        return " ".join(query_parts)
    
    def build_team_workload_query(self, context: QueryContext) -> str:
        """Build a query to analyze team workload - simplified without GROUP BY."""
        query_parts = [
            "SELECT [System.Id], [System.Title], [System.AssignedTo], [System.WorkItemType], [System.State]",
            "FROM WorkItems",
            "WHERE"
        ]
        
        where_conditions = []
        
        # Project filter
        if context.projects:
            if len(context.projects) == 1:
                where_conditions.append(f"[System.TeamProject] = '{context.projects[0]}'")
            else:
                project_list = "', '".join(context.projects)
                where_conditions.append(f"[System.TeamProject] IN ('{project_list}')")
        else:
            where_conditions.append("[System.TeamProject] = @project")
        
        # Only active items
        where_conditions.append("[System.State] IN ('New', 'Active', 'In Progress')")
        where_conditions.append("[System.AssignedTo] <> ''")  # Has assignee
        
        query_parts.append(" AND ".join(where_conditions))
        query_parts.append("ORDER BY [System.AssignedTo], [System.ChangedDate] DESC")
        
        return " ".join(query_parts)
    
    def parse_natural_language_to_context(self, request: str, available_projects: List[str] = None) -> QueryContext:
        """Parse natural language request into QueryContext for query building."""
        context = QueryContext()
        request_lower = request.lower()
        
        # Extract work item types
        for alias, types in self.work_item_type_aliases.items():
            if alias in request_lower:
                context.work_item_types = types
                break
        
        # Extract priority level
        if "critical" in request_lower:
            context.priority_level = "critical"
        elif "high priority" in request_lower or "high-priority" in request_lower:
            context.priority_level = "high"
        elif "medium priority" in request_lower:
            context.priority_level = "medium"
        elif "low priority" in request_lower:
            context.priority_level = "low"
        
        # Extract person references
        person_patterns = [
            r"assigned to (\w+)",
            r"for (\w+)",
            r"by (\w+)"
        ]
        for pattern in person_patterns:
            match = re.search(pattern, request_lower)
            if match:
                context.person = match.group(1)
                break
        
        # Extract timeframe
        time_patterns = [
            (r"last (\d+) days?", lambda m: int(m.group(1))),
            (r"past (\d+) days?", lambda m: int(m.group(1))),
            (r"last week", lambda m: 7),
            (r"past week", lambda m: 7), 
            (r"last month", lambda m: 30),
            (r"past month", lambda m: 30),
            (r"yesterday", lambda m: 1),
            (r"today", lambda m: 1),
            (r"recent", lambda m: 7)
        ]
        
        for pattern, extractor in time_patterns:
            match = re.search(pattern, request_lower)
            if match:
                context.timeframe_days = extractor(match)
                break
        
        # Extract state preferences
        for alias, states in self.state_aliases.items():
            if alias in request_lower:
                context.states = states
                break
        
        # Check if closed items should be included
        if "all" in request_lower or "closed" in request_lower or "completed" in request_lower:
            context.include_closed = True
        
        # Try to extract project names from available projects
        if available_projects:
            mentioned_projects = []
            for project in available_projects:
                # Simple word matching - could be enhanced
                project_words = project.lower().split()
                if any(word in request_lower for word in project_words if len(word) > 3):
                    mentioned_projects.append(project)
            
            if mentioned_projects:
                context.projects = mentioned_projects
        
        return context
    
    def get_suggested_queries(self, context: QueryContext) -> Dict[str, str]:
        """Get a set of suggested queries based on context."""
        suggestions = {}
        
        # Basic work items query
        suggestions["work_items"] = self.build_work_items_query(context, "basic work items")
        
        # Summary query
        suggestions["summary"] = self.build_summary_query(context)
        
        # If no specific filters, add some useful variations
        if not context.work_item_types and not context.priority_level:
            # Critical items
            critical_context = QueryContext(
                projects=context.projects,
                priority_level="critical",
                include_closed=False
            )
            suggestions["critical_items"] = self.build_work_items_query(critical_context, "critical items")
            
            # Team workload
            suggestions["team_workload"] = self.build_team_workload_query(context)
        
        return suggestions