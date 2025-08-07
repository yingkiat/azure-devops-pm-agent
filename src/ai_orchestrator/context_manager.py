"""
Context Manager for persistent session memory.
Maintains conversation context, learned information, and user preferences across sessions.
"""
import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class ConversationEntry:
    """A single conversation entry with metadata."""
    timestamp: str
    user_request: str
    intent: str
    success: bool
    key_learnings: Dict[str, Any]
    session_id: str
    ai_response_summary: str = ""
    topic_keywords: List[str] = None
    
    def __post_init__(self):
        if self.topic_keywords is None:
            self.topic_keywords = []


@dataclass
class ConversationSegment:
    """A logical segment of conversation around a specific topic."""
    topic: str
    start_time: str
    end_time: str
    exchanges: List[Dict[str, str]]
    keywords: List[str]
    session_id: str


@dataclass
class ProjectContext:
    """Context about a specific project."""
    name: str
    last_analyzed: str
    health_score: float
    key_repositories: List[str]
    team_members: List[str]
    common_work_types: List[str]
    recent_insights: List[str]


@dataclass
class UserPreferences:
    """User preferences and behavior patterns."""
    preferred_projects: List[str]
    favorite_queries: List[str]
    common_intents: Dict[str, int]  # Intent -> frequency
    preferred_timeframes: Dict[str, int]  # Timeframe -> frequency
    display_preferences: Dict[str, Any]


class ContextManager:
    """Manages persistent context across AI assistant sessions."""
    
    def __init__(self, context_dir: str = "data/context"):
        self.context_dir = Path(context_dir)
        self.context_dir.mkdir(parents=True, exist_ok=True)
        
        self.context_file = self.context_dir / "session_context.json"
        self.projects_file = self.context_dir / "project_contexts.json"
        self.preferences_file = self.context_dir / "user_preferences.json"
        self.conversations_file = self.context_dir / "conversation_history.json"
        
        # In-memory context
        self.current_context = {}
        self.project_contexts = {}
        self.user_preferences = UserPreferences(
            preferred_projects=[],
            favorite_queries=[],
            common_intents=defaultdict(int),
            preferred_timeframes=defaultdict(int),
            display_preferences={}
        )
        self.conversation_history = []
        self.conversation_segments = []  # Topic-based conversation segments
        self.current_session_exchanges = []  # Current session Q&A pairs
        
        # Load existing context
        self._load_context()
    
    def _load_context(self):
        """Load all context data from disk."""
        try:
            # Load session context
            if self.context_file.exists():
                with open(self.context_file, 'r') as f:
                    self.current_context = json.load(f)
            
            # Load project contexts
            if self.projects_file.exists():
                with open(self.projects_file, 'r') as f:
                    project_data = json.load(f)
                    self.project_contexts = {
                        name: ProjectContext(**data) 
                        for name, data in project_data.items()
                    }
            
            # Load user preferences
            if self.preferences_file.exists():
                with open(self.preferences_file, 'r') as f:
                    pref_data = json.load(f)
                    self.user_preferences = UserPreferences(
                        preferred_projects=pref_data.get('preferred_projects', []),
                        favorite_queries=pref_data.get('favorite_queries', []),
                        common_intents=defaultdict(int, pref_data.get('common_intents', {})),
                        preferred_timeframes=defaultdict(int, pref_data.get('preferred_timeframes', {})),
                        display_preferences=pref_data.get('display_preferences', {})
                    )
            
            # Load conversation history (keep only recent entries)
            if self.conversations_file.exists():
                with open(self.conversations_file, 'r') as f:
                    conv_data = json.load(f)
                    self.conversation_history = [
                        ConversationEntry(**entry) for entry in conv_data
                    ]
                    # Keep only last 100 conversations
                    self.conversation_history = self.conversation_history[-100:]
        
        except Exception as e:
            print(f"⚠️  Warning: Failed to load context: {e}")
            # Continue with empty context
    
    def save_context(self):
        """Save all context data to disk."""
        try:
            # Save session context
            with open(self.context_file, 'w') as f:
                json.dump(self.current_context, f, indent=2)
            
            # Save project contexts
            project_data = {
                name: asdict(context) 
                for name, context in self.project_contexts.items()
            }
            with open(self.projects_file, 'w') as f:
                json.dump(project_data, f, indent=2)
            
            # Save user preferences
            pref_data = {
                'preferred_projects': self.user_preferences.preferred_projects,
                'favorite_queries': self.user_preferences.favorite_queries,
                'common_intents': dict(self.user_preferences.common_intents),
                'preferred_timeframes': dict(self.user_preferences.preferred_timeframes),
                'display_preferences': self.user_preferences.display_preferences
            }
            with open(self.preferences_file, 'w') as f:
                json.dump(pref_data, f, indent=2)
            
            # Save conversation history
            conv_data = [asdict(entry) for entry in self.conversation_history]
            with open(self.conversations_file, 'w') as f:
                json.dump(conv_data, f, indent=2)
        
        except Exception as e:
            print(f"⚠️  Warning: Failed to save context: {e}")
    
    def update_session_context(self, key: str, value: Any):
        """Update session context with a key-value pair."""
        self.current_context[key] = value
        self.save_context()
    
    def get_session_context(self, key: str = None) -> Any:
        """Get session context value or entire context."""
        if key is None:
            return self.current_context
        return self.current_context.get(key)
    
    def learn_from_interaction(self, user_request: str, classified_intent: Dict, 
                             execution_result: Dict, session_id: str = None):
        """Learn from a user interaction to improve future responses."""
        
        # Extract learnings
        intent = classified_intent.get('intent', 'UNKNOWN')
        success = execution_result.get('success', False)
        
        # Add to current session exchanges for wiki push context
        ai_summary = self._create_response_summary(execution_result)
        self.current_session_exchanges.append({
            'user_request': user_request,
            'ai_response': ai_summary,
            'timestamp': datetime.utcnow().isoformat(),
            'intent': intent,
            'success': success,
            'full_result': execution_result if success else None
        })
        
        # Keep only recent exchanges (last 20 for current session)
        if len(self.current_session_exchanges) > 20:
            self.current_session_exchanges = self.current_session_exchanges[-20:]
        
        # Update user preferences
        self.user_preferences.common_intents[intent] += 1
        
        # Extract timeframe preferences from request
        timeframe_patterns = {
            'last week': 7,
            'past week': 7,
            'last month': 30,
            'recent': 7,
            'yesterday': 1,
            'today': 1
        }
        
        for pattern, days in timeframe_patterns.items():
            if pattern in user_request.lower():
                self.user_preferences.preferred_timeframes[pattern] += 1
                break
        
        # Learn project preferences from successful interactions
        if success and 'execution_result' in execution_result:
            results = execution_result['execution_result'].get('results', [])
            for result in results:
                if result.get('tool') == 'get_projects' and result.get('success'):
                    projects = result.get('data', {}).get('projects', [])
                    for project in projects:
                        project_name = project.get('name', '')
                        if project_name and project_name not in self.user_preferences.preferred_projects:
                            self.user_preferences.preferred_projects.append(project_name)
        
        # Store conversation entry
        key_learnings = {
            'intent': intent,
            'success': success,
            'projects_involved': self._extract_projects_from_request(user_request),
            'query_patterns': self._extract_query_patterns(user_request)
        }
        
        conversation_entry = ConversationEntry(
            timestamp=datetime.utcnow().isoformat(),
            user_request=user_request,
            intent=intent,
            success=success,
            key_learnings=key_learnings,
            session_id=session_id or "default"
        )
        
        self.conversation_history.append(conversation_entry)
        
        # Keep only recent conversations
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-100:]
        
        self.save_context()
    
    def update_project_context(self, project_name: str, project_data: Dict[str, Any]):
        """Update context for a specific project."""
        
        if project_name not in self.project_contexts:
            self.project_contexts[project_name] = ProjectContext(
                name=project_name,
                last_analyzed=datetime.utcnow().isoformat(),
                health_score=0.0,
                key_repositories=[],
                team_members=[],
                common_work_types=[],
                recent_insights=[]
            )
        
        context = self.project_contexts[project_name]
        context.last_analyzed = datetime.utcnow().isoformat()
        
        # Update from project data
        if 'health_score' in project_data:
            context.health_score = project_data['health_score']
        
        if 'repositories' in project_data:
            repos = [repo.get('name', '') for repo in project_data['repositories']]
            context.key_repositories = repos[:10]  # Keep top 10
        
        if 'work_items_summary' in project_data:
            work_items = project_data['work_items_summary']
            
            # Extract team members
            team_members = set()
            work_types = []
            
            for item in work_items:
                assignee = item.get('fields', {}).get('System.AssignedTo', '')
                if assignee:
                    if isinstance(assignee, dict):
                        assignee = assignee.get('displayName', '')
                    elif '<' in assignee:
                        assignee = assignee.split('<')[0].strip()
                    if assignee:
                        team_members.add(assignee)
                
                work_type = item.get('fields', {}).get('System.WorkItemType', '')
                if work_type:
                    work_types.append(work_type)
            
            context.team_members = list(team_members)[:20]  # Keep top 20
            
            # Find most common work types
            from collections import Counter
            work_type_counts = Counter(work_types)
            context.common_work_types = [wt for wt, _ in work_type_counts.most_common(5)]
        
        self.save_context()
    
    def get_project_context(self, project_name: str) -> Optional[ProjectContext]:
        """Get context for a specific project."""
        return self.project_contexts.get(project_name)
    
    def get_relevant_context(self, user_request: str) -> Dict[str, Any]:
        """Get context relevant to the current user request."""
        relevant_context = {}
        
        # Add session context
        relevant_context.update(self.current_context)
        
        # Add project-specific context if project mentioned
        mentioned_projects = self._extract_projects_from_request(user_request)
        if mentioned_projects:
            project_contexts = {}
            for project_name in mentioned_projects:
                if project_name in self.project_contexts:
                    project_contexts[project_name] = asdict(self.project_contexts[project_name])
            if project_contexts:
                relevant_context['known_projects'] = project_contexts
        
        # Add user preferences
        relevant_context['user_preferences'] = {
            'preferred_projects': self.user_preferences.preferred_projects[:5],
            'common_intents': dict(list(self.user_preferences.common_intents.items())[:5]),
            'preferred_timeframes': dict(list(self.user_preferences.preferred_timeframes.items())[:3])
        }
        
        # Add recent successful patterns
        recent_conversations = [
            conv for conv in self.conversation_history[-10:] 
            if conv.success and conv.intent != 'UNKNOWN'
        ]
        
        if recent_conversations:
            relevant_context['recent_successful_patterns'] = [
                {
                    'intent': conv.intent,
                    'request_pattern': conv.user_request[:50],
                    'timestamp': conv.timestamp
                }
                for conv in recent_conversations
            ]
        
        return relevant_context
    
    def _extract_projects_from_request(self, request: str) -> List[str]:
        """Extract project names mentioned in the request."""
        projects = []
        request_lower = request.lower()
        
        # Check against known projects
        for project_name in self.project_contexts.keys():
            if project_name.lower() in request_lower:
                projects.append(project_name)
        
        # Check against preferred projects
        for project_name in self.user_preferences.preferred_projects:
            if project_name.lower() in request_lower:
                projects.append(project_name)
        
        return list(set(projects))  # Remove duplicates
    
    def _extract_query_patterns(self, request: str) -> List[str]:
        """Extract query patterns from the request."""
        patterns = []
        request_lower = request.lower()
        
        # Common query patterns
        if 'critical' in request_lower or 'high priority' in request_lower:
            patterns.append('high_priority_focus')
        
        if 'assigned to' in request_lower or 'for ' in request_lower:
            patterns.append('person_specific')
        
        if 'last' in request_lower or 'recent' in request_lower:
            patterns.append('time_bounded')
        
        if 'status' in request_lower or 'progress' in request_lower:
            patterns.append('status_inquiry')
        
        if 'create' in request_lower or 'add' in request_lower:
            patterns.append('creation_intent')
        
        return patterns
    
    def get_conversation_summary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a summary of recent conversations."""
        recent = self.conversation_history[-limit:] if limit > 0 else self.conversation_history
        
        return [
            {
                'timestamp': conv.timestamp,
                'request': conv.user_request[:100],
                'intent': conv.intent,
                'success': conv.success
            }
            for conv in recent
        ]
    
    def clear_context(self, keep_preferences: bool = True):
        """Clear context data (useful for testing or reset)."""
        self.current_context = {}
        self.project_contexts = {}
        self.conversation_history = []
        
        if not keep_preferences:
            self.user_preferences = UserPreferences(
                preferred_projects=[],
                favorite_queries=[],
                common_intents=defaultdict(int),
                preferred_timeframes=defaultdict(int),
                display_preferences={}
            )
        
        self.save_context()
    
    def get_context_stats(self) -> Dict[str, Any]:
        """Get statistics about stored context."""
        return {
            'session_keys': len(self.current_context),
            'known_projects': len(self.project_contexts),
            'conversation_entries': len(self.conversation_history),
            'preferred_projects': len(self.user_preferences.preferred_projects),
            'total_interactions': sum(self.user_preferences.common_intents.values()),
            'context_files_size_mb': self._get_context_files_size()
        }
    
    def _get_context_files_size(self) -> float:
        """Get total size of context files in MB."""
        total_size = 0
        for file_path in [self.context_file, self.projects_file, 
                         self.preferences_file, self.conversations_file]:
            if file_path.exists():
                total_size += file_path.stat().st_size
        return round(total_size / (1024 * 1024), 2)
    
    def _create_response_summary(self, execution_result: Dict) -> str:
        """Create a concise summary of the AI response for wiki context."""
        if not execution_result.get('success'):
            return "Request failed"
        
        results = execution_result.get('results', [])
        if not results:
            return "No results"
        
        # Create summary based on successful operations
        summaries = []
        for result in results:
            if not result.get('success'):
                continue
                
            tool = result.get('tool', 'unknown')
            data = result.get('data', {})
            
            if tool == 'get_work_items' and 'count' in data:
                summaries.append(f"Found {data['count']} work items")
            elif tool == 'get_projects' and 'projects' in data:
                summaries.append(f"Found {len(data['projects'])} projects")
            elif tool == 'get_repositories' and 'repositories' in data:
                summaries.append(f"Found {len(data['repositories'])} repositories")
            elif tool == 'get_pull_requests' and 'count' in data:
                summaries.append(f"Found {data['count']} pull requests")
        
        return "; ".join(summaries) if summaries else execution_result.get('summary', 'Operation completed')
    
    def get_wiki_push_content(self, user_request: str) -> List[Dict]:
        """Get content for wiki push based on natural language request."""
        request_lower = user_request.lower()
        
        # Different scope patterns
        if any(phrase in request_lower for phrase in ['push this', 'save this', 'document this']):
            # Just the last meaningful exchange
            return self._get_last_meaningful_exchange()
            
        elif any(phrase in request_lower for phrase in ['push our conversation', 'save our discussion', 'document our chat']):
            # Multiple recent exchanges on same topic
            return self._get_conversation_thread(user_request)
            
        elif 'push everything' in request_lower or 'save all' in request_lower:
            # All recent exchanges
            return self.current_session_exchanges[-5:] if self.current_session_exchanges else []
            
        else:
            # Try to find topic-based content
            return self._get_topic_based_content(user_request)
    
    def _get_last_meaningful_exchange(self) -> List[Dict]:
        """Get the last exchange that had substantial results."""
        for exchange in reversed(self.current_session_exchanges):
            if exchange['success'] and exchange['intent'] in ['QUERY', 'ANALYSIS', 'DISCOVERY']:
                return [exchange]
        
        # Fallback to last exchange
        return self.current_session_exchanges[-1:] if self.current_session_exchanges else []
    
    def _get_conversation_thread(self, request: str) -> List[Dict]:
        """Get exchanges related to a conversation thread."""
        # Extract topic keywords from the request
        keywords = self._extract_topic_keywords(request)
        
        if not keywords:
            # Return last few exchanges if no specific topic
            return self.current_session_exchanges[-3:] if len(self.current_session_exchanges) >= 3 else self.current_session_exchanges
        
        # Find exchanges mentioning these keywords
        relevant_exchanges = []
        for exchange in self.current_session_exchanges:
            exchange_text = f"{exchange['user_request']} {exchange['ai_response']}".lower()
            if any(keyword in exchange_text for keyword in keywords):
                relevant_exchanges.append(exchange)
        
        return relevant_exchanges[-5:] if relevant_exchanges else self.current_session_exchanges[-1:]
    
    def _get_topic_based_content(self, request: str) -> List[Dict]:
        """Get content based on topic keywords in the request."""
        keywords = self._extract_topic_keywords(request)
        
        if not keywords:
            return self._get_last_meaningful_exchange()
        
        # Find most recent exchange matching the keywords
        for exchange in reversed(self.current_session_exchanges):
            exchange_text = f"{exchange['user_request']} {exchange['ai_response']}".lower()
            if any(keyword in exchange_text for keyword in keywords):
                return [exchange]
        
        return self._get_last_meaningful_exchange()
    
    def _extract_topic_keywords(self, request: str) -> List[str]:
        """Extract topic keywords from a wiki push request."""
        request_lower = request.lower()
        
        # Common topic keywords
        topic_keywords = []
        
        # Project/system related
        for project in self.user_preferences.preferred_projects:
            if project.lower() in request_lower:
                topic_keywords.append(project.lower())
        
        # Common technical terms
        tech_terms = ['bug', 'feature', 'epic', 'task', 'pull request', 'pr', 'repository', 'repo',
                     'project', 'health', 'analysis', 'status', 'critical', 'issue']
        
        for term in tech_terms:
            if term in request_lower:
                topic_keywords.append(term)
        
        return topic_keywords