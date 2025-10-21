"""
Persona detector that determines whether a user request is PM-focused or EA-focused.
Uses keyword analysis, context, and LLM classification for accurate detection.
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from utils.openai_client import client
from utils.json_fence import extract


@dataclass
class PersonaDecision:
    """Result of persona detection analysis."""
    primary_persona: str  # "PM" or "EA"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    cross_persona_needs: bool  # True if request needs info from both personas
    keyword_matches: Dict[str, List[str]]  # Matched keywords per persona
    context_factors: List[str]  # Factors that influenced decision


class PersonaDetector:
    """
    Detects whether user requests are PM-focused, EA-focused, or require both.
    Uses multi-factor analysis for accurate persona routing.
    """

    # PM-focused keywords and phrases
    PM_KEYWORDS = {
        'work_management': ['work item', 'epic', 'feature', 'user story', 'task', 'bug', 'sprint', 'backlog'],
        'team_management': ['team', 'assignment', 'assigned to', 'workload', 'capacity', 'developer', 'tester'],
        'project_tracking': ['status', 'progress', 'timeline', 'milestone', 'deadline', 'release', 'delivery'],
        'azure_devops': ['pull request', 'pr', 'repository', 'build', 'pipeline', 'commit', 'branch'],
        'business_intel': ['health', 'metrics', 'dashboard', 'report', 'analytics', 'insights', 'performance']
    }

    # EA-focused keywords and phrases
    EA_KEYWORDS = {
        'architecture': ['architecture', 'architectural', 'system design', 'design pattern', 'component', 'analyze architecture', 'system architecture'],
        'ea_discovery': ['EA', 'enterprise architecture', 'discover architecture', 'EA discovery', 'discover EA', 'EA objects', 'EA matrix'],
        'integration': ['integration', 'interface', 'api', 'service', 'microservice', 'endpoint'],
        'governance': ['governance', 'compliance', 'standard', 'policy', 'framework', 'guideline'],
        'modeling': ['model', 'diagram', 'blueprint', 'specification', 'documentation', 'capability matrix'],
        'technology': ['technology stack', 'tech stack', 'platform', 'infrastructure', 'capability'],
        'enterprise': ['enterprise', 'domain', 'business capability', 'process', 'workflow', 'capability mapping']
    }

    # Cross-persona indicators (requests that need both perspectives)
    CROSS_PERSONA_INDICATORS = [
        'impact', 'risk', 'dependency', 'roadmap', 'strategy', 'planning', 'assessment'
    ]

    def __init__(self):
        self.client = client
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts" / "shared"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

    def detect_persona(self, user_request: str, context: Optional[Dict[str, Any]] = None) -> PersonaDecision:
        """
        Detect the appropriate persona for a user request.

        Args:
            user_request: Natural language request from user
            context: Optional context from previous interactions

        Returns:
            PersonaDecision with detected persona and reasoning
        """
        context = context or {}

        # Step 1: Keyword analysis
        keyword_analysis = self._analyze_keywords(user_request)

        # Step 2: Context analysis
        context_factors = self._analyze_context(context)

        # Step 3: Calculate initial scores
        pm_score, ea_score = self._calculate_keyword_scores(keyword_analysis)

        # Step 4: Apply context adjustments
        pm_score, ea_score = self._apply_context_adjustments(pm_score, ea_score, context_factors)

        # Step 5: Check for cross-persona needs
        cross_persona_needs = self._detect_cross_persona_needs(user_request, keyword_analysis)

        # Step 6: Determine primary persona and confidence
        if abs(pm_score - ea_score) < 0.2:  # Scores are close, use LLM for disambiguation
            return self._llm_disambiguation(user_request, context, keyword_analysis, context_factors)

        if pm_score > ea_score:
            primary_persona = "PM"
            confidence = min(pm_score / (pm_score + ea_score + 0.01), 0.95)
        else:
            primary_persona = "EA"
            confidence = min(ea_score / (pm_score + ea_score + 0.01), 0.95)

        reasoning = self._generate_reasoning(primary_persona, keyword_analysis, context_factors)

        return PersonaDecision(
            primary_persona=primary_persona,
            confidence=confidence,
            reasoning=reasoning,
            cross_persona_needs=cross_persona_needs,
            keyword_matches=keyword_analysis,
            context_factors=context_factors
        )

    def _analyze_keywords(self, user_request: str) -> Dict[str, List[str]]:
        """Analyze keyword matches for PM and EA personas."""
        request_lower = user_request.lower()

        pm_matches = {}
        ea_matches = {}

        # Check PM keywords
        for category, keywords in self.PM_KEYWORDS.items():
            matches = [kw for kw in keywords if kw in request_lower]
            if matches:
                pm_matches[category] = matches

        # Check EA keywords
        for category, keywords in self.EA_KEYWORDS.items():
            matches = [kw for kw in keywords if kw in request_lower]
            if matches:
                ea_matches[category] = matches

        return {
            'PM': pm_matches,
            'EA': ea_matches
        }

    def _analyze_context(self, context: Dict[str, Any]) -> List[str]:
        """Analyze context factors that might influence persona selection."""
        factors = []

        # Check for recent persona preferences
        if context.get('recent_persona') == 'PM':
            factors.append('recent_pm_context')
        elif context.get('recent_persona') == 'EA':
            factors.append('recent_ea_context')

        # Check for project types in context
        if context.get('preferred_projects'):
            factors.append('has_project_context')

        # Check for ongoing work context
        if context.get('conversation_entries', 0) > 0:
            factors.append('ongoing_conversation')

        return factors

    def _calculate_keyword_scores(self, keyword_analysis: Dict[str, List[str]]) -> Tuple[float, float]:
        """Calculate initial scores based on keyword matches."""
        pm_matches = keyword_analysis['PM']
        ea_matches = keyword_analysis['EA']

        # Weight different categories differently
        pm_weights = {
            'work_management': 1.0,
            'team_management': 0.8,
            'project_tracking': 0.9,
            'azure_devops': 0.7,
            'business_intel': 0.6
        }

        ea_weights = {
            'architecture': 1.0,
            'integration': 0.9,
            'governance': 0.8,
            'modeling': 0.7,
            'technology': 0.8,
            'enterprise': 0.9
        }

        pm_score = sum(len(matches) * pm_weights.get(category, 0.5)
                      for category, matches in pm_matches.items())

        ea_score = sum(len(matches) * ea_weights.get(category, 0.5)
                      for category, matches in ea_matches.items())

        # Normalize scores
        total_score = pm_score + ea_score
        if total_score > 0:
            pm_score = pm_score / total_score
            ea_score = ea_score / total_score
        else:
            # No keyword matches - default slightly toward PM (existing functionality)
            pm_score = 0.6
            ea_score = 0.4

        return pm_score, ea_score

    def _apply_context_adjustments(self, pm_score: float, ea_score: float,
                                  context_factors: List[str]) -> Tuple[float, float]:
        """Apply context-based adjustments to scores."""
        adjustments = {
            'recent_pm_context': (0.1, -0.05),
            'recent_ea_context': (-0.05, 0.1),
            'has_project_context': (0.05, 0.0),
            'ongoing_conversation': (0.0, 0.0)  # No adjustment for ongoing conversation
        }

        for factor in context_factors:
            if factor in adjustments:
                pm_adj, ea_adj = adjustments[factor]
                pm_score = max(0.0, min(1.0, pm_score + pm_adj))
                ea_score = max(0.0, min(1.0, ea_score + ea_adj))

        return pm_score, ea_score

    def _detect_cross_persona_needs(self, user_request: str,
                                   keyword_analysis: Dict[str, List[str]]) -> bool:
        """Detect if request needs information from both personas."""
        request_lower = user_request.lower()

        # Check for cross-persona indicators
        cross_indicators = any(indicator in request_lower for indicator in self.CROSS_PERSONA_INDICATORS)

        # Check if both PM and EA keywords are present
        has_pm_keywords = bool(keyword_analysis['PM'])
        has_ea_keywords = bool(keyword_analysis['EA'])
        both_present = has_pm_keywords and has_ea_keywords

        return cross_indicators or both_present

    def _llm_disambiguation(self, user_request: str, context: Dict[str, Any],
                           keyword_analysis: Dict[str, List[str]],
                           context_factors: List[str]) -> PersonaDecision:
        """Use LLM for disambiguation when keyword analysis is unclear."""
        try:
            prompt_template = self._load_persona_detection_prompt()

            # Format prompt with analysis data
            analysis_data = {
                'keyword_analysis': keyword_analysis,
                'context_factors': context_factors,
                'cross_persona_indicators': self.CROSS_PERSONA_INDICATORS
            }

            prompt = prompt_template.replace("{{user_request}}", user_request)
            prompt = prompt.replace("{{analysis_data}}", json.dumps(analysis_data, indent=2))
            prompt = prompt.replace("{{context}}", json.dumps(context, indent=2))

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a persona detection expert. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=500
            )

            response_text = response.choices[0].message.content
            extracted_json = extract(response_text)

            if extracted_json:
                result = json.loads(extracted_json)
                return PersonaDecision(
                    primary_persona=result['primary_persona'],
                    confidence=result['confidence'],
                    reasoning=result['reasoning'],
                    cross_persona_needs=result.get('cross_persona_needs', False),
                    keyword_matches=keyword_analysis,
                    context_factors=context_factors
                )

        except Exception as e:
            print(f"LLM disambiguation failed: {e}")

        # Fallback to PM if LLM fails
        return PersonaDecision(
            primary_persona="PM",
            confidence=0.5,
            reasoning="LLM disambiguation failed, defaulting to PM",
            cross_persona_needs=False,
            keyword_matches=keyword_analysis,
            context_factors=context_factors
        )

    def _load_persona_detection_prompt(self) -> str:
        """Load the persona detection prompt template."""
        prompt_path = self.prompts_dir / "persona_detection.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8')
        else:
            # Return a basic prompt if file doesn't exist yet
            return """
# Persona Detection

Analyze the user request and determine whether it's PM-focused or EA-focused.

User Request: {{user_request}}
Analysis Data: {{analysis_data}}
Context: {{context}}

Respond with JSON:
{
  "primary_persona": "PM" or "EA",
  "confidence": 0.0-1.0,
  "reasoning": "explanation of decision",
  "cross_persona_needs": true/false
}
"""

    def _generate_reasoning(self, primary_persona: str, keyword_analysis: Dict[str, List[str]],
                          context_factors: List[str]) -> str:
        """Generate human-readable reasoning for the persona decision."""
        reasoning_parts = []

        persona_matches = keyword_analysis[primary_persona]
        if persona_matches:
            categories = list(persona_matches.keys())
            reasoning_parts.append(f"Strong {primary_persona} keywords found: {', '.join(categories)}")

        if context_factors:
            reasoning_parts.append(f"Context factors: {', '.join(context_factors)}")

        if not reasoning_parts:
            reasoning_parts.append(f"Default assignment to {primary_persona}")

        return "; ".join(reasoning_parts)