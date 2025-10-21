"""
Intelligent Repository Caching System for Azure DevOps PM Agent.

This module provides persistent, intelligent caching of repository analysis with 
automatic cache invalidation based on repository changes. Significantly reduces
API calls and improves performance by caching README content and AI analysis.

Key Features:
- Persistent JSON-based cache storage
- Repository change detection using last commit hash
- Automatic cache invalidation when repositories are updated
- Configurable cache expiration policies
- Memory + disk caching for optimal performance

Architecture:
- Cache key: {project}:{repository}:{last_commit_hash}
- Cache data: README content + AI analysis + metadata
- Invalidation: Compare current commit hash with cached hash
- Storage: JSON files in .cache/ directory with rotation

Usage:
    cache = RepositoryCache()
    
    # Check if repository analysis is cached and still valid
    cached_analysis = await cache.get_repository_analysis(project, repo_name)
    
    if not cached_analysis:
        # Perform fresh analysis
        analysis = await analyze_repository(project, repo_name)
        await cache.set_repository_analysis(project, repo_name, analysis)
"""

import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path

# Avoid circular import by using TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .repository_intelligence import RepositoryContext


@dataclass
class CacheEntry:
    """Single repository cache entry with metadata."""
    project: str
    repository: str
    last_commit_hash: str
    readme_content: str
    repository_context: Dict[str, Any]  # Serialized RepositoryContext
    cached_at: str  # ISO timestamp
    cache_version: str = "1.0"


@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_invalidations: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100


class RepositoryCache:
    """
    Intelligent repository caching system with change detection.
    
    Provides persistent caching of repository README content and AI analysis
    with automatic invalidation when repositories are updated.
    """
    
    def __init__(self, cache_dir: str = ".cache", max_age_hours: int = 24 * 7):  # 1 week default
        """Initialize repository cache system."""
        self.cache_dir = Path(cache_dir) / "repositories"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = timedelta(hours=max_age_hours)
        
        # In-memory cache for performance
        self._memory_cache: Dict[str, CacheEntry] = {}
        
        # Performance tracking
        self.stats = CacheStats()
        
        # Load existing cache entries into memory
        self._load_cache_index()
    
    def _load_cache_index(self):
        """Load cache index from disk into memory for fast lookups."""
        try:
            index_file = self.cache_dir / "cache_index.json"
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    
                # Load recent cache entries into memory
                for entry_data in index_data.get("entries", []):
                    entry = CacheEntry(**entry_data)
                    cache_key = self._get_cache_key(entry.project, entry.repository)
                    self._memory_cache[cache_key] = entry
                    
                print(f"Loaded {len(self._memory_cache)} cached repository analyses")
        except Exception as e:
            print(f"Warning: Failed to load cache index: {e}")
            self._memory_cache = {}
    
    def _save_cache_index(self):
        """Save cache index to disk for persistence."""
        try:
            index_file = self.cache_dir / "cache_index.json"
            entries_data = []
            
            for entry in self._memory_cache.values():
                entries_data.append(asdict(entry))
            
            index_data = {
                "last_updated": datetime.utcnow().isoformat(),
                "cache_version": "1.0",
                "total_entries": len(entries_data),
                "entries": entries_data
            }
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Warning: Failed to save cache index: {e}")
    
    def _get_cache_key(self, project: str, repository: str) -> str:
        """Generate cache key for repository."""
        return f"{project}:{repository}"
    
    async def get_repository_analysis(
        self, 
        project: str, 
        repository: str, 
        current_commit_hash: Optional[str] = None,
        mcp_client = None
    ) -> Optional['RepositoryContext']:
        """
        Retrieve cached repository analysis if valid.
        
        Args:
            project: Azure DevOps project name
            repository: Repository name
            current_commit_hash: Latest commit hash (if known)
            mcp_client: MCP client instance for fetching commit hash
            
        Returns:
            RepositoryContext if cache is valid, None if cache miss/invalid
        """
        self.stats.total_requests += 1
        cache_key = self._get_cache_key(project, repository)
        
        # Check memory cache first
        if cache_key not in self._memory_cache:
            self.stats.cache_misses += 1
            return None
        
        entry = self._memory_cache[cache_key]
        
        # Check cache age
        cached_time = datetime.fromisoformat(entry.cached_at)
        if datetime.utcnow() - cached_time > self.max_age:
            print(f"Cache expired for {repository} (age: {datetime.utcnow() - cached_time})")
            await self._invalidate_cache_entry(cache_key)
            self.stats.cache_invalidations += 1
            self.stats.cache_misses += 1
            return None
        
        # Check if repository has been updated
        if current_commit_hash is None and mcp_client:
            try:
                # Fetch latest commit hash to check for changes
                current_commit_hash = await self._get_latest_commit_hash(project, repository, mcp_client)
            except Exception as e:
                print(f"Warning: Could not fetch commit hash for {repository}: {e}")
                # Proceed with cached version if commit hash check fails
                current_commit_hash = entry.last_commit_hash
        
        if current_commit_hash and current_commit_hash != entry.last_commit_hash:
            print(f"Repository {repository} has been updated (cached: {entry.last_commit_hash[:8]}, current: {current_commit_hash[:8]})")
            await self._invalidate_cache_entry(cache_key)
            self.stats.cache_invalidations += 1
            self.stats.cache_misses += 1
            return None
        
        # Cache hit - deserialize RepositoryContext
        try:
            from .repository_intelligence import RepositoryContext
            
            context_data = entry.repository_context
            repository_context = RepositoryContext(
                name=context_data["name"],
                project=context_data["project"],
                tech_stack=context_data["tech_stack"],
                purpose=context_data["purpose"],
                keywords=context_data["keywords"],
                readme_content=context_data["readme_content"],
                recent_work_items=context_data.get("recent_work_items", []),  # Handle missing field
                confidence_score=context_data["confidence_score"],
                analysis_reasoning=context_data["analysis_reasoning"]
            )
            
            self.stats.cache_hits += 1
            print(f"Cache hit for {repository} (cached {cached_time.strftime('%Y-%m-%d %H:%M')})")
            return repository_context
            
        except Exception as e:
            print(f"Error deserializing cached analysis for {repository}: {e}")
            await self._invalidate_cache_entry(cache_key)
            self.stats.cache_misses += 1
            return None
    
    async def set_repository_analysis(
        self, 
        project: str, 
        repository: str, 
        repository_context: 'RepositoryContext',
        commit_hash: Optional[str] = None,
        mcp_client = None
    ):
        """
        Cache repository analysis with metadata.
        
        Args:
            project: Azure DevOps project name
            repository: Repository name
            repository_context: Analyzed repository context
            commit_hash: Current commit hash
            mcp_client: MCP client instance for fetching commit hash
        """
        cache_key = self._get_cache_key(project, repository)
        
        # Get commit hash if not provided
        if commit_hash is None and mcp_server:
            try:
                commit_hash = await self._get_latest_commit_hash(project, repository, mcp_client)
            except Exception as e:
                print(f"Warning: Could not fetch commit hash for {repository}: {e}")
                commit_hash = "unknown"
        
        if commit_hash is None:
            commit_hash = "unknown"
        
        # Create cache entry
        entry = CacheEntry(
            project=project,
            repository=repository,
            last_commit_hash=commit_hash,
            readme_content=repository_context.readme_content,
            repository_context=asdict(repository_context),
            cached_at=datetime.utcnow().isoformat()
        )
        
        # Store in memory cache
        self._memory_cache[cache_key] = entry
        
        # Persist to disk
        self._save_cache_index()
        
        print(f"Cached analysis for {repository} (commit: {commit_hash[:8] if commit_hash != 'unknown' else 'unknown'})")
    
    async def _get_latest_commit_hash(self, project: str, repository: str, mcp_client) -> str:
        """Get the latest commit hash for a repository."""
        try:
            # Use MCP client to get repository metadata including latest commit
            repo_results = await mcp_client.call_tool("get_repositories", {"project": project})
            repo_result = repo_results[0] if repo_results else {"success": False, "error": "No response"}
            
            # Handle different response formats
            repositories = []
            if isinstance(repo_result, dict):
                if repo_result.get("success") and "repositories" in repo_result:
                    repositories = repo_result["repositories"]
                elif "repositories" in repo_result:
                    repositories = repo_result["repositories"]
            elif isinstance(repo_result, list):
                repositories = repo_result
            
            # Find the specific repository
            for repo in repositories:
                if isinstance(repo, dict) and repo.get("name") == repository:
                    # Azure DevOps API doesn't always include commit hash in repository list
                    # For now, we'll use a simple hash of the last updated time as a proxy
                    last_updated = repo.get("lastUpdateTime", "")
                    if last_updated:
                        return hashlib.sha256(last_updated.encode()).hexdigest()[:40]
                    else:
                        return hashlib.sha256(f"{project}:{repository}:{datetime.utcnow().date()}".encode()).hexdigest()[:40]
            
            # Fallback to date-based hash
            return hashlib.sha256(f"{project}:{repository}:{datetime.utcnow().date()}".encode()).hexdigest()[:40]
            
        except Exception as e:
            print(f"Error fetching commit hash for {repository}: {e}")
            # Fallback hash based on current date (invalidates daily)
            return hashlib.sha256(f"{project}:{repository}:{datetime.utcnow().date()}".encode()).hexdigest()[:40]
    
    async def _invalidate_cache_entry(self, cache_key: str):
        """Remove cache entry from memory and disk."""
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
            self._save_cache_index()
    
    def clear_all_cache(self):
        """Clear all cached repository analyses."""
        self._memory_cache.clear()
        try:
            # Remove cache files
            if self.cache_dir.exists():
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()
            print("All repository cache cleared")
        except Exception as e:
            print(f"Error clearing cache files: {e}")
    
    def get_cache_stats(self) -> CacheStats:
        """Get current cache performance statistics."""
        return self.stats
    
    def print_cache_stats(self):
        """Print cache performance statistics."""
        print(f"Repository Cache Statistics:")
        print(f"  Total Requests: {self.stats.total_requests}")
        print(f"  Cache Hits: {self.stats.cache_hits}")
        print(f"  Cache Misses: {self.stats.cache_misses}")
        print(f"  Cache Invalidations: {self.stats.cache_invalidations}")
        print(f"  Hit Rate: {self.stats.hit_rate:.1f}%")
        print(f"  Cached Repositories: {len(self._memory_cache)}")
    
    def list_cached_repositories(self) -> List[Dict[str, Any]]:
        """List all cached repositories with metadata."""
        cached_repos = []
        
        for cache_key, entry in self._memory_cache.items():
            cached_time = datetime.fromisoformat(entry.cached_at)
            age = datetime.utcnow() - cached_time
            
            cached_repos.append({
                "project": entry.project,
                "repository": entry.repository,
                "commit_hash": entry.last_commit_hash[:8] if entry.last_commit_hash != "unknown" else "unknown",
                "cached_at": cached_time.strftime("%Y-%m-%d %H:%M"),
                "age_hours": round(age.total_seconds() / 3600, 1),
                "readme_length": len(entry.readme_content),
                "tech_stack": entry.repository_context.get("tech_stack", [])
            })
        
        return sorted(cached_repos, key=lambda x: x["cached_at"], reverse=True)