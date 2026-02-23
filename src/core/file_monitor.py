"""
Smart File Monitoring and Caching System

Provides intelligent change detection and caching for ea_inputs/ directory,
allowing the AI to process only NEW/MODIFIED files and skip unchanged content.
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class FileInfo:
    """Information about a tracked file"""
    file_path: str
    checksum: str
    size: int
    last_modified: float
    last_processed: Optional[str] = None
    insights_extracted: List[str] = None
    discovered_elements: Optional[Dict[str, List[str]]] = None  # NEW: Track what this file discovered
    error_count: int = 0

    def __post_init__(self):
        if self.insights_extracted is None:
            self.insights_extracted = []
        if self.discovered_elements is None:
            self.discovered_elements = {}


@dataclass
class ChangeSet:
    """Set of file changes detected"""
    new_files: List[str]
    modified_files: List[str]
    deleted_files: List[str]
    unchanged_files: List[str]
    total_files: int
    efficiency_gain: float  # Percentage of files skipped


class FileChangeMonitor:
    """
    Intelligent file change detection and caching system

    Features:
    - Checksum-based change detection
    - Processing result caching
    - Incremental workload calculation
    - Performance metrics tracking
    """

    def __init__(self, journal_dir: str = "ai_journal"):
        self.journal_dir = Path(journal_dir)
        self.context_dir = self.journal_dir / "context"
        self.tracking_file = self.context_dir / "file_tracking.json"

        # Runtime state
        self.tracked_files: Dict[str, FileInfo] = {}
        self.processing_stats = {
            "total_runs": 0,
            "total_files_processed": 0,
            "total_files_skipped": 0,
            "cache_hit_rate": 0.0
        }

        self._ensure_structure()
        self._load_tracking_data()

    def _ensure_structure(self):
        """Ensure directory structure exists"""
        self.context_dir.mkdir(parents=True, exist_ok=True)

    def detect_changes(self, directory: str,
                      file_patterns: List[str] = None) -> ChangeSet:
        """
        Detect file changes in directory since last run

        Args:
            directory: Directory to monitor (e.g., "ea_inputs")
            file_patterns: File extensions to monitor (e.g., [".txt", ".md", ".json"])

        Returns:
            ChangeSet with new, modified, deleted, and unchanged files
        """
        if file_patterns is None:
            file_patterns = [".txt", ".md", ".json", ".csv", ".xml", ".yaml", ".yml", ".xlsx", ".xls"]

        directory_path = Path(directory)
        if not directory_path.exists():
            return ChangeSet([], [], [], [], 0, 0.0)

        # Get current files in directory
        current_files = {}
        for file_path in directory_path.rglob("*"):
            if file_path.is_file() and any(file_path.suffix.lower() == ext for ext in file_patterns):
                try:
                    # Try to get relative path from current working directory
                    rel_path = str(file_path.relative_to(Path.cwd()))
                except ValueError:
                    # If that fails, use relative to the directory being monitored
                    try:
                        rel_path = str(directory_path / file_path.relative_to(directory_path.resolve()))
                    except ValueError:
                        # Last resort: use absolute path
                        rel_path = str(file_path.resolve())

                current_files[rel_path] = self._get_file_info(file_path)

        # Compare with tracked files
        new_files = []
        modified_files = []
        unchanged_files = []

        for file_path, current_info in current_files.items():
            if file_path not in self.tracked_files:
                # New file
                new_files.append(file_path)
            else:
                tracked_info = self.tracked_files[file_path]
                if (current_info.checksum != tracked_info.checksum or
                    current_info.last_modified != tracked_info.last_modified):
                    # Modified file
                    modified_files.append(file_path)
                else:
                    # Unchanged file
                    unchanged_files.append(file_path)

        # Find deleted files
        deleted_files = [
            file_path for file_path in self.tracked_files.keys()
            if file_path not in current_files and file_path.startswith(str(directory_path))
        ]

        # Calculate efficiency
        total_files = len(current_files)
        files_to_process = len(new_files) + len(modified_files)
        files_skipped = len(unchanged_files)
        efficiency_gain = (files_skipped / total_files * 100) if total_files > 0 else 0.0

        # Update tracking data, preserving processed metadata for unchanged files
        for file_path, file_info in current_files.items():
            if file_path in self.tracked_files:
                existing = self.tracked_files[file_path]
                if file_info.checksum == existing.checksum:
                    file_info.last_processed = existing.last_processed
                    file_info.insights_extracted = existing.insights_extracted
                    file_info.discovered_elements = existing.discovered_elements
                    file_info.error_count = existing.error_count
            self.tracked_files[file_path] = file_info

        # Remove deleted files from tracking
        for file_path in deleted_files:
            if file_path in self.tracked_files:
                del self.tracked_files[file_path]

        # Update stats
        self._update_processing_stats(files_to_process, files_skipped)

        changeset = ChangeSet(
            new_files=new_files,
            modified_files=modified_files,
            deleted_files=deleted_files,
            unchanged_files=unchanged_files,
            total_files=total_files,
            efficiency_gain=efficiency_gain
        )

        self._save_tracking_data()
        return changeset

    def mark_processed(self, file_path: str,
                      insights: List[str] = None,
                      discovered_elements: Dict[str, List[str]] = None,
                      success: bool = True):
        """
        Mark a file as processed and cache the results

        Args:
            file_path: Path to processed file
            insights: Extracted insights/keywords for future reference
            discovered_elements: Elements discovered by this file (for content validation)
            success: Whether processing was successful
        """
        if insights is None:
            insights = []
        if discovered_elements is None:
            discovered_elements = {}

        if file_path in self.tracked_files:
            file_info = self.tracked_files[file_path]
            file_info.last_processed = datetime.now().isoformat()
            file_info.insights_extracted = insights
            file_info.discovered_elements = discovered_elements

            if not success:
                file_info.error_count += 1
            else:
                file_info.error_count = 0  # Reset on successful processing

            self._save_tracking_data()

    def get_file_insights(self, file_path: str) -> List[str]:
        """Get cached insights for a file"""
        if file_path in self.tracked_files:
            return self.tracked_files[file_path].insights_extracted.copy()
        return []

    def get_incremental_workload(self, directory: str,
                                  output_dir: str = "archi_inputs",
                                  validate_output: bool = True,
                                  granular_validation: bool = True) -> Dict:
        """
        Get smart processing workload - only files that need processing

        Args:
            directory: Input directory to monitor (e.g., "ea_inputs")
            output_dir: Output directory to validate (e.g., "archi_inputs")
            validate_output: Whether to validate that outputs still exist
            granular_validation: Use per-file content validation (more precise)

        Returns detailed breakdown for efficient processing
        """
        changeset = self.detect_changes(directory)

        # First: Global validation (does output directory exist at all?)
        cache_valid = True
        cache_invalidation_reason = None
        files_needing_reprocessing = []

        if validate_output:
            cache_valid, cache_invalidation_reason = self._validate_output_exists(output_dir)

            if not cache_valid:
                # Output is missing/invalid - mark ALL files as needing processing
                print(f"\n  Global cache invalidated: {cache_invalidation_reason}")
                print(f"    All files will be re-processed to rebuild outputs.")

                # Clear the cache since outputs are gone
                self.clear_cache()

                # Re-detect changes (everything is now "new")
                changeset = self.detect_changes(directory)

            elif granular_validation:
                # Output exists, but validate per-file content
                print(f"\n Performing granular content validation...")

                for file_path in changeset.unchanged_files:
                    file_valid, reason = self._validate_file_outputs_exist(file_path, output_dir)

                    if not file_valid:
                        print(f"     {file_path}: {reason}")
                        files_needing_reprocessing.append(file_path)

                if files_needing_reprocessing:
                    print(f"   Found {len(files_needing_reprocessing)} files with missing outputs")

        # Build workload with granular invalidation
        files_to_process = changeset.new_files + changeset.modified_files + files_needing_reprocessing

        # Remove files_needing_reprocessing from unchanged_files
        truly_unchanged = [f for f in changeset.unchanged_files if f not in files_needing_reprocessing]

        workload = {
            "files_to_process": files_to_process,
            "new_files": changeset.new_files,
            "modified_files": changeset.modified_files,
            "output_invalidated_files": files_needing_reprocessing,  # NEW: Files with missing outputs
            "unchanged_files": truly_unchanged,
            "deleted_files": changeset.deleted_files,
            "total_files": changeset.total_files,
            "files_to_skip": len(truly_unchanged),
            "efficiency_gain_percent": (len(truly_unchanged) / changeset.total_files * 100) if changeset.total_files > 0 else 0.0,
            "processing_required": len(files_to_process),
            "cached_insights": self._get_cached_insights_summary(truly_unchanged) if cache_valid else {},
            "cache_valid": cache_valid,
            "cache_invalidation_reason": cache_invalidation_reason,
            "granular_validation_enabled": granular_validation
        }

        return workload

    def _validate_output_exists(self, output_dir: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that output directory exists and contains valid data

        Returns:
            (is_valid, reason_if_invalid)
        """
        from pathlib import Path

        output_path = Path(output_dir)

        # Check if output directory exists
        if not output_path.exists():
            return False, f"Output directory '{output_dir}' does not exist"

        # Check for required ArchiMate files
        required_files = ["elements.csv", "relations.csv"]
        missing_files = [f for f in required_files if not (output_path / f).exists()]

        if missing_files:
            return False, f"Required output files missing: {', '.join(missing_files)}"

        # Check if elements.csv has data (not just header)
        try:
            import csv
            elements_file = output_path / "elements.csv"
            with open(elements_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)  # Read header
                first_row = next(reader, None)  # Try to read first data row

                if first_row is None:
                    return False, f"Output file '{elements_file}' is empty (no elements)"
        except Exception as e:
            return False, f"Cannot read output file '{elements_file}': {str(e)}"

        # All checks passed
        return True, None

    def _validate_file_outputs_exist(self, file_path: str, output_dir: str = "archi_inputs") -> Tuple[bool, Optional[str]]:
        """
        Validate that a specific file's discovered elements still exist in outputs.

        This enables granular cache invalidation - only reprocess files whose
        outputs are missing, not all files.

        Args:
            file_path: Path to the file to validate
            output_dir: Output directory to check

        Returns:
            (is_valid, reason_if_invalid)
        """
        from pathlib import Path
        import csv

        # Check if we have tracked discovery data for this file
        if file_path not in self.tracked_files:
            return True, None  # No tracking data, assume valid

        file_info = self.tracked_files[file_path]
        discovered_elements = file_info.discovered_elements

        if file_info.last_processed is None:
            return False, "File was tracked but never successfully processed"

        if not discovered_elements:
            return True, None  # No elements tracked, assume valid

        # Check if output files exist
        output_path = Path(output_dir)
        elements_file = output_path / "elements.csv"

        if not elements_file.exists():
            return False, f"Output file missing: {elements_file}"

        # Read existing elements from output
        try:
            existing_names = set()
            with open(elements_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_names.add(row.get('Name', ''))

            # Check if all discovered elements still exist
            missing_elements = []
            for element_type, names in discovered_elements.items():
                for name in names:
                    if name not in existing_names:
                        missing_elements.append(name)

            if missing_elements:
                return False, f"Expected elements missing from outputs: {', '.join(missing_elements[:3])}" + (f" (+{len(missing_elements)-3} more)" if len(missing_elements) > 3 else "")

            return True, None

        except Exception as e:
            return False, f"Cannot validate outputs: {str(e)}"

    def _get_cached_insights_summary(self, unchanged_files: List[str]) -> Dict:
        """Get summary of cached insights from unchanged files"""
        all_insights = []
        processed_files = 0

        for file_path in unchanged_files:
            if file_path in self.tracked_files:
                file_info = self.tracked_files[file_path]
                if file_info.last_processed and file_info.insights_extracted:
                    all_insights.extend(file_info.insights_extracted)
                    processed_files += 1

        # Count unique insights
        unique_insights = list(set(all_insights))

        return {
            "files_with_cached_results": processed_files,
            "total_cached_insights": len(all_insights),
            "unique_cached_insights": len(unique_insights),
            "top_insights": unique_insights[:10]  # Top 10 most common
        }

    def get_processing_stats(self) -> Dict:
        """Get performance statistics"""
        return {
            **self.processing_stats,
            "tracked_files": len(self.tracked_files),
            "files_with_insights": len([
                f for f in self.tracked_files.values()
                if f.last_processed and f.insights_extracted
            ]),
            "files_with_errors": len([
                f for f in self.tracked_files.values()
                if f.error_count > 0
            ])
        }

    def clear_cache(self, older_than_days: int = None):
        """
        Clear cached data

        Args:
            older_than_days: Only clear entries older than N days (None = clear all)
        """
        if older_than_days is None:
            # Clear everything
            self.tracked_files.clear()
        else:
            # Clear only old entries
            cutoff_timestamp = datetime.now().timestamp() - (older_than_days * 24 * 3600)

            files_to_remove = []
            for file_path, file_info in self.tracked_files.items():
                if file_info.last_modified < cutoff_timestamp:
                    files_to_remove.append(file_path)

            for file_path in files_to_remove:
                del self.tracked_files[file_path]

        self._save_tracking_data()

    def _get_file_info(self, file_path: Path) -> FileInfo:
        """Get file information including checksum"""
        try:
            stat = file_path.stat()

            # Calculate MD5 checksum
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)

            # Get safe relative path
            try:
                safe_path = str(file_path.relative_to(Path.cwd()))
            except ValueError:
                safe_path = str(file_path)

            return FileInfo(
                file_path=safe_path,
                checksum=hasher.hexdigest(),
                size=stat.st_size,
                last_modified=stat.st_mtime
            )
        except Exception as e:
            # Return minimal info if file can't be read
            try:
                safe_path = str(file_path.relative_to(Path.cwd()))
            except ValueError:
                safe_path = str(file_path)

            return FileInfo(
                file_path=safe_path,
                checksum="error",
                size=0,
                last_modified=0,
                error_count=1
            )

    def _update_processing_stats(self, files_processed: int, files_skipped: int):
        """Update processing statistics"""
        self.processing_stats["total_runs"] += 1
        self.processing_stats["total_files_processed"] += files_processed
        self.processing_stats["total_files_skipped"] += files_skipped

        total_files = (self.processing_stats["total_files_processed"] +
                      self.processing_stats["total_files_skipped"])

        if total_files > 0:
            self.processing_stats["cache_hit_rate"] = (
                self.processing_stats["total_files_skipped"] / total_files * 100
            )

    def _load_tracking_data(self):
        """Load file tracking data from disk"""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Load tracked files
                self.tracked_files = {
                    file_path: FileInfo(**file_data)
                    for file_path, file_data in data.get("tracked_files", {}).items()
                }

                # Load stats
                self.processing_stats.update(data.get("processing_stats", {}))

            except Exception as e:
                # If loading fails, start fresh
                self.tracked_files = {}

    def _save_tracking_data(self):
        """Save file tracking data to disk"""
        try:
            data = {
                "tracked_files": {
                    file_path: asdict(file_info)
                    for file_path, file_info in self.tracked_files.items()
                },
                "processing_stats": self.processing_stats,
                "last_updated": datetime.now().isoformat()
            }

            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            # Silently fail - don't break the system if we can't save cache
            pass

    def get_file_status(self, file_path: str) -> Optional[Dict]:
        """Get detailed status information for a specific file"""
        if file_path not in self.tracked_files:
            return None

        file_info = self.tracked_files[file_path]
        return {
            "file_path": file_info.file_path,
            "size_kb": round(file_info.size / 1024, 2),
            "last_modified": datetime.fromtimestamp(file_info.last_modified).isoformat(),
            "last_processed": file_info.last_processed,
            "insights_count": len(file_info.insights_extracted),
            "insights": file_info.insights_extracted[:5],  # First 5 insights
            "error_count": file_info.error_count,
            "needs_processing": file_info.last_processed is None or file_info.error_count > 0
        }