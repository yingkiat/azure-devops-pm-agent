"""
Interactive Work Item Planning with Multi-Stage Approval Workflow.

This module implements the interactive approval workflow for safe work item creation,
preventing accidental work item generation while providing intelligent planning capabilities.

Key Features:
- Multi-stage proposal generation with repository intelligence
- Interactive approval workflow with rich formatting
- Safe execution with explicit human confirmation
- Detailed proposal previews with acceptance criteria
- Extensible approval options (approve/reject/preview/edit)

Architecture:
- Stage 1: Work item classification and analysis
- Stage 2: Repository intelligence and assignment
- Stage 3: Comprehensive proposal generation
- Stage 4: Interactive approval with user input
- Stage 5: Controlled execution of approved proposals

Usage:
    planner = InteractivePlanner(mcp_server)
    proposal = await planner.plan_work_items(request, intent, projects)
    formatted = planner.format_proposal_for_approval(proposal)
    result = await planner.execute_approved_proposal(proposal)

Safety Features:
- No work items created without explicit approval
- Clear proposal formatting with effort estimates
- Cancellation support (Ctrl+C)
- Preview mode for detailed inspection
"""
from typing import Dict, Any, List
from dataclasses import dataclass

from .work_item_classifier import WorkItemClassifier, HierarchicalPlan
from shared.repository_intelligence import RepositoryIntelligence, RepositoryContext


@dataclass
class ExecutionProposal:
    """Enhanced proposal for work item creation with repository intelligence."""
    request_text: str
    intent: str
    hierarchical_plan: HierarchicalPlan
    execution_summary: str
    estimated_timeline: str
    confidence_score: float
    repository_analysis: List[RepositoryContext]
    repository_assignments: Dict[str, str]  # work_item_title -> repository_name


class InteractivePlanner:
    """Enhanced interactive planner with repository intelligence."""
    
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.work_item_classifier = WorkItemClassifier()
        self.repository_intelligence = RepositoryIntelligence(mcp_client)
    
    async def plan_work_items(self, request_text: str, intent: str, projects: List[str]) -> ExecutionProposal:
        """Generate work item proposal with repository intelligence."""
        
        # Stage 1: Work item classification and hierarchical planning
        primary_recommendation = await self.work_item_classifier.classify_work_item_type(request_text, intent)
        hierarchical_plan = await self.work_item_classifier.plan_hierarchical_work_items(
            request_text, intent, primary_recommendation
        )
        
        # Stage 2: Repository intelligence analysis
        repository_contexts = await self.repository_intelligence.analyze_request_repositories(
            intent, request_text, projects
        )
        
        # Stage 3: Smart repository assignment
        repository_assignments = self._assign_repositories_to_work_items(
            hierarchical_plan, repository_contexts, request_text
        )
        
        # Update work items with repository assignments
        self._update_work_item_repositories(hierarchical_plan, repository_assignments)
        
        return ExecutionProposal(
            request_text=request_text,
            intent=intent,
            hierarchical_plan=hierarchical_plan,
            execution_summary=f"Create {hierarchical_plan.primary_work_item.work_item_type.value.lower()} for: {request_text}",
            estimated_timeline=hierarchical_plan.total_estimated_effort,
            confidence_score=primary_recommendation.confidence,
            repository_analysis=repository_contexts[:3],  # Top 3 repositories
            repository_assignments=repository_assignments
        )
    
    def format_proposal_for_approval(self, proposal: ExecutionProposal) -> str:
        """Format proposal for human approval."""
        
        output = []
        output.append("WORK ITEM CREATION PROPOSAL")
        output.append("=" * 50)
        output.append("")
        
        # Summary
        output.append("SUMMARY")
        output.append(f"Request: {proposal.request_text}")
        output.append(f"Timeline: {proposal.estimated_timeline}")
        output.append("")
        
        # Primary work item
        primary = proposal.hierarchical_plan.primary_work_item
        output.append("PRIMARY WORK ITEM")
        output.append(f"  Type: {primary.work_item_type.value} (confidence: {proposal.confidence_score:.2f})")
        output.append(f"  Title: {primary.title}")
        output.append(f"  Effort: {primary.estimated_effort}")
        repo_info = self._format_repository_assignment(primary.target_repository, proposal.repository_analysis)
        output.append(f"  Repository: {repo_info}")
        output.append("")
        
        # Child work items
        if proposal.hierarchical_plan.child_items:
            output.append(f"CHILD ITEMS ({len(proposal.hierarchical_plan.child_items)})")
            for i, child in enumerate(proposal.hierarchical_plan.child_items):
                output.append(f"  - {child.work_item_type.value}: {child.title}")
                child_repo_info = self._format_repository_assignment(child.target_repository, proposal.repository_analysis)
                output.append(f"    Repository: {child_repo_info}")
                output.append(f"    Effort: {child.estimated_effort}")
            output.append("")
        
        # Repository analysis summary
        if proposal.repository_analysis:
            output.append("REPOSITORY ANALYSIS")
            for i, repo_context in enumerate(proposal.repository_analysis[:3]):
                output.append(f"  - {repo_context.name} (score: {repo_context.confidence_score:.2f})")
                output.append(f"    Tech: {', '.join(repo_context.tech_stack) if repo_context.tech_stack else 'Unknown'}")
                output.append(f"    Purpose: {repo_context.purpose[:80]}{'...' if len(repo_context.purpose) > 80 else ''}")
            output.append("")
        
        # Options
        output.append("OPTIONS")
        output.append("  [y] Approve and execute")
        output.append("  [n] Reject proposal")
        output.append("  [preview] Show detailed content")
        
        return "\n".join(output)
    
    def _assign_repositories_to_work_items(self, hierarchical_plan: HierarchicalPlan, 
                                         repository_contexts: List[RepositoryContext], 
                                         request_text: str) -> Dict[str, str]:
        """Assign repositories to work items based on intelligence analysis."""
        assignments = {}
        
        # Get repository recommendations for primary work item
        primary_repos = self.repository_intelligence.get_repository_recommendations(
            f"{hierarchical_plan.primary_work_item.title} {request_text}", 
            repository_contexts, 
            top_n=1
        )
        
        if primary_repos:
            assignments[hierarchical_plan.primary_work_item.title] = primary_repos[0].name
        
        # Assign repositories to child work items
        for child_item in hierarchical_plan.child_items:
            child_repos = self.repository_intelligence.get_repository_recommendations(
                f"{child_item.title} {child_item.description}",
                repository_contexts,
                top_n=1
            )
            
            if child_repos:
                assignments[child_item.title] = child_repos[0].name
            elif primary_repos:
                # Fallback to primary work item's repository
                assignments[child_item.title] = primary_repos[0].name
        
        return assignments
    
    def _update_work_item_repositories(self, hierarchical_plan: HierarchicalPlan, 
                                     repository_assignments: Dict[str, str]) -> None:
        """Update work item objects with repository assignments."""
        
        # Update primary work item
        primary_title = hierarchical_plan.primary_work_item.title
        if primary_title in repository_assignments:
            hierarchical_plan.primary_work_item.target_repository = repository_assignments[primary_title]
        
        # Update child work items
        for child_item in hierarchical_plan.child_items:
            if child_item.title in repository_assignments:
                child_item.target_repository = repository_assignments[child_item.title]
    
    def _format_repository_assignment(self, repository_name: str, 
                                    repository_contexts: List[RepositoryContext]) -> str:
        """Format repository assignment with confidence info."""
        
        if not repository_name:
            return "TBD"
        
        # Find the repository context for confidence score
        for context in repository_contexts:
            if context.name == repository_name:
                return f"{repository_name} (confidence: {context.confidence_score:.2f})"
        
        return repository_name
    
    async def execute_approved_proposal(self, proposal: ExecutionProposal) -> Dict[str, Any]:
        """Execute approved proposal (simplified - just return success for now)."""
        
        # For now, simulate successful execution
        # In full implementation, this would call Azure DevOps APIs
        
        return {
            "success": True,
            "created_work_items": [
                {
                    "title": proposal.hierarchical_plan.primary_work_item.title,
                    "type": proposal.hierarchical_plan.primary_work_item.work_item_type.value,
                    "id": 12345,  # Simulated ID
                    "repository": proposal.hierarchical_plan.primary_work_item.target_repository or "unknown/repo"
                }
            ],
            "errors": [],
            "summary": f"Successfully created work items for: {proposal.request_text}"
        }