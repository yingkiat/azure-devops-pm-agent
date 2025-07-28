"""
Business request classifier using LLM-based prompts.
Replaces hardcoded text matching with intelligent classification.
"""
from __future__ import annotations
from typing import Dict, Any, List
from pathlib import Path
import json
from dataclasses import dataclass

from utils.openai_client import client
from utils.json_fence import extract
from .page_reader import BusinessRequest


@dataclass
class ClassifiedRequest:
    """A business request with LLM classification results."""
    request_type: str  # pull_requests, work_items, sprint_progress
    confidence: float
    time_range_days: int
    filters: Dict[str, Any]
    reasoning: str
    original_request: BusinessRequest


class BusinessRequestClassifier:
    """Classifies business requests using LLM prompts."""
    
    def __init__(self):
        self.client = client
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    
    def load_prompt(self, prompt_name: str) -> str:
        """Load a prompt template from the prompts directory."""
        prompt_path = self.prompts_dir / f"{prompt_name}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")
        
        return prompt_path.read_text(encoding='utf-8')
    
    def classify_request(self, request: BusinessRequest, projects: List[str] = None) -> ClassifiedRequest:
        """Classify a business request using LLM."""
        
        # Load and prepare the prompt
        prompt_template = self.load_prompt("classify_business_request")
        
        # Format the prompt with request details
        prompt = prompt_template.replace("{{title}}", request.title)
        prompt = prompt.replace("{{description}}", request.description)
        prompt = prompt.replace("{{projects}}", ", ".join(projects or request.projects or []))
        
        # Get classification from LLM
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a business intelligence classifier. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            # Extract JSON from response
            response_text = response.choices[0].message.content
            extracted_json = extract(response_text)
            classification_data = json.loads(extracted_json)
            
            if not classification_data:
                raise ValueError("No valid JSON found in LLM response")
            
            # Validate required fields
            required_fields = ["request_type", "confidence", "time_range_days", "filters", "reasoning"]
            for field in required_fields:
                if field not in classification_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create classified request
            return ClassifiedRequest(
                request_type=classification_data["request_type"],
                confidence=float(classification_data["confidence"]),
                time_range_days=int(classification_data["time_range_days"]),
                filters=classification_data["filters"],
                reasoning=classification_data["reasoning"],
                original_request=request
            )
            
        except Exception as e:
            # Fallback to simple keyword matching if LLM fails
            print(f"⚠️  LLM classification failed: {e}, falling back to keyword matching")
            return self._fallback_classification(request)
    
    def _fallback_classification(self, request: BusinessRequest) -> ClassifiedRequest:
        """Fallback classification using simple keyword matching."""
        text = (request.title + " " + request.description).lower()
        
        if "pull request" in text or " pr " in text:
            request_type = "pull_requests"
        elif "sprint" in text or "progress" in text:
            request_type = "sprint_progress"
        elif "issue" in text or "bug" in text or "critical" in text:
            request_type = "work_items"
        else:
            request_type = "work_items"  # Default
        
        return ClassifiedRequest(
            request_type=request_type,
            confidence=0.6,  # Lower confidence for fallback
            time_range_days=7,
            filters={"priority": "all", "status": "all"},
            reasoning="Fallback keyword matching due to LLM failure",
            original_request=request
        )
    
    def classify_all_requests(self, requests: List[BusinessRequest], projects: List[str] = None) -> List[ClassifiedRequest]:
        """Classify multiple business requests."""
        classified = []
        
        for request in requests:
            try:
                classified_request = self.classify_request(request, projects)
                print(f"🤖 Classified '{request.title}' as {classified_request.request_type} (confidence: {classified_request.confidence:.2f})")
                print(f"   💭 Reasoning: {classified_request.reasoning}")
                classified.append(classified_request)
            except Exception as e:
                print(f"❌ Failed to classify request '{request.title}': {e}")
                # Add fallback classification
                classified.append(self._fallback_classification(request))
        
        return classified