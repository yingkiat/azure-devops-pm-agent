"""
Repository Intelligence Engine for Azure DevOps PM Agent.

This module provides intelligent repository analysis and assignment capabilities
by analyzing repository READMEs, technology stacks, and historical patterns
to make smart work item assignments.

Key Features:
- README content analysis for technology stack detection
- Repository purpose and capability extraction  
- Historical pattern learning from past work item assignments
- Confidence-based repository scoring and ranking
- Smart repository assignment recommendations

Usage:
    analyzer = RepositoryIntelligence(mcp_server)
    contexts = await analyzer.analyze_request_repositories("CREATE", "Build user dashboard", ["MyProject"])
    best_repo = analyzer.get_best_repository_match("dashboard UI components", contexts)

Architecture:
- Fetches repository data via MCP server tools
- Uses AI to analyze README content for tech stack extraction
- Learns from historical work item patterns
- Provides confidence scoring for repository assignments
"""
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from utils.openai_client import client
from utils.settings import settings
from .repository_cache import RepositoryCache


@dataclass
class RepositoryContext:
    """Repository context with intelligence analysis."""
    name: str
    project: str
    tech_stack: List[str]
    purpose: str
    keywords: List[str]
    readme_content: str
    recent_work_items: List[Dict[str, Any]]
    confidence_score: float
    analysis_reasoning: str


class RepositoryIntelligence:
    """
    Intelligent repository analysis and assignment system.
    
    This class analyzes repositories to understand their purpose, technology stack,
    and suitability for different types of work items. It uses README analysis,
    historical patterns, and AI-powered content analysis.
    
    Attributes:
        mcp_server: The MCP server for Azure DevOps API access
        repository_cache: Cache of analyzed repository contexts
    """
    
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        
        # Initialize intelligent cache system
        self.cache = RepositoryCache(cache_dir=".cache", max_age_hours=24 * 7)  # 1 week cache
        
        # Technology patterns for stack detection
        self.tech_patterns = {
            "frontend": {
                "keywords": ["react", "vue", "angular", "html", "css", "javascript", "typescript", "frontend", "ui", "component", "dashboard", "interface"],
                "file_patterns": ["package.json", "webpack.config", "src/components/", "public/", ".tsx", ".jsx"]
            },
            "backend": {
                "keywords": ["api", "server", "backend", "database", "service", "endpoint", "rest", "graphql", "microservice"],
                "file_patterns": ["requirements.txt", "pom.xml", "Dockerfile", "src/main/", "Controllers/", "Services/"]
            },
            "python": {
                "keywords": ["python", "django", "flask", "fastapi", "pandas", "numpy", "pytest"],
                "file_patterns": ["requirements.txt", "setup.py", "pyproject.toml", "*.py"]
            },
            "dotnet": {
                "keywords": ["c#", "csharp", ".net", "dotnet", "asp.net", "blazor", "mvc"],
                "file_patterns": ["*.csproj", "*.sln", "Program.cs", "Startup.cs", "appsettings.json"]
            },
            "javascript": {
                "keywords": ["javascript", "node", "npm", "yarn", "express", "react", "vue"],
                "file_patterns": ["package.json", "*.js", "*.ts", "node_modules/"]
            },
            "mobile": {
                "keywords": ["mobile", "ios", "android", "react native", "flutter", "xamarin", "swift", "kotlin"],
                "file_patterns": ["android/", "ios/", "*.xcodeproj", "pubspec.yaml", "react-native.config.js"]
            },
            "database": {
                "keywords": ["database", "sql", "mongodb", "postgresql", "mysql", "redis", "elasticsearch"],
                "file_patterns": ["*.sql", "migrations/", "schema.sql", "docker-compose.yml"]
            },
            "devops": {
                "keywords": ["devops", "ci/cd", "pipeline", "docker", "kubernetes", "terraform", "ansible"],
                "file_patterns": ["Dockerfile", "docker-compose.yml", "*.yml", ".github/workflows/", "terraform/"]
            }
        }
    
    async def analyze_request_repositories(self, intent: str, request_text: str, projects: List[str]) -> List[RepositoryContext]:
        """
        Analyze all repositories across projects to find best matches for a request.
        
        Args:
            intent: The classified intent (CREATE, QUERY, etc.)
            request_text: The user's natural language request
            projects: List of project names to analyze
            
        Returns:
            List of RepositoryContext objects with confidence scoring
        """
        print(f"Repository Intelligence: Analyzing {len(projects)} projects for request: '{request_text}'")
        all_repositories = []
        
        for project in projects:
            try:
                print(f"Analyzing project: {project}")
                
                # Get all repositories in project
                repos_results = await self.mcp_client.call_tool("get_repositories", {"project": project})
                repos_result = repos_results[0] if repos_results else {"success": False, "error": "No response"}
                
                if repos_result.get("success") and "repositories" in repos_result:
                    repositories = repos_result["repositories"]
                    print(f"   Found {len(repositories)} repositories in {project}")
                    
                    for repo in repositories:
                        repo_name = repo["name"]
                        print(f"   Processing repository: {repo_name}")
                        
                        # Check intelligent cache first
                        context = await self.cache.get_repository_analysis(project, repo_name, mcp_client=self.mcp_client)
                        
                        if context:
                            print(f"      Using cached analysis for {repo_name}")
                        else:
                            print(f"      Analyzing repository {repo_name}...")
                            context = await self._analyze_single_repository(project, repo_name, repo)
                            
                            # Cache the fresh analysis
                            await self.cache.set_repository_analysis(project, repo_name, context, mcp_client=self.mcp_client)
                            
                            print(f"      Analysis complete for {repo_name}")
                            print(f"         Tech Stack: {', '.join(context.tech_stack) if context.tech_stack else 'Unknown'}")
                            print(f"         Purpose: {context.purpose[:80]}{'...' if len(context.purpose) > 80 else ''}")
                            print(f"         README Length: {len(context.readme_content)} chars")
                        
                        # Score relevance to current request
                        old_score = context.confidence_score
                        context.confidence_score = self._score_repository_relevance(context, request_text, intent)
                        print(f"         Relevance Score: {context.confidence_score:.2f}")
                        all_repositories.append(context)
                        
                else:
                    print(f"   ERROR: Failed to get repositories from {project}: {repos_result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                print(f"   ERROR: Error analyzing repositories in project {project}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Sort by confidence score (highest first)
        all_repositories.sort(key=lambda r: r.confidence_score, reverse=True)
        print(f"Repository analysis complete. Top matches:")
        for i, repo in enumerate(all_repositories[:3]):
            print(f"   {i+1}. {repo.name} (score: {repo.confidence_score:.2f}) - {', '.join(repo.tech_stack[:2]) if repo.tech_stack else 'No tech detected'}")
        
        # Show cache performance statistics
        print(f"\nCache Statistics:")
        print(f"  Hit Rate: {self.cache.get_cache_stats().hit_rate:.1f}% ({self.cache.get_cache_stats().cache_hits}/{self.cache.get_cache_stats().total_requests})")
        print(f"  Cached Repositories: {len(self.cache._memory_cache)}")
        
        return all_repositories
    
    async def _analyze_single_repository(self, project: str, repository: str, repo_metadata: Dict[str, Any]) -> RepositoryContext:
        """Analyze a single repository to extract context and capabilities."""
        
        print(f"         Fetching README for {repository}...")
        
        # Get README content
        readme_results = await self.mcp_client.call_tool("get_readme", {
            "project": project,
            "repository": repository
        })
        readme_result = readme_results[0] if readme_results else {"success": False, "error": "No response"}
        
        readme_content = ""
        readme_found = False
        
        if readme_result.get("success") and "content" in readme_result:
            readme_content = readme_result["content"]
            readme_found = True
            print(f"         README found! Length: {len(readme_content)} characters")
            # Show first few lines for debugging
            preview_lines = readme_content.split('\n')[:3]
            for i, line in enumerate(preview_lines):
                if line.strip():
                    print(f"            Line {i+1}: {line[:60]}{'...' if len(line) > 60 else ''}")
        else:
            print(f"         ERROR: README not found: {readme_result.get('error', 'Unknown error')}")
            if 'tried_files' in readme_result:
                print(f"            Tried files: {', '.join(readme_result['tried_files'])}")
        
        # Analyze with AI if README content available
        if readme_content and len(readme_content.strip()) > 50:
            print(f"         Using AI analysis (README has {len(readme_content)} chars)...")
            tech_stack, purpose, keywords, reasoning = await self._ai_analyze_repository(
                repository, readme_content
            )
            print(f"         AI analysis complete")
        else:
            print(f"         Using pattern-based fallback analysis...")
            tech_stack, purpose, keywords, reasoning = self._pattern_analyze_repository(
                repository, repo_metadata
            )
            print(f"         Pattern analysis complete")
        
        return RepositoryContext(
            name=repository,
            project=project,
            tech_stack=tech_stack,
            purpose=purpose,
            keywords=keywords,
            readme_content=readme_content,
            recent_work_items=[],  # TODO: Fetch from historical data
            confidence_score=0.0,  # Will be scored against specific requests
            analysis_reasoning=reasoning
        )
    
    async def _ai_analyze_repository(self, repository: str, readme_content: str) -> Tuple[List[str], str, List[str], str]:
        """Use AI to deeply understand repository capabilities and domain."""
        
        analysis_prompt = f"""
You are an expert software architect analyzing a repository to understand its true purpose and capabilities.

REPOSITORY: {repository}
README CONTENT:
{readme_content[:2000]}

TASK: Analyze this repository to understand:
1. What is the PRIMARY DOMAIN/PURPOSE of this repository?
2. What type of work can this repository handle?
3. Is this an implementation repository or a tooling/management repository?
4. What technologies and capabilities does it provide?

DOMAIN CATEGORIES to consider:
- DATA_WAREHOUSE: Data warehousing, ETL, data transformation, analytics platforms
- DATA_PIPELINE: Data processing pipelines, ingestion, aggregation, ADF, fabric
- DATABASE: Database management, migrations, schemas, data storage
- FRONTEND: User interfaces, web apps, dashboards, React/Angular/Vue
- BACKEND: APIs, services, business logic, authentication, servers
- MOBILE: Mobile applications, React Native, iOS, Android
- DEVOPS: CI/CD, infrastructure, deployment, monitoring, containers
- TOOLING: Development tools, build systems, testing frameworks
- MANAGEMENT: Project management, documentation, business intelligence tools
- PLATFORM: Platform services, shared infrastructure, common services

Respond in JSON format:
{{
    "primary_domain": "DATA_WAREHOUSE",
    "repository_type": "IMPLEMENTATION",
    "capabilities": [
        "Data transformation using DBT",
        "SQL-based data modeling", 
        "Automated data quality checks",
        "Incremental data loading"
    ],
    "tech_stack": ["DBT", "SQL", "Python", "Snowflake"],
    "purpose": "Handles data transformation and modeling for the unified data warehouse using DBT framework",
    "work_types": [
        "Data migration and transformation",
        "Creating data models and schemas", 
        "Implementing ETL pipelines",
        "Data quality validation"
    ],
    "keywords": ["dbt", "data", "warehouse", "transformation", "etl", "sql"],
    "reasoning": "Repository contains DBT project structure with models, transformations, and data pipeline configurations"
}}

IMPORTANT: 
- Be precise about the PRIMARY domain - don't list multiple if there's a clear focus
- Distinguish between IMPLEMENTATION repos (contain actual code/logic) vs TOOLING/MANAGEMENT repos
- Focus on what types of WORK this repo can actually handle
- Extract specific CAPABILITIES, not just technologies
"""

        try:
            response = client.chat.completions.create(
                model=settings.azure_openai_deployment,
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.1
            )
            
            analysis_text = response.choices[0].message.content
            
            # Extract JSON
            start_idx = analysis_text.find('{')
            end_idx = analysis_text.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                analysis_json = json.loads(analysis_text[start_idx:end_idx])
                
                # Store enhanced analysis in the context
                enhanced_purpose = self._format_enhanced_purpose(analysis_json)
                enhanced_keywords = analysis_json.get("keywords", []) + analysis_json.get("work_types", [])
                
                # Debug: Show what AI extracted
                print(f"         🤖 AI Analysis Results for {repository}:")
                print(f"            Domain: {analysis_json.get('primary_domain', 'Unknown')}")
                print(f"            Repo Type: {analysis_json.get('repository_type', 'Unknown')}")
                print(f"            Tech Stack: {analysis_json.get('tech_stack', [])}")
                print(f"            Capabilities: {analysis_json.get('capabilities', [])[:3]}")  # First 3
                print(f"            Work Types: {analysis_json.get('work_types', [])[:3]}")  # First 3
                
                return (
                    analysis_json.get("tech_stack", []),
                    enhanced_purpose,
                    enhanced_keywords,
                    analysis_json.get("reasoning", "AI analysis completed")
                )
                
        except Exception as e:
            print(f"Error in AI repository analysis: {e}")
        
        # Fallback to pattern analysis
        return self._pattern_analyze_repository(repository, {"readme_content": readme_content})
    
    def _format_enhanced_purpose(self, analysis_json: dict) -> str:
        """Format enhanced purpose with domain and capabilities."""
        
        domain = analysis_json.get("primary_domain", "UNKNOWN")
        repo_type = analysis_json.get("repository_type", "UNKNOWN")
        purpose = analysis_json.get("purpose", "")
        capabilities = analysis_json.get("capabilities", [])
        
        # Create rich purpose description
        enhanced_purpose = f"[{domain}] {purpose}"
        
        if capabilities:
            # Add top capabilities
            top_capabilities = capabilities[:3]  # Limit to top 3
            enhanced_purpose += f" | Capabilities: {'; '.join(top_capabilities)}"
        
        return enhanced_purpose
    
    def _pattern_analyze_repository(self, repository: str, repo_metadata: Dict[str, Any]) -> Tuple[List[str], str, List[str], str]:
        """Fallback pattern-based repository analysis."""
        
        repo_name_lower = repository.lower()
        readme_content = repo_metadata.get("readme_content", "").lower()
        combined_text = f"{repo_name_lower} {readme_content}"
        
        detected_tech = []
        detected_keywords = []
        
        # Analyze against tech patterns
        for category, patterns in self.tech_patterns.items():
            matches = 0
            for keyword in patterns["keywords"]:
                if keyword in combined_text:
                    matches += 1
                    detected_keywords.append(keyword)
            
            if matches >= 2:  # Require at least 2 keyword matches
                detected_tech.append(category)
        
        # Generate purpose based on repository name patterns
        purpose = self._infer_purpose_from_name(repository)
        
        reasoning = f"Pattern analysis: detected {len(detected_tech)} tech categories from keywords"
        
        return detected_tech, purpose, detected_keywords, reasoning
    
    
    def _infer_purpose_from_name(self, repository: str) -> str:
        """Infer repository purpose from naming patterns."""
        repo_lower = repository.lower()
        
        if any(word in repo_lower for word in ["frontend", "web", "ui", "client"]):
            return "Frontend web application or user interface components"
        elif any(word in repo_lower for word in ["backend", "api", "service", "server"]):
            return "Backend service or API implementation"  
        elif any(word in repo_lower for word in ["mobile", "app", "ios", "android"]):
            return "Mobile application development"
        elif any(word in repo_lower for word in ["database", "data", "db"]):
            return "Database schema, migrations, or data management"
        elif any(word in repo_lower for word in ["devops", "infra", "deployment", "pipeline"]):
            return "DevOps infrastructure and deployment automation"
        else:
            return f"Software component: {repository}"
    
    def _score_repository_relevance(self, context: RepositoryContext, request_text: str, intent: str) -> float:
        """Score repository relevance using enhanced AI understanding."""
        
        # Extract domain from enhanced purpose
        purpose_lower = context.purpose.lower()
        request_lower = request_text.lower()
        
        # Start with domain matching (high weight)
        domain_score = self._calculate_domain_match_score(purpose_lower, request_lower)
        
        # Check if this is a management/tooling repo (should get low scores for implementation work)
        if self._is_management_repository(purpose_lower):
            return max(0.1, domain_score * 0.2)  # Very low score for management repos
        
        # Capability matching (high weight)
        capability_score = self._calculate_capability_match_score(context.keywords, request_lower)
        
        # Tech stack matching (moderate weight)
        tech_score = 0.0
        for tech in context.tech_stack:
            if tech.lower() in request_lower:
                tech_score += 0.2
        
        # Repository name semantic matching (lower weight)
        name_score = self._calculate_name_match_score(context.name.lower(), request_lower)
        
        # Technology stack matching (high weight)
        tech_stack_score = self._calculate_tech_stack_match(context.tech_stack, request_lower)
        
        # Combine scores with weights
        total_score = (
            domain_score * 0.4 +          # Domain matching is most important
            capability_score * 0.3 +      # Capabilities are very important  
            tech_stack_score * 0.2 +      # Tech stack matching
            name_score * 0.1              # Name matching is least important
        )
        
        return min(1.0, total_score)
    
    def _calculate_tech_stack_match(self, tech_stack: List[str], request: str) -> float:
        """Score based on technology stack matches in request."""
        
        score = 0.0
        request_lower = request.lower()
        
        # Check if request mentions technologies from the tech stack
        for tech in tech_stack:
            tech_lower = tech.lower()
            tech_words = tech_lower.split()
            
            # Handle multi-word technologies like "Azure Data Factory"
            if len(tech_words) > 1:
                # Check if full phrase is in request
                tech_phrase = ' '.join(tech_words)
                if tech_phrase in request_lower:
                    score += 0.6  # High score for full phrase match
                # Check individual significant words
                elif any(word in request_lower for word in tech_words if len(word) > 3):
                    score += 0.4  # Moderate score for partial match
            else:
                # Single word technology - direct match
                if len(tech_lower) > 2 and tech_lower in request_lower:
                    score += 0.5
        
        return min(1.0, score)
    
    def _calculate_domain_match_score(self, purpose: str, request: str) -> float:
        """Score based on domain matching."""
        
        # Define request patterns and their matching domains
        domain_patterns = {
            'DATA_WAREHOUSE': ['warehouse', 'udw', 'transform', 'modeling', 'dbt'],
            'DATA_PIPELINE': ['pipeline', 'adf', 'bring in', 'import', 'ingestion', 'load', 'extract', 'ingest', 'via adf'],
            'DATABASE': ['database', 'schema', 'sql', 'table'],
            'FRONTEND': ['dashboard', 'ui', 'user interface', 'web app', 'frontend'],
            'BACKEND': ['api', 'service', 'backend', 'server'],
            'MOBILE': ['mobile', 'app', 'ios', 'android'],
            'MANAGEMENT': ['project', 'management', 'pm', 'documentation']
        }
        
        # Extract domain from purpose (format: [DOMAIN] ...)
        domain_match = purpose.split(']')[0].replace('[', '') if '[' in purpose else ''
        
        # Score based on request patterns
        max_score = 0.0
        for domain, patterns in domain_patterns.items():
            if domain in domain_match.upper():
                # Check if request matches this domain's patterns
                pattern_matches = sum(1 for pattern in patterns if pattern in request)
                if pattern_matches > 0:
                    score = min(1.0, pattern_matches * 0.3)  # 0.3 per pattern match
                    max_score = max(max_score, score)
        
        return max_score
    
    def _calculate_capability_match_score(self, keywords: List[str], request: str) -> float:
        """Score based on capability and work type matching."""
        
        score = 0.0
        request_lower = request.lower()
        
        # Semantic similarity - let the AI-extracted keywords do the work
        # No hardcoded mappings needed since AI already extracted work_types and capabilities
        
        # Check direct keyword matches (AI has already extracted relevant work_types and capabilities)
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Check for exact matches
            if keyword_lower in request_lower:
                score += 0.4
            
            # Check for partial phrase matches (e.g., "data pipeline" matches "pipeline")
            keyword_words = keyword_lower.split()
            request_words = request_lower.split()
            
            # If keyword has multiple words, check for partial matches
            if len(keyword_words) > 1:
                word_matches = sum(1 for word in keyword_words if word in request_words and len(word) > 3)
                if word_matches > 0:
                    score += (word_matches / len(keyword_words)) * 0.3
            
            # Single word matches for significant terms
            elif len(keyword_lower) > 3 and any(keyword_lower in word for word in request_words):
                score += 0.2
                        
        return min(1.0, score)
    
    def _calculate_name_match_score(self, repo_name: str, request: str) -> float:
        """Score based on repository name semantic matching."""
        
        score = 0.0
        request_words = request.split()
        
        for word in request_words:
            if len(word) > 3 and word in repo_name:
                score += 0.3
            elif any(word in part for part in repo_name.split('-')):
                score += 0.1
                
        return min(1.0, score)
    
    def _is_management_repository(self, purpose: str) -> bool:
        """Check if repository is for management/tooling rather than implementation."""
        
        management_indicators = [
            '[management]', 'project management', 'business intelligence', 
            'documentation', 'pm agent', 'devops agent'
        ]
        
        return any(indicator in purpose for indicator in management_indicators)
    
    def get_best_repository_match(self, request_text: str, repository_contexts: List[RepositoryContext]) -> Optional[RepositoryContext]:
        """Get the best repository match for a request."""
        
        if not repository_contexts:
            return None
        
        # Return highest scoring repository
        return repository_contexts[0]  # Already sorted by confidence
    
    def get_repository_recommendations(self, request_text: str, repository_contexts: List[RepositoryContext], top_n: int = 3) -> List[RepositoryContext]:
        """Get top N repository recommendations for a request."""
        
        return repository_contexts[:top_n]
    
    def clear_cache(self):
        """Clear all repository analysis cache."""
        self.cache.clear_all_cache()
        print("Repository analysis cache cleared")
    
    def get_cache_stats(self):
        """Get repository cache statistics."""
        return self.cache.get_cache_stats()
    
    def print_cache_stats(self):
        """Print detailed cache statistics."""
        self.cache.print_cache_stats()
    
    def list_cached_repositories(self):
        """List all cached repositories with details."""
        return self.cache.list_cached_repositories()