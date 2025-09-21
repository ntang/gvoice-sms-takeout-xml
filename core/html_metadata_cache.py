"""
HTML File Metadata Cache for Performance Optimization.

This module provides caching functionality for HTML file metadata to significantly
improve performance on repeat runs while maintaining complete flexibility for
filtering and parameter changes.

The cache stores extracted metadata (phone numbers, timestamps, src elements, etc.)
and uses file modification time for invalidation.
"""

import json
import time
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class HTMLMetadataCache:
    """
    High-performance cache for HTML file metadata with automatic invalidation.
    
    This cache stores extracted metadata from HTML files and uses file modification
    time for cache invalidation. It's designed to be completely safe for use with
    any filtering or parameter changes since it only caches raw extracted data.
    """
    
    def __init__(self, processing_dir: Path, cache_version: str = "1.0"):
        """
        Initialize HTML metadata cache.
        
        Args:
            processing_dir: Directory containing HTML files to cache
            cache_version: Cache format version for compatibility
        """
        self.processing_dir = Path(processing_dir)
        self.cache_dir = self.processing_dir / ".gvoice_cache"
        self.cache_file = self.cache_dir / "html_metadata.json"
        self.cache_version = cache_version
        
        # Initialize cache data structure
        self.cache_data = {
            "cache_version": cache_version,
            "last_updated": time.time(),
            "files": {}
        }
        
        # Create cache directory
        self.cache_dir.mkdir(exist_ok=True)
        
        # Load existing cache
        self._load_cache()
        
        logger.debug(f"HTML metadata cache initialized: {len(self.cache_data['files'])} cached files")
    
    def get_metadata(self, html_file: Path) -> Optional[Dict[str, Any]]:
        """
        Get cached metadata for an HTML file if valid.
        
        Args:
            html_file: Path to HTML file
            
        Returns:
            Cached metadata dict or None if cache miss/invalid
        """
        try:
            file_key = str(html_file.relative_to(self.processing_dir))
            
            if file_key not in self.cache_data["files"]:
                return None
            
            cached_entry = self.cache_data["files"][file_key]
            current_hash = self._compute_file_hash(html_file)
            
            if cached_entry["file_hash"] != current_hash:
                # File changed, invalidate cache entry
                del self.cache_data["files"][file_key]
                logger.debug(f"Cache invalidated for {file_key} (file changed)")
                return None
            
            logger.debug(f"Cache hit for {file_key}")
            return cached_entry["metadata"]
            
        except Exception as e:
            logger.debug(f"Cache lookup failed for {html_file}: {e}")
            return None
    
    def store_metadata(self, html_file: Path, metadata: Dict[str, Any]):
        """
        Store metadata for an HTML file.
        
        Args:
            html_file: Path to HTML file
            metadata: Metadata dict to cache
        """
        try:
            file_key = str(html_file.relative_to(self.processing_dir))
            file_hash = self._compute_file_hash(html_file)
            
            self.cache_data["files"][file_key] = {
                "file_hash": file_hash,
                "metadata": metadata,
                "cached_at": time.time()
            }
            
            logger.debug(f"Cached metadata for {file_key}")
            
            # Auto-save cache every 50 entries for performance and reliability
            if len(self.cache_data["files"]) % 50 == 0:
                self._save_cache()
            
        except Exception as e:
            logger.debug(f"Failed to cache metadata for {html_file}: {e}")
            # Don't fail the operation if caching fails
    
    def update_metadata(self, html_file: Path, metadata_update: Dict[str, Any]):
        """
        Update existing cached metadata for an HTML file.
        
        Args:
            html_file: Path to HTML file
            metadata_update: Metadata fields to update
        """
        try:
            existing_metadata = self.get_metadata(html_file)
            if existing_metadata is not None:
                existing_metadata.update(metadata_update)
                self.store_metadata(html_file, existing_metadata)
            else:
                # No existing cache, store as new
                self.store_metadata(html_file, metadata_update)
                
        except Exception as e:
            logger.debug(f"Failed to update cached metadata for {html_file}: {e}")
    
    def cleanup_stale_entries(self, max_age_days: int = 30):
        """
        Remove cache entries for files that no longer exist or are very old.
        
        Args:
            max_age_days: Maximum age in days for cache entries
        """
        try:
            current_time = time.time()
            stale_threshold = current_time - (max_age_days * 24 * 3600)
            
            stale_keys = []
            for file_key, entry in self.cache_data["files"].items():
                file_path = self.processing_dir / file_key
                
                # Remove if file doesn't exist or entry is too old
                if (not file_path.exists() or 
                    entry.get("cached_at", 0) < stale_threshold):
                    stale_keys.append(file_key)
            
            for key in stale_keys:
                del self.cache_data["files"][key]
            
            if stale_keys:
                logger.debug(f"Cleaned up {len(stale_keys)} stale cache entries")
                
        except Exception as e:
            logger.debug(f"Cache cleanup failed: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        try:
            total_entries = len(self.cache_data["files"])
            cache_size_bytes = len(json.dumps(self.cache_data))
            
            # Check how many cached files still exist
            valid_entries = 0
            for file_key in self.cache_data["files"]:
                file_path = self.processing_dir / file_key
                if file_path.exists():
                    valid_entries += 1
            
            return {
                "total_entries": total_entries,
                "valid_entries": valid_entries,
                "cache_size_mb": cache_size_bytes / (1024 * 1024),
                "last_updated": self.cache_data.get("last_updated", 0),
                "cache_version": self.cache_data.get("cache_version", "unknown")
            }
            
        except Exception as e:
            logger.debug(f"Failed to get cache stats: {e}")
            return {"error": str(e)}
    
    def _load_cache(self):
        """Load cache from disk if it exists and is valid."""
        try:
            if not self.cache_file.exists():
                return
            
            cache_data = json.loads(self.cache_file.read_text())
            
            # Validate cache version
            if cache_data.get("cache_version") != self.cache_version:
                logger.debug("Cache version mismatch, starting fresh")
                return
            
            # Validate cache structure
            if not all(field in cache_data for field in ["cache_version", "last_updated", "files"]):
                logger.debug("Invalid cache structure, starting fresh")
                return
            
            self.cache_data = cache_data
            logger.debug(f"Loaded cache with {len(cache_data['files'])} entries")
            
        except Exception as e:
            logger.debug(f"Failed to load cache: {e}")
            # Continue with empty cache
    
    def _save_cache(self):
        """Save cache to disk atomically."""
        try:
            self.cache_data["last_updated"] = time.time()
            
            # Write atomically using temporary file
            temp_file = self.cache_file.with_suffix('.tmp')
            temp_file.write_text(json.dumps(self.cache_data, indent=2))
            temp_file.replace(self.cache_file)
            
            logger.debug(f"Saved cache with {len(self.cache_data['files'])} entries")
            
        except Exception as e:
            logger.debug(f"Failed to save cache: {e}")
            # Don't fail the operation if saving fails
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """
        Compute fast hash for cache invalidation using file metadata.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hash string representing file state
        """
        try:
            stat = file_path.stat()
            return f"mtime_{int(stat.st_mtime)}_size_{stat.st_size}"
        except Exception:
            return "invalid"
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save cache."""
        self._save_cache()


# Global cache instance (initialized when needed)
_global_html_cache = None


def get_html_cache(processing_dir: Path) -> HTMLMetadataCache:
    """
    Get or create global HTML metadata cache instance.
    
    Args:
        processing_dir: Processing directory
        
    Returns:
        HTMLMetadataCache instance
    """
    global _global_html_cache
    
    if _global_html_cache is None or _global_html_cache.processing_dir != processing_dir:
        _global_html_cache = HTMLMetadataCache(processing_dir)
    
    return _global_html_cache
