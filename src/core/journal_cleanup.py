"""
AI Journal Cleanup System

Intelligent cleanup that preserves valuable architectural content while removing:
- Test data and mock content
- Temporary deliverables
- Low-value conversations
- Duplicate insights
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass

from .working_journal import WorkingJournal, DeliverableMetadata


@dataclass
class CleanupRule:
    """Rule for determining what content to clean up"""
    name: str
    pattern: str
    reason: str
    severity: int  # 1=low (keep), 5=high (delete immediately)


@dataclass
class ContentAssessment:
    """Assessment of content value"""
    deliverable_id: str
    architectural_value: int  # 1-10 scale
    reasons: List[str]
    should_keep: bool
    cleanup_recommendation: str


class JournalCleanup:
    """
    Intelligent cleanup system for AI journal

    Features:
    - Content quality assessment
    - Architectural value detection
    - Test data removal
    - Automatic scheduling
    - Safe backup before cleanup
    """

    def __init__(self, journal: WorkingJournal):
        self.journal = journal
        self.cleanup_rules = self._initialize_cleanup_rules()

    def _initialize_cleanup_rules(self) -> List[CleanupRule]:
        """Initialize rules for identifying low-value content"""
        return [
            # Test and temporary content
            CleanupRule(
                name="test_content",
                pattern=r"test|testing|demo|mock|sample|tmp|temp",
                reason="Test or temporary content",
                severity=4
            ),
            CleanupRule(
                name="mvp_test_data",
                pattern=r"mvp.*test|test.*mvp|for mvp4|testing mvp",
                reason="MVP testing artifacts",
                severity=5
            ),
            CleanupRule(
                name="filler_content",
                pattern=r"lorem ipsum|placeholder|dummy|example|fake",
                reason="Placeholder or filler content",
                severity=5
            ),

            # Low architectural value patterns
            CleanupRule(
                name="simple_greetings",
                pattern=r"^(hello|hi|hey)[\s\w]*$",
                reason="Simple greeting with no context",
                severity=3
            ),
            CleanupRule(
                name="system_messages",
                pattern=r"system:|error:|debug:|log:",
                reason="System messages and debug output",
                severity=4
            ),

            # Duplicate or redundant content
            CleanupRule(
                name="duplicate_analysis",
                pattern=r"analyze.*platform.*analyze",
                reason="Likely duplicate analysis request",
                severity=3
            ),

            # Short, low-value content
            CleanupRule(
                name="minimal_content",
                pattern=r"^.{1,20}$",
                reason="Very short content with minimal value",
                severity=2
            )
        ]

    def assess_content_value(self, deliverable: DeliverableMetadata, content: str) -> ContentAssessment:
        """
        Assess the architectural value of content

        Returns assessment with recommendation
        """
        architectural_value = 5  # Start with neutral
        reasons = []

        content_lower = content.lower() if content else ""
        title_lower = deliverable.title.lower()

        # Positive value indicators
        if self._contains_architectural_keywords(content_lower):
            architectural_value += 2
            reasons.append("Contains architectural keywords")

        if self._contains_technical_details(content_lower):
            architectural_value += 1
            reasons.append("Contains technical details")

        if len(content) > 500:  # Substantial content
            architectural_value += 1
            reasons.append("Substantial content length")

        if deliverable.type in ["analysis", "architecture", "capability"]:
            architectural_value += 1
            reasons.append("Valuable deliverable type")

        # Negative value indicators
        cleanup_score = 0
        triggered_rules = []

        for rule in self.cleanup_rules:
            if re.search(rule.pattern, content_lower, re.IGNORECASE) or \
               re.search(rule.pattern, title_lower, re.IGNORECASE):
                cleanup_score += rule.severity
                triggered_rules.append(rule.name)
                reasons.append(f"Triggered rule: {rule.reason}")

        # Adjust architectural value based on cleanup rules
        architectural_value -= (cleanup_score / 2)

        # Age factor - older test content is less valuable
        if deliverable.created_at:
            try:
                created_date = datetime.fromisoformat(deliverable.created_at.replace('Z', '+00:00'))
                age_days = (datetime.now() - created_date.replace(tzinfo=None)).days

                if age_days > 7 and cleanup_score > 0:
                    architectural_value -= 1
                    reasons.append("Old content with cleanup triggers")
            except:
                pass

        # Final decision
        should_keep = architectural_value >= 4

        if cleanup_score >= 8:  # High cleanup score
            should_keep = False
            recommendation = "DELETE - High cleanup score"
        elif architectural_value >= 7:
            should_keep = True
            recommendation = "KEEP - High architectural value"
        elif architectural_value <= 2:
            should_keep = False
            recommendation = "DELETE - Low architectural value"
        else:
            recommendation = "REVIEW - Borderline case"

        return ContentAssessment(
            deliverable_id=deliverable.id,
            architectural_value=max(1, min(10, int(architectural_value))),
            reasons=reasons,
            should_keep=should_keep,
            cleanup_recommendation=recommendation
        )

    def _contains_architectural_keywords(self, content: str) -> bool:
        """Check if content contains valuable architectural keywords"""
        arch_keywords = [
            "microservices", "architecture", "api", "database", "security",
            "scalability", "performance", "integration", "workflow", "capability",
            "component", "service", "data flow", "business process", "enterprise",
            "infrastructure", "deployment", "monitoring", "logging", "authentication",
            "authorization", "load balancer", "cache", "queue", "messaging"
        ]

        return any(keyword in content for keyword in arch_keywords)

    def _contains_technical_details(self, content: str) -> bool:
        """Check if content contains technical implementation details"""
        tech_patterns = [
            r"port\s+\d+", r"http[s]?://", r"\.json|\.xml|\.yaml",
            r"REST|GraphQL|gRPC", r"Redis|MongoDB|PostgreSQL|MySQL",
            r"Docker|Kubernetes|AWS|Azure|GCP", r"CI/CD|DevOps",
            r"\w+\.\w+\.\w+",  # Package-like names
            r"[A-Z][a-z]+[A-Z][a-z]+"  # CamelCase (likely class/service names)
        ]

        return any(re.search(pattern, content, re.IGNORECASE) for pattern in tech_patterns)

    def analyze_journal_content(self) -> Dict[str, List[ContentAssessment]]:
        """
        Analyze all journal content and categorize by cleanup recommendation

        Returns categorized assessments
        """
        assessments = {
            "keep": [],
            "delete": [],
            "review": []
        }

        for deliverable_id, metadata in self.journal.deliverables.items():
            # Load content
            _, content = self.journal.get_deliverable(deliverable_id)
            content_str = str(content) if content else ""

            # Assess value
            assessment = self.assess_content_value(metadata, content_str)

            # Categorize
            if "DELETE" in assessment.cleanup_recommendation:
                assessments["delete"].append(assessment)
            elif "KEEP" in assessment.cleanup_recommendation:
                assessments["keep"].append(assessment)
            else:
                assessments["review"].append(assessment)

        return assessments

    def create_cleanup_backup(self) -> str:
        """Create backup before cleanup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = self.journal.journal_dir / "backups" / f"cleanup_backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Copy deliverables
        import shutil

        # Backup deliverables directory
        deliverables_backup = backup_dir / "deliverables"
        if self.journal.deliverables_dir.exists():
            shutil.copytree(self.journal.deliverables_dir, deliverables_backup)

        # Backup context files
        context_backup = backup_dir / "context"
        if self.journal.context_dir.exists():
            shutil.copytree(self.journal.context_dir, context_backup)

        # Create backup manifest
        manifest = {
            "backup_timestamp": timestamp,
            "deliverables_count": len(self.journal.deliverables),
            "backup_reason": "Pre-cleanup backup",
            "source_journal_dir": str(self.journal.journal_dir)
        }

        with open(backup_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)

        return str(backup_dir)

    def execute_cleanup(self, assessments: Dict[str, List[ContentAssessment]],
                       dry_run: bool = True) -> Dict[str, Any]:
        """
        Execute the cleanup based on assessments

        Args:
            assessments: Categorized content assessments
            dry_run: If True, only simulate cleanup without deleting

        Returns:
            Cleanup results summary
        """
        results = {
            "dry_run": dry_run,
            "backup_created": None,
            "deleted_deliverables": [],
            "kept_deliverables": [],
            "errors": []
        }

        to_delete = assessments["delete"]

        if not to_delete:
            results["message"] = "No content identified for cleanup"
            return results

        # Create backup if not dry run
        if not dry_run:
            try:
                backup_path = self.create_cleanup_backup()
                results["backup_created"] = backup_path
            except Exception as e:
                results["errors"].append(f"Backup creation failed: {e}")
                return results

        # Process deletions
        for assessment in to_delete:
            deliverable_id = assessment.deliverable_id

            if dry_run:
                results["deleted_deliverables"].append({
                    "id": deliverable_id,
                    "title": self.journal.deliverables[deliverable_id].title,
                    "reason": assessment.cleanup_recommendation,
                    "architectural_value": assessment.architectural_value
                })
            else:
                try:
                    # Remove from journal
                    metadata = self.journal.deliverables[deliverable_id]

                    # Delete file if it exists
                    file_path = Path(metadata.file_path)
                    if file_path.exists():
                        file_path.unlink()

                    # Remove from tracking
                    del self.journal.deliverables[deliverable_id]

                    # Remove from active context
                    if deliverable_id in self.journal.active_context:
                        self.journal.active_context.remove(deliverable_id)

                    results["deleted_deliverables"].append({
                        "id": deliverable_id,
                        "title": metadata.title,
                        "reason": assessment.cleanup_recommendation
                    })

                except Exception as e:
                    results["errors"].append(f"Failed to delete {deliverable_id}: {e}")

        # Track kept deliverables
        for assessment in assessments["keep"]:
            results["kept_deliverables"].append({
                "id": assessment.deliverable_id,
                "title": self.journal.deliverables[assessment.deliverable_id].title,
                "architectural_value": assessment.architectural_value
            })

        # Save updated journal if not dry run
        if not dry_run and not results["errors"]:
            try:
                self.journal._save_deliverable_index()
                self.journal._save_conversation_context()
            except Exception as e:
                results["errors"].append(f"Failed to save journal updates: {e}")

        return results

    def smart_cleanup(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Perform intelligent cleanup of the journal

        Args:
            dry_run: If True, only simulate without making changes

        Returns:
            Comprehensive cleanup report
        """
        # Analyze content
        assessments = self.analyze_journal_content()

        # Execute cleanup
        cleanup_results = self.execute_cleanup(assessments, dry_run)

        # Create comprehensive report
        report = {
            "timestamp": datetime.now().isoformat(),
            "analysis": {
                "total_deliverables": len(self.journal.deliverables),
                "to_keep": len(assessments["keep"]),
                "to_delete": len(assessments["delete"]),
                "to_review": len(assessments["review"])
            },
            "cleanup_results": cleanup_results,
            "recommendations": []
        }

        # Add recommendations
        if assessments["review"]:
            report["recommendations"].append(
                f"Review {len(assessments['review'])} borderline deliverables manually"
            )

        if len(assessments["delete"]) > len(assessments["keep"]):
            report["recommendations"].append(
                "High proportion of low-value content - consider reviewing content creation patterns"
            )

        return report

    def schedule_cleanup(self, max_age_days: int = 7, max_deliverables: int = 100) -> bool:
        """
        Check if automatic cleanup should be triggered

        Args:
            max_age_days: Trigger cleanup if oldest low-value content is older than this
            max_deliverables: Trigger cleanup if total deliverables exceed this

        Returns:
            True if cleanup should be triggered
        """
        total_deliverables = len(self.journal.deliverables)

        if total_deliverables > max_deliverables:
            return True

        # Check for old low-value content
        assessments = self.analyze_journal_content()
        old_low_value = 0

        for assessment in assessments["delete"]:
            metadata = self.journal.deliverables[assessment.deliverable_id]
            if metadata.created_at:
                try:
                    created_date = datetime.fromisoformat(metadata.created_at.replace('Z', '+00:00'))
                    age_days = (datetime.now() - created_date.replace(tzinfo=None)).days
                    if age_days > max_age_days:
                        old_low_value += 1
                except:
                    pass

        return old_low_value > 5  # Trigger if more than 5 old low-value items