"""
Insights Engine for Azure DevOps data analysis.
Transforms raw data into actionable business intelligence with patterns, trends, and recommendations.
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import re


@dataclass
class ProjectInsight:
    """Insights about a specific project."""
    project_name: str
    health_score: float  # 0.0 to 1.0
    key_metrics: Dict[str, Any]
    trends: List[str]
    risks: List[str]
    recommendations: List[str]


@dataclass  
class TeamInsight:
    """Insights about team performance and workload."""
    team_members: List[str]
    workload_distribution: Dict[str, int]
    bottlenecks: List[str]
    recommendations: List[str]


@dataclass
class BusinessIntelligence:
    """Complete business intelligence analysis."""
    summary: str
    projects: List[ProjectInsight]
    team_insights: TeamInsight
    overall_recommendations: List[str]
    executive_summary: str


class InsightsEngine:
    """Analyzes Azure DevOps data to generate business insights."""
    
    def __init__(self):
        self.priority_weights = {
            "1": 4,  # Critical
            "2": 3,  # High  
            "3": 2,  # Medium
            "4": 1   # Low
        }
        
        self.state_categories = {
            "active": ["New", "Active", "In Progress", "Committed"],
            "completed": ["Done", "Closed", "Resolved"],
            "blocked": ["Blocked", "On Hold", "Waiting"],
            "removed": ["Removed", "Cancelled"]
        }
    
    def analyze_work_items(self, work_items: List[Dict[str, Any]], 
                          project_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze work items to extract insights."""
        if not work_items:
            return {"summary": "No work items found", "insights": []}
        
        analysis = {
            "total_items": len(work_items),
            "by_type": Counter(),
            "by_state": Counter(), 
            "by_priority": Counter(),
            "by_assignee": Counter(),
            "unassigned_count": 0,
            "high_priority_count": 0,
            "stale_items": [],
            "insights": []
        }
        
        # Analyze each work item
        for item in work_items:
            fields = item.get("fields", {})
            
            # Type analysis
            work_type = fields.get("System.WorkItemType", "Unknown")
            analysis["by_type"][work_type] += 1
            
            # State analysis
            state = fields.get("System.State", "Unknown")
            analysis["by_state"][state] += 1
            
            # Priority analysis
            priority = str(fields.get("Microsoft.VSTS.Common.Priority", "None"))
            analysis["by_priority"][priority] += 1
            
            if priority in ["1", "2"]:
                analysis["high_priority_count"] += 1
            
            # Assignment analysis
            assigned_to = fields.get("System.AssignedTo", "")
            if assigned_to:
                # Extract display name if it's a complex object
                if isinstance(assigned_to, dict):
                    assigned_to = assigned_to.get("displayName", "Unknown")
                elif isinstance(assigned_to, str) and "<" in assigned_to:
                    # Extract name from "John Smith <john@company.com>" format
                    assigned_to = assigned_to.split("<")[0].strip()
                
                analysis["by_assignee"][assigned_to] += 1
            else:
                analysis["unassigned_count"] += 1
            
            # Identify stale items (unchanged for 30+ days)
            changed_date_str = fields.get("System.ChangedDate", "")
            if changed_date_str:
                try:
                    changed_date = datetime.fromisoformat(changed_date_str.replace("Z", "+00:00"))
                    if (datetime.now().replace(tzinfo=changed_date.tzinfo) - changed_date).days > 30:
                        if state in ["Active", "New", "In Progress"]:
                            analysis["stale_items"].append({
                                "id": item.get("id"),
                                "title": fields.get("System.Title", "")[:50],
                                "days_stale": (datetime.now().replace(tzinfo=changed_date.tzinfo) - changed_date).days,
                                "assignee": assigned_to
                            })
                except:
                    pass  # Skip if date parsing fails
        
        # Generate insights
        analysis["insights"] = self._generate_work_item_insights(analysis)
        
        return analysis
    
    def _generate_work_item_insights(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate insights from work item analysis."""
        insights = []
        
        total = analysis["total_items"]
        if total == 0:
            return ["No work items found to analyze"]
        
        # Priority insights
        high_priority_pct = (analysis["high_priority_count"] / total) * 100
        if high_priority_pct > 30:
            insights.append(f" High priority items represent {high_priority_pct:.1f}% of workload - consider prioritization review")
        elif high_priority_pct < 10:
            insights.append(f"🟢 Well-balanced priority distribution ({high_priority_pct:.1f}% high priority)")
        
        # Assignment insights
        unassigned_pct = (analysis["unassigned_count"] / total) * 100
        if unassigned_pct > 20:
            insights.append(f"  {unassigned_pct:.1f}% of items are unassigned - may impact delivery predictability")
        
        # Workload distribution
        if analysis["by_assignee"]:
            assignee_counts = list(analysis["by_assignee"].values())
            if assignee_counts:
                max_items = max(assignee_counts)
                min_items = min(assignee_counts) if len(assignee_counts) > 1 else max_items
                
                if max_items > min_items * 2:
                    heaviest_loaded = max(analysis["by_assignee"].items(), key=lambda x: x[1])
                    insights.append(f"  Uneven workload distribution - {heaviest_loaded[0]} has {heaviest_loaded[1]} items")
        
        # State insights
        active_states = ["New", "Active", "In Progress", "Committed"]
        active_count = sum(analysis["by_state"][state] for state in active_states)
        active_pct = (active_count / total) * 100
        
        if active_pct > 70:
            insights.append(f"🟡 {active_pct:.1f}% of items are in active states - high WIP may impact flow")
        
        # Stale items
        if analysis["stale_items"]:
            stale_count = len(analysis["stale_items"])
            insights.append(f" {stale_count} items haven't been updated in 30+ days - potential blockers")
        
        # Type distribution insights
        if analysis["by_type"]:
            bug_count = analysis["by_type"].get("Bug", 0)
            bug_pct = (bug_count / total) * 100
            
            if bug_pct > 40:
                insights.append(f" Bugs represent {bug_pct:.1f}% of items - quality improvement needed")
            elif bug_pct < 10:
                insights.append(f" Low bug ratio ({bug_pct:.1f}%) indicates good quality")
        
        return insights
    
    def analyze_pull_requests(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze pull requests for development velocity insights."""
        if not prs:
            return {"summary": "No pull requests found", "insights": []}
        
        analysis = {
            "total_prs": len(prs),
            "by_status": Counter(),
            "by_author": Counter(),
            "by_repository": Counter(),
            "recent_activity": [],
            "insights": []
        }
        
        # Analyze each PR
        for pr in prs:
            status = pr.get("status", "unknown")
            analysis["by_status"][status] += 1
            
            author = pr.get("created_by", "Unknown")
            analysis["by_author"][author] += 1
            
            repo = pr.get("repository", "Unknown")
            analysis["by_repository"][repo] += 1
            
            # Track recent activity
            created_date = pr.get("created_date", "")
            if created_date:
                analysis["recent_activity"].append({
                    "title": pr.get("title", "")[:50],
                    "author": author,
                    "status": status,
                    "date": created_date
                })
        
        # Generate PR insights
        analysis["insights"] = self._generate_pr_insights(analysis)
        
        return analysis
    
    def _generate_pr_insights(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate insights from pull request analysis."""
        insights = []
        
        total = analysis["total_prs"]
        if total == 0:
            return ["No pull requests found in the specified timeframe"]
        
        # Status distribution
        completed_count = analysis["by_status"].get("completed", 0)
        active_count = analysis["by_status"].get("active", 0)
        
        if completed_count > 0:
            completion_rate = (completed_count / total) * 100
            insights.append(f" {completion_rate:.1f}% PR completion rate ({completed_count}/{total})")
        
        if active_count > total * 0.5:
            insights.append(f"🟡 {active_count} active PRs may indicate review bottlenecks")
        
        # Author activity
        if analysis["by_author"]:
            top_contributor = max(analysis["by_author"].items(), key=lambda x: x[1])
            insights.append(f" Most active contributor: {top_contributor[0]} ({top_contributor[1]} PRs)")
            
            # Check for contribution distribution
            contributor_counts = list(analysis["by_author"].values())
            if len(contributor_counts) > 1:
                avg_contributions = sum(contributor_counts) / len(contributor_counts)
                if top_contributor[1] > avg_contributions * 2:
                    insights.append(f"  {top_contributor[0]} is carrying heavy load - consider workload balancing")
        
        # Repository activity
        if analysis["by_repository"]:
            most_active_repo = max(analysis["by_repository"].items(), key=lambda x: x[1])
            insights.append(f" Most active repository: {most_active_repo[0]} ({most_active_repo[1]} PRs)")
        
        return insights
    
    def analyze_project_health(self, project_data: Dict[str, Any]) -> ProjectInsight:
        """Analyze overall project health and generate insights."""
        project_name = project_data.get("project", "Unknown Project")
        
        # Extract data components
        work_items = project_data.get("work_items_summary", [])
        repositories = project_data.get("repositories", [])
        recent_items = project_data.get("recent_work_items", [])
        
        # Calculate health score
        health_score = self._calculate_health_score(work_items, recent_items)
        
        # Generate metrics
        key_metrics = {
            "total_work_items": len(work_items),
            "repositories": len(repositories),
            "recent_activity": len(recent_items),
            "health_score": health_score
        }
        
        # Analyze work items for trends and risks
        work_item_analysis = self.analyze_work_items(work_items)
        
        trends = []
        risks = []
        recommendations = []
        
        # Extract trends from recent activity
        if recent_items:
            recent_types = Counter(item.get("fields", {}).get("System.WorkItemType", "Unknown") 
                                 for item in recent_items)
            most_common_type = recent_types.most_common(1)[0] if recent_types else ("Unknown", 0)
            trends.append(f"Recent focus on {most_common_type[0]} items ({most_common_type[1]} created)")
        
        # Identify risks
        if work_item_analysis["unassigned_count"] > len(work_items) * 0.3:
            risks.append("High percentage of unassigned work items")
        
        if work_item_analysis["high_priority_count"] > len(work_items) * 0.4:
            risks.append("Too many high-priority items may indicate scope creep")
        
        if len(work_item_analysis["stale_items"]) > 5:
            risks.append(f"{len(work_item_analysis['stale_items'])} stale items indicate potential blockers")
        
        # Generate recommendations
        if health_score < 0.6:
            recommendations.append("Consider project health review - multiple risk factors identified")
        
        if work_item_analysis["unassigned_count"] > 0:
            recommendations.append(f"Assign owners to {work_item_analysis['unassigned_count']} unassigned items")
        
        if not recent_items:
            recommendations.append("No recent activity detected - verify project is active")
        
        return ProjectInsight(
            project_name=project_name,
            health_score=health_score,
            key_metrics=key_metrics,
            trends=trends,
            risks=risks,
            recommendations=recommendations
        )
    
    def _calculate_health_score(self, work_items: List[Dict], recent_items: List[Dict]) -> float:
        """Calculate a health score (0.0 to 1.0) for a project."""
        if not work_items:
            return 0.0
        
        score = 1.0
        
        # Factor 1: Assignment rate (well-assigned items are healthy)
        assigned_count = sum(1 for item in work_items 
                           if item.get("fields", {}).get("System.AssignedTo", ""))
        assignment_rate = assigned_count / len(work_items)
        score *= (0.5 + assignment_rate * 0.5)  # 0.5 to 1.0 range
        
        # Factor 2: Recent activity (active projects are healthier)
        if recent_items:
            activity_factor = min(len(recent_items) / len(work_items), 0.3) / 0.3  # Cap at 30%
            score *= (0.7 + activity_factor * 0.3)  # 0.7 to 1.0 range
        else:
            score *= 0.5  # Penalize no recent activity
        
        # Factor 3: State distribution (too many active items indicate problems)
        state_counter = Counter(item.get("fields", {}).get("System.State", "Unknown") 
                              for item in work_items)
        active_states = ["New", "Active", "In Progress"]
        active_count = sum(state_counter[state] for state in active_states)
        active_ratio = active_count / len(work_items)
        
        if active_ratio > 0.8:  # Too much WIP
            score *= 0.8
        elif active_ratio < 0.2:  # Too little activity
            score *= 0.9
        
        return max(0.0, min(1.0, score))
    
    def generate_executive_summary(self, projects: List[ProjectInsight], 
                                 overall_data: Dict[str, Any] = None) -> str:
        """Generate an executive summary of all projects."""
        if not projects:
            return "No projects analyzed."
        
        total_projects = len(projects)
        avg_health = sum(p.health_score for p in projects) / total_projects
        
        healthy_projects = sum(1 for p in projects if p.health_score >= 0.7)
        at_risk_projects = sum(1 for p in projects if p.health_score < 0.5)
        
        summary_parts = [
            f" **Portfolio Health**: {avg_health:.1f}/1.0 across {total_projects} projects",
            f" **Healthy**: {healthy_projects} projects",
            f"  **At Risk**: {at_risk_projects} projects"
        ]
        
        # Highlight top concerns
        all_risks = []
        for project in projects:
            for risk in project.risks:
                all_risks.append(f"{project.project_name}: {risk}")
        
        if all_risks:
            summary_parts.append(f" **Top Concerns**: {len(all_risks)} risk factors identified")
        
        # Highlight best performing project
        if projects:
            best_project = max(projects, key=lambda p: p.health_score)
            summary_parts.append(f" **Best Performer**: {best_project.project_name} (health: {best_project.health_score:.1f})")
        
        return " • ".join(summary_parts)
    
    def create_business_intelligence(self, orchestration_results: Dict[str, Any]) -> BusinessIntelligence:
        """Create comprehensive business intelligence from orchestration results."""
        
        # Extract data from orchestration results
        execution_result = orchestration_results.get("execution_result", {})
        results = execution_result.get("results", [])
        
        project_insights = []
        team_data = defaultdict(list)
        
        # Process each result
        for result in results:
            tool = result.get("tool", "")
            data = result.get("data", {})
            
            if not result.get("success", False):
                continue
            
            if tool == "batch_project_overview" and "project_overviews" in data:
                # Process project overviews
                for project_name, overview in data["project_overviews"].items():
                    if "error" not in overview:
                        insight = self.analyze_project_health(overview)
                        project_insights.append(insight)
            
            elif tool == "get_work_items" and "work_items" in data:
                # Process work items for team analysis
                work_items = data["work_items"]
                for item in work_items:
                    assignee = item.get("fields", {}).get("System.AssignedTo", "")
                    if assignee:
                        if isinstance(assignee, dict):
                            assignee = assignee.get("displayName", "Unknown")
                        team_data[assignee].append(item)
        
        # Generate team insights
        team_insight = self._create_team_insights(team_data)
        
        # Create overall summary
        if project_insights:
            executive_summary = self.generate_executive_summary(project_insights)
        else:
            executive_summary = "No project data available for analysis."
        
        # Generate overall recommendations
        overall_recommendations = self._generate_overall_recommendations(project_insights, team_insight)
        
        return BusinessIntelligence(
            summary=f"Analyzed {len(project_insights)} projects with {len(team_data)} team members",
            projects=project_insights,
            team_insights=team_insight,
            overall_recommendations=overall_recommendations,
            executive_summary=executive_summary
        )
    
    def _create_team_insights(self, team_data: Dict[str, List]) -> TeamInsight:
        """Create team insights from work item assignments."""
        if not team_data:
            return TeamInsight(
                team_members=[],
                workload_distribution={},
                bottlenecks=[],
                recommendations=["No team assignment data available"]
            )
        
        workload_distribution = {name: len(items) for name, items in team_data.items()}
        team_members = list(team_data.keys())
        
        bottlenecks = []
        recommendations = []
        
        # Identify workload imbalances
        if len(workload_distribution) > 1:
            max_load = max(workload_distribution.values())
            min_load = min(workload_distribution.values())
            
            if max_load > min_load * 2:
                overloaded = [name for name, load in workload_distribution.items() if load == max_load]
                bottlenecks.append(f"Workload imbalance: {overloaded[0]} has {max_load} items vs {min_load} minimum")
                recommendations.append("Consider redistributing work items to balance team workload")
        
        # Check for team members with too many items
        for name, count in workload_distribution.items():
            if count > 15:
                bottlenecks.append(f"{name} has {count} assigned items - potential capacity issue")
        
        if not bottlenecks:
            recommendations.append("Team workload appears well balanced")
        
        return TeamInsight(
            team_members=team_members,
            workload_distribution=workload_distribution,
            bottlenecks=bottlenecks,
            recommendations=recommendations
        )
    
    def _generate_overall_recommendations(self, projects: List[ProjectInsight], 
                                        team_insight: TeamInsight) -> List[str]:
        """Generate overall recommendations based on all analysis."""
        recommendations = []
        
        if not projects:
            recommendations.append("Set up project monitoring to enable business intelligence analysis")
            return recommendations
        
        # Health-based recommendations
        unhealthy_projects = [p for p in projects if p.health_score < 0.5]
        if unhealthy_projects:
            project_names = [p.project_name for p in unhealthy_projects]
            recommendations.append(f"Priority review needed for: {', '.join(project_names)}")
        
        # Common risk patterns
        risk_patterns = Counter()
        for project in projects:
            for risk in project.risks:
                risk_patterns[risk] += 1
        
        if risk_patterns:
            most_common_risk = risk_patterns.most_common(1)[0]
            if most_common_risk[1] > 1:
                recommendations.append(f"Address common issue: {most_common_risk[0]} (affects {most_common_risk[1]} projects)")
        
        # Team recommendations
        if team_insight.bottlenecks:
            recommendations.append("Address team workload bottlenecks to improve delivery predictability")
        
        # Process recommendations
        all_project_recommendations = []
        for project in projects:
            all_project_recommendations.extend(project.recommendations)
        
        if all_project_recommendations:
            # Find most common recommendations across projects
            rec_counter = Counter(all_project_recommendations)
            top_rec = rec_counter.most_common(1)[0]
            if top_rec[1] > 1:
                recommendations.append(f"Cross-project action: {top_rec[0]} (applies to {top_rec[1]} projects)")
        
        if not recommendations:
            recommendations.append("Continue monitoring - no critical issues identified")
        
        return recommendations