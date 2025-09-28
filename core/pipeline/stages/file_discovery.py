"""
File Discovery Stage

Catalogs all HTML files in the processing directory and identifies their types,
creating a comprehensive inventory for downstream processing stages.
"""

import json
import logging
import mimetypes
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple

from bs4 import BeautifulSoup

from ..base import PipelineStage, PipelineContext, StageResult

logger = logging.getLogger(__name__)


class FileDiscoveryStage(PipelineStage):
    """Discovers and catalogs HTML files for processing."""
    
    def __init__(self):
        super().__init__("file_discovery")
        
        # File type detection patterns
        self.file_type_patterns = {
            "sms_mms": {
                "directories": ["Texts", ""],  # Root and Texts directory
                "indicators": ["message-text", "message", "hChatLog", "thread"]
            },
            "calls": {
                "directories": ["Calls"],
                "indicators": ["call-log", "call", "hChatLog"]
            },
            "voicemails": {
                "directories": ["Voicemails"],
                "indicators": ["voicemail", "hChatLog"]
            }
        }
        
    def execute(self, context: PipelineContext) -> StageResult:
        """
        Execute file discovery stage.
        
        Args:
            context: Pipeline context
            
        Returns:
            StageResult: Discovery results
        """
        start_time = time.time()
        
        try:
            logger.info("Starting file discovery and cataloging")
            
            # Discover all HTML files
            html_files = self._discover_html_files(context.processing_dir)
            logger.info(f"Found {len(html_files)} HTML files")
            
            # Classify files by type
            file_inventory = self._classify_files(html_files, context.processing_dir)
            logger.info(f"Classified files: {len(file_inventory['files'])} total")
            
            # Add processing metadata
            file_inventory["discovery_metadata"] = {
                "scan_date": datetime.now().isoformat(),
                "processing_dir": str(context.processing_dir),
                "scan_duration_ms": int((time.time() - start_time) * 1000),
                "total_files_found": len(html_files)
            }
            
            # Save file inventory
            output_file = context.output_dir / "file_inventory.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(file_inventory, f, indent=2, default=str)
                
            execution_time = time.time() - start_time
            
            # Calculate statistics
            type_counts = {}
            total_size = 0
            for file_info in file_inventory["files"]:
                file_type = file_info["type"]
                type_counts[file_type] = type_counts.get(file_type, 0) + 1
                total_size += file_info["size_bytes"]
                
            result = StageResult(
                success=True,
                execution_time=execution_time,
                records_processed=len(html_files),
                output_files=[output_file],
                metadata={
                    "total_files": len(html_files),
                    "type_counts": type_counts,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "largest_file_mb": round(max((f["size_bytes"] for f in file_inventory["files"]), default=0) / (1024 * 1024), 2)
                }
            )
            
            logger.info(f"File discovery completed in {execution_time:.2f}s")
            logger.info(f"File types found: {type_counts}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"File discovery failed: {e}", exc_info=True)
            
            return StageResult(
                success=False,
                execution_time=execution_time,
                records_processed=0,
                errors=[f"File discovery failed: {str(e)}"]
            )
            
    def _discover_html_files(self, processing_dir: Path) -> List[Path]:
        """Discover all HTML files in the processing directory."""
        html_files = []
        
        # Search in common subdirectories and root
        search_paths = [
            processing_dir,
            processing_dir / "Calls",
            processing_dir / "Texts",
            processing_dir / "Voicemails"
        ]
        
        for search_path in search_paths:
            if search_path.exists() and search_path.is_dir():
                # Find HTML files recursively
                html_files.extend(search_path.rglob("*.html"))
                
        # Remove duplicates and sort
        html_files = sorted(list(set(html_files)))
        
        return html_files
        
    def _classify_files(self, html_files: List[Path], processing_dir: Path) -> Dict[str, Any]:
        """Classify HTML files by type and gather metadata."""
        file_inventory = {
            "files": [],
            "summary": {
                "total_files": 0,
                "by_type": {},
                "by_directory": {},
                "total_size_bytes": 0
            }
        }
        
        for html_file in html_files:
            try:
                file_info = self._analyze_file(html_file, processing_dir)
                file_inventory["files"].append(file_info)
                
                # Update summary statistics
                file_type = file_info["type"]
                directory = file_info["directory"]
                size = file_info["size_bytes"]
                
                file_inventory["summary"]["by_type"][file_type] = \
                    file_inventory["summary"]["by_type"].get(file_type, 0) + 1
                file_inventory["summary"]["by_directory"][directory] = \
                    file_inventory["summary"]["by_directory"].get(directory, 0) + 1
                file_inventory["summary"]["total_size_bytes"] += size
                
            except Exception as e:
                logger.warning(f"Failed to analyze {html_file}: {e}")
                # Add as unknown type
                file_inventory["files"].append({
                    "path": str(html_file),
                    "relative_path": str(html_file.relative_to(processing_dir)),
                    "type": "unknown",
                    "directory": html_file.parent.name,
                    "size_bytes": 0,
                    "modified_time": None,
                    "error": str(e)
                })
                
        file_inventory["summary"]["total_files"] = len(file_inventory["files"])
        
        return file_inventory
        
    def _analyze_file(self, html_file: Path, processing_dir: Path) -> Dict[str, Any]:
        """Analyze a single HTML file to determine its type and metadata."""
        # Basic file metadata
        stat = html_file.stat()
        relative_path = html_file.relative_to(processing_dir)
        
        file_info = {
            "path": str(html_file),
            "relative_path": str(relative_path),
            "directory": html_file.parent.name if html_file.parent != processing_dir else "root",
            "filename": html_file.name,
            "size_bytes": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "type": "unknown"
        }
        
        # Determine file type by directory first
        directory_name = html_file.parent.name.lower()
        if directory_name in ["texts", ""]:
            file_info["type"] = "sms_mms"
        elif directory_name == "calls":
            file_info["type"] = "calls"
        elif directory_name == "voicemails":
            file_info["type"] = "voicemails"
        else:
            # Try to determine by content
            file_info["type"] = self._detect_file_type_by_content(html_file)
            
        # Add content-based metadata if file is not too large
        if stat.st_size < 10 * 1024 * 1024:  # Less than 10MB
            try:
                content_metadata = self._extract_content_metadata(html_file)
                file_info.update(content_metadata)
            except Exception as e:
                logger.debug(f"Failed to extract content metadata from {html_file}: {e}")
                
        return file_info
        
    def _detect_file_type_by_content(self, html_file: Path) -> str:
        """Detect file type by examining HTML content."""
        try:
            # Read a sample of the file to avoid loading huge files
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                sample = f.read(8192)  # Read first 8KB
                
            sample_lower = sample.lower()
            
            # Check for content indicators
            for file_type, patterns in self.file_type_patterns.items():
                for indicator in patterns["indicators"]:
                    if indicator in sample_lower:
                        return file_type
                        
            return "unknown"
            
        except Exception as e:
            logger.debug(f"Failed to detect file type for {html_file}: {e}")
            return "unknown"
            
    def _extract_content_metadata(self, html_file: Path) -> Dict[str, Any]:
        """Extract metadata from HTML content."""
        metadata = {
            "has_messages": False,
            "estimated_message_count": 0,
            "participants": [],
            "date_range": None
        }
        
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Parse with BeautifulSoup for basic analysis
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for message indicators
            message_elements = soup.find_all(['div', 'span'], class_=lambda x: x and any(
                term in str(x).lower() for term in ['message', 'text', 'chat']
            ))
            
            if message_elements:
                metadata["has_messages"] = True
                metadata["estimated_message_count"] = len(message_elements)
                
            # Try to extract participant information from title or headers
            title = soup.find('title')
            if title:
                title_text = title.get_text().strip()
                # Common patterns: "Conversation with John Doe" or "John Doe"
                if title_text and title_text != "Google Voice":
                    metadata["participants"] = [title_text]
                    
            # Look for date information
            date_elements = soup.find_all(text=lambda text: text and any(
                month in text for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            ))
            
            if date_elements:
                # Extract first and last dates found
                dates = []
                for date_text in date_elements[:10]:  # Check first 10 date elements
                    # Simple date extraction - could be enhanced
                    if len(str(date_text).strip()) > 5:
                        dates.append(str(date_text).strip())
                        
                if dates:
                    metadata["date_range"] = {
                        "first_date": dates[0],
                        "last_date": dates[-1] if len(dates) > 1 else dates[0]
                    }
                    
        except Exception as e:
            logger.debug(f"Failed to extract content metadata from {html_file}: {e}")
            
        return metadata
        
    def get_dependencies(self) -> List[str]:
        """File discovery has no dependencies."""
        return []
        
    def validate_prerequisites(self, context: PipelineContext) -> bool:
        """
        Validate prerequisites for file discovery.
        
        Args:
            context: Pipeline context
            
        Returns:
            bool: True if prerequisites are satisfied
        """
        if not context.processing_dir.exists():
            logger.error(f"Processing directory does not exist: {context.processing_dir}")
            return False
            
        if not context.processing_dir.is_dir():
            logger.error(f"Processing directory is not a directory: {context.processing_dir}")
            return False
            
        return True
