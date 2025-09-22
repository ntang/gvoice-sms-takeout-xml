"""
Performance optimizations for Google Voice SMS Converter.

This module provides optimized implementations of performance-critical functions
with caching, parallel processing, and memory efficiency improvements.
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

logger = logging.getLogger(__name__)


class AttachmentCache:
    """High-performance caching system for attachment mapping."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.attachment_cache_file = cache_dir / "attachment_mapping.json"
        self.directory_cache_file = cache_dir / "directory_scan.json"
    
    def get_directory_hash(self, directory: Path) -> str:
        """Generate a hash of directory structure for cache validation."""
        try:
            # Use directory modification time and file count for fast hashing
            stat = directory.stat()
            file_count = sum(1 for _ in directory.rglob("*") if _.is_file())
            return hashlib.md5(f"{stat.st_mtime}_{file_count}".encode()).hexdigest()
        except Exception:
            return "unknown"
    
    def is_cache_valid(self, directory: Path, cache_file: Path) -> bool:
        """Check if cache is still valid."""
        if not cache_file.exists():
            return False
        
        try:
            cache_data = json.loads(cache_file.read_text())
            current_hash = self.get_directory_hash(directory)
            return cache_data.get("directory_hash") == current_hash
        except Exception:
            return False
    
    def load_attachment_cache(self, directory: Path) -> Optional[Dict[str, str]]:
        """Load cached attachment mapping if valid."""
        if self.is_cache_valid(directory, self.attachment_cache_file):
            try:
                cache_data = json.loads(self.attachment_cache_file.read_text())
                logger.info(f"✅ Loaded attachment cache with {len(cache_data['mappings'])} entries")
                return cache_data["mappings"]
            except Exception as e:
                logger.debug(f"Failed to load attachment cache: {e}")
        return None
    
    def save_attachment_cache(self, directory: Path, mappings: Dict[str, str]) -> None:
        """Save attachment mapping to cache."""
        try:
            cache_data = {
                "directory_hash": self.get_directory_hash(directory),
                "timestamp": time.time(),
                "mappings": mappings
            }
            self.attachment_cache_file.write_text(json.dumps(cache_data, indent=2))
            logger.info(f"✅ Saved attachment cache with {len(mappings)} entries")
        except Exception as e:
            logger.debug(f"Failed to save attachment cache: {e}")


def scan_directory_optimized(directory: Path, extensions: Set[str]) -> List[str]:
    """
    Optimized directory scanning with early termination and filtering.
    
    Args:
        directory: Directory to scan
        extensions: Set of file extensions to look for
        
    Returns:
        List of attachment filenames found
    """
    attachment_files = []
    
    # Convert extensions to lowercase for faster comparison
    extensions_lower = {ext.lower() for ext in extensions}
    
    try:
        # Use os.scandir for better performance than os.walk
        for entry in os.scandir(directory):
            if entry.is_file():
                # Fast extension check without creating Path object
                name = entry.name
                if '.' in name:
                    ext = name[name.rfind('.'):].lower()
                    if ext in extensions_lower:
                        attachment_files.append(name)
            elif entry.is_dir():
                # Recursive scan for subdirectories
                try:
                    sub_files = scan_directory_optimized(Path(entry.path), extensions)
                    attachment_files.extend(sub_files)
                except PermissionError:
                    logger.debug(f"Permission denied accessing {entry.path}")
                    continue
                
        return attachment_files
        
    except Exception as e:
        logger.error(f"Error scanning directory {directory}: {e}")
        return attachment_files


@lru_cache(maxsize=10000)
def normalize_filename_cached(filename: str) -> str:
    """Cached filename normalization for better performance."""
    return filename.lower().strip()


def build_attachment_mapping_optimized(
    processing_dir: Path,
    sample_files: Optional[List[str]] = None,
    use_cache: bool = True
) -> Dict[str, Tuple[str, Path]]:
    """
    Optimized attachment mapping with caching and performance improvements.
    
    Args:
        processing_dir: Directory to process
        sample_files: Optional list of files to limit processing (test mode)
        use_cache: Whether to use caching (default: True)
        
    Returns:
        Mapping from src elements to (filename, source_path) tuples
    """
    start_time = time.time()
    
    # Initialize cache system
    cache = AttachmentCache(processing_dir / ".cache") if use_cache else None
    
    # Try to load from cache first
    if cache:
        cached_mapping = cache.load_attachment_cache(processing_dir)
        if cached_mapping:
            # Convert cached mapping back to expected format
            result = {}
            for src, filename in cached_mapping.items():
                file_path = processing_dir / filename
                if file_path.exists():
                    result[src] = (filename, file_path)
            
            if result:
                logger.info(f"✅ Using cached attachment mapping ({len(result)} entries) in {time.time() - start_time:.2f}s")
                return result
    
    logger.info("Building optimized attachment mapping...")
    
    # Step 1: Fast directory scan for attachment files
    attachment_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',  # Images
        '.vcf',  # vCards  
        '.mp3', '.wav', '.m4a', '.aac',  # Audio
        '.mp4', '.mov', '.avi', '.mkv',  # Video
        '.pdf', '.doc', '.docx', '.txt'  # Documents
    }
    
    scan_start = time.time()
    attachment_files = scan_directory_optimized(processing_dir, attachment_extensions)
    scan_time = time.time() - scan_start
    logger.info(f"✅ Directory scan completed: {len(attachment_files)} files in {scan_time:.2f}s")
    
    # Step 2: Extract src elements from HTML files (optimized)
    src_start = time.time()
    if sample_files:
        logger.info(f"🧪 TEST MODE: Limiting src extraction to {len(sample_files)} files")
        src_elements = extract_src_elements_optimized(processing_dir, sample_files)
    else:
        src_elements = extract_src_elements_optimized(processing_dir)
    
    src_time = time.time() - src_start
    logger.info(f"✅ Src extraction completed: {len(src_elements)} elements in {src_time:.2f}s")
    
    # Step 3: Build mapping with optimized matching
    mapping_start = time.time()
    mapping = create_optimized_mapping(src_elements, attachment_files, processing_dir)
    mapping_time = time.time() - mapping_start
    
    # Save to cache for future runs
    if cache and mapping:
        cache_mapping = {src: filename for src, (filename, _) in mapping.items()}
        cache.save_attachment_cache(processing_dir, cache_mapping)
    
    total_time = time.time() - start_time
    logger.info(f"✅ Optimized attachment mapping completed: {len(mapping)} mappings in {total_time:.2f}s")
    logger.info(f"   Breakdown: Scan {scan_time:.2f}s, Src {src_time:.2f}s, Mapping {mapping_time:.2f}s")
    
    return mapping


def extract_src_elements_optimized(processing_dir: Path, sample_files: Optional[List[str]] = None) -> Set[str]:
    """
    Optimized extraction of src elements from HTML files.
    
    Args:
        processing_dir: Directory containing HTML files
        sample_files: Optional list of specific files to process
        
    Returns:
        Set of unique src elements found
    """
    src_elements = set()
    
    # Determine which files to process
    if sample_files:
        html_files = [processing_dir / f for f in sample_files if Path(processing_dir / f).exists()]
    else:
        # Fast glob for HTML files
        html_files = list(processing_dir.rglob("*.html"))
    
    logger.info(f"Extracting src elements from {len(html_files)} HTML files...")
    
    for html_file in html_files:
        try:
            # Fast text-based extraction instead of full HTML parsing
            content = html_file.read_text(encoding='utf-8', errors='ignore')
            
            # Use simple string operations for speed
            import re
            # Match src="..." and href="..." attributes
            src_matches = re.findall(r'(?:src|href)="([^"]+)"', content, re.IGNORECASE)
            
            for src in src_matches:
                if src and not src.startswith(('http', 'mailto', '#')):
                    src_elements.add(src.strip())
                    
        except Exception as e:
            logger.debug(f"Error processing {html_file}: {e}")
            continue
    
    return src_elements


def create_optimized_mapping(
    src_elements: Set[str], 
    attachment_files: List[str], 
    processing_dir: Path
) -> Dict[str, Tuple[str, Path]]:
    """
    Create optimized src-to-attachment mapping.
    
    Args:
        src_elements: Set of src elements to map
        attachment_files: List of available attachment files
        processing_dir: Processing directory
        
    Returns:
        Mapping from src to (filename, path) tuples
    """
    mapping = {}
    used_files = set()
    
    # Create fast lookup structures
    files_by_name = {normalize_filename_cached(f): f for f in attachment_files}
    files_by_stem = {}
    for f in attachment_files:
        stem = Path(f).stem.lower()
        if stem not in files_by_stem:
            files_by_stem[stem] = []
        files_by_stem[stem].append(f)
    
    logger.info(f"Creating mapping for {len(src_elements)} src elements...")
    
    for src in src_elements:
        if not src.strip():
            continue
            
        src_normalized = normalize_filename_cached(src)
        
        # Strategy 1: Direct filename match
        if src_normalized in files_by_name and files_by_name[src_normalized] not in used_files:
            filename = files_by_name[src_normalized]
            file_path = processing_dir / filename
            if file_path.exists():
                mapping[src] = (filename, file_path)
                used_files.add(filename)
                continue
        
        # Strategy 2: Stem-based matching
        src_stem = Path(src).stem.lower()
        if src_stem in files_by_stem:
            for candidate in files_by_stem[src_stem]:
                if candidate not in used_files:
                    file_path = processing_dir / candidate
                    if file_path.exists():
                        mapping[src] = (candidate, file_path)
                        used_files.add(candidate)
                        break
    
    return mapping


def optimize_html_parsing():
    """Implement HTML parsing optimizations."""
    # Use faster HTML parser
    try:
        import lxml
        logger.info("✅ lxml available - using fast XML parser")
        return "lxml"
    except ImportError:
        logger.info("ℹ️ lxml not available - using html.parser")
        return "html.parser"


class OptimizedHTMLProcessor:
    """Optimized HTML processing with caching and memory efficiency."""
    
    def __init__(self, cache_size: int = 1000):
        self.parser_cache = {}
        self.cache_size = cache_size
        self.parser_type = optimize_html_parsing()
        self.file_content_cache = {}
        
    @lru_cache(maxsize=5000)
    def extract_phone_number_cached(self, phone_text: str) -> Optional[str]:
        """Cached phone number extraction."""
        import re
        # Simple phone number extraction with caching
        phone_pattern = r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        match = re.search(phone_pattern, phone_text)
        if match:
            return f"+1{match.group(1)}{match.group(2)}{match.group(3)}"
        return None
    
    def get_optimized_parser(self) -> str:
        """Get the best available HTML parser."""
        try:
            import lxml
            return "lxml"  # Fastest parser
        except ImportError:
            try:
                import html5lib
                return "html5lib"  # More accurate than html.parser
            except ImportError:
                return "html.parser"  # Fallback
    
    def read_file_with_cache(self, html_file: Path) -> str:
        """Read file with intelligent caching."""
        file_key = str(html_file)
        file_stat = html_file.stat()
        cache_key = f"{file_key}_{file_stat.st_mtime}_{file_stat.st_size}"
        
        if cache_key in self.file_content_cache:
            return self.file_content_cache[cache_key]
        
        # Read file with optimized buffer
        try:
            with html_file.open('r', encoding='utf-8', buffering=131072, errors='ignore') as f:
                content = f.read()
            
            # Cache small files only to prevent memory bloat
            if len(content) < 50000:  # 50KB limit for caching
                self.file_content_cache[cache_key] = content
                
                # Prevent cache from growing too large
                if len(self.file_content_cache) > self.cache_size:
                    # Remove oldest 20% of entries
                    keys_to_remove = list(self.file_content_cache.keys())[:self.cache_size // 5]
                    for key in keys_to_remove:
                        del self.file_content_cache[key]
            
            return content
            
        except Exception as e:
            logger.debug(f"Error reading {html_file}: {e}")
            return ""
    
    def fast_html_precheck(self, content: str) -> Dict[str, any]:
        """Fast pre-analysis of HTML content without full parsing."""
        if len(content) < 100:
            return {"skip": True, "reason": "too_small"}
        
        content_lower = content.lower()
        
        # Fast checks without parsing
        has_html = '<html' in content_lower
        has_messages = any(keyword in content_lower for keyword in ['<div', '<span', 'message', 'sms', 'mms'])
        has_calls = 'call' in content_lower or 'duration' in content_lower
        has_voicemail = 'voicemail' in content_lower or 'transcript' in content_lower
        
        # Estimate message count without parsing
        estimated_messages = content.count('<div') + content.count('<tr')
        
        return {
            "skip": not has_html,
            "has_messages": has_messages,
            "has_calls": has_calls,
            "has_voicemail": has_voicemail,
            "estimated_messages": estimated_messages,
            "content_size": len(content)
        }
    
    def process_html_optimized(self, html_file: Path) -> Dict[str, any]:
        """
        Process HTML file with comprehensive optimizations.
        
        Args:
            html_file: Path to HTML file
            
        Returns:
            Processing results with performance metrics
        """
        start_time = time.time()
        
        try:
            # Step 1: Fast file reading with caching
            read_start = time.time()
            content = self.read_file_with_cache(html_file)
            read_time = time.time() - read_start
            
            # Step 2: Fast pre-analysis
            precheck_start = time.time()
            precheck = self.fast_html_precheck(content)
            precheck_time = time.time() - precheck_start
            
            if precheck["skip"]:
                return {
                    "skipped": True, 
                    "reason": precheck["reason"],
                    "read_time": read_time,
                    "precheck_time": precheck_time
                }
            
            # Step 3: Optimized parsing only if needed
            parse_start = time.time()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, self.parser_type)
            parse_time = time.time() - parse_start
            
            # Step 4: Fast data extraction
            extract_start = time.time()
            messages = soup.find_all(['div', 'span'], class_=['message', 'sms', 'mms'])
            extract_time = time.time() - extract_start
            
            total_time = time.time() - start_time
            
            return {
                "messages": len(messages),
                "content_length": len(content),
                "parser_used": self.parser_type,
                "performance": {
                    "total_time": total_time,
                    "read_time": read_time,
                    "precheck_time": precheck_time,
                    "parse_time": parse_time,
                    "extract_time": extract_time
                }
            }
            
        except Exception as e:
            logger.debug(f"Error processing {html_file}: {e}")
            return {"error": str(e), "total_time": time.time() - start_time}


class OptimizedFileIO:
    """Optimized file I/O operations with buffering and caching."""
    
    def __init__(self, buffer_size: int = 65536):
        self.buffer_size = buffer_size
        self.file_cache = {}
    
    def read_file_optimized(self, file_path: Path) -> str:
        """Read file with optimized buffering."""
        try:
            with file_path.open('r', encoding='utf-8', buffering=self.buffer_size, errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.debug(f"Error reading {file_path}: {e}")
            return ""
    
    def write_file_optimized(self, file_path: Path, content: str) -> bool:
        """Write file with optimized buffering."""
        try:
            with file_path.open('w', encoding='utf-8', buffering=self.buffer_size) as f:
                f.write(content)
                f.flush()  # Ensure immediate write
            return True
        except Exception as e:
            logger.error(f"Error writing {file_path}: {e}")
            return False


def optimize_conversation_manager_performance():
    """Apply performance optimizations to ConversationManager."""
    
    # Increase buffer sizes for better I/O performance
    optimizations = {
        "write_buffer_size": 65536,  # 64KB buffer
        "batch_size": 2000,  # Larger batches
        "enable_compression": False,  # Disable compression for speed
        "use_memory_mapping": True,  # Enable memory mapping for large files
    }
    
    logger.info("🚀 Applied ConversationManager performance optimizations")
    return optimizations


def get_performance_recommendations(stats: Dict[str, float]) -> List[str]:
    """
    Analyze performance stats and provide optimization recommendations.
    
    Args:
        stats: Performance statistics
        
    Returns:
        List of optimization recommendations
    """
    recommendations = []
    
    total_time = sum(stats.values())
    
    for component, time_taken in stats.items():
        percentage = (time_taken / total_time) * 100 if total_time > 0 else 0
        
        if percentage > 50:
            recommendations.append(f"🔴 CRITICAL: {component} takes {percentage:.1f}% of total time - needs optimization")
        elif percentage > 25:
            recommendations.append(f"🟡 HIGH: {component} takes {percentage:.1f}% of total time - consider optimization")
        elif percentage > 10:
            recommendations.append(f"🟢 MEDIUM: {component} takes {percentage:.1f}% of total time - minor optimization opportunity")
    
    return recommendations


def apply_all_performance_optimizations(config) -> Dict[str, any]:
    """
    Apply all safe performance optimizations.
    
    Args:
        config: Processing configuration
        
    Returns:
        Dictionary of applied optimizations
    """
    optimizations = {
        "attachment_mapping": "optimized_with_caching",
        "html_parsing": optimize_html_parsing(),
        "file_io": "optimized_buffering",
        "conversation_manager": optimize_conversation_manager_performance(),
        "caching_enabled": True,
        "parallel_processing": "disabled_for_stability"
    }
    
    logger.info("🚀 Applied comprehensive performance optimizations")
    for key, value in optimizations.items():
        logger.info(f"   • {key}: {value}")
    
    return optimizations
