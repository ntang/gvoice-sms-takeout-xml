"""
Path Manager for Google Voice SMS Takeout XML Converter.

This module provides centralized, consistent path handling for all file operations,
eliminating working directory dependencies and ensuring absolute path resolution.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class PathValidationError(Exception):
    """Raised when path validation fails."""
    
    def __init__(self, message: str, path: Optional[Path] = None, context: Optional[str] = None):
        self.message = message
        self.path = path
        self.context = context
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        msg = f"Path validation error: {self.message}"
        if self.path:
            msg += f" (Path: {self.path})"
        if self.context:
            msg += f" (Context: {self.context})"
        return msg


@dataclass
class PathContext:
    """Context information for path operations."""
    operation: str
    source: Optional[Path] = None
    destination: Optional[Path] = None
    working_directory: Optional[Path] = None


class PathManager:
    """
    Centralized path management for all file operations.
    
    This class ensures that all paths are absolute and working directory independent,
    providing consistent path handling throughout the application.
    """
    
    def __init__(self, processing_dir: Path, output_dir: Optional[Path] = None, test_mode: bool = False):
        """
        Initialize PathManager with processing and output directories.
        
        Args:
            processing_dir: Directory containing Google Voice export data
            output_dir: Directory for output files (defaults to processing_dir/conversations)
            test_mode: If True, skip strict path validation for testing
        """
        # Resolve all paths to absolute
        self.processing_dir = Path(processing_dir).resolve()
        
        if output_dir is None:
            self.output_dir = self.processing_dir / "conversations"
        else:
            self.output_dir = Path(output_dir).resolve()
        
        # Define critical subdirectories and files
        self.attachments_dir = self.output_dir / "attachments"
        self.calls_dir = self.processing_dir / "Calls"
        self.phones_vcf = self.processing_dir / "Phones.vcf"
        
        # File location index for performance optimization
        self._file_location_index: Dict[str, Path] = {}
        self._index_built = False
        
        # Validate all paths exist and are accessible (unless in test mode)
        if not test_mode:
            self._validate_paths()
        
        # Log initialization
        logger.info(f"PathManager initialized:")
        logger.info(f"  Processing: {self.processing_dir}")
        logger.info(f"  Output: {self.output_dir}")
        logger.info(f"  Attachments: {self.attachments_dir}")
        logger.info(f"  Calls: {self.calls_dir}")
        logger.info(f"  Phones.vcf: {self.phones_vcf}")
    
    def _validate_paths(self) -> None:
        """Validate all critical paths exist and are accessible."""
        logger.info("Validating critical paths...")
        
        required_paths = [
            (self.processing_dir, "Processing directory"),
            (self.calls_dir, "Calls directory"),
            (self.phones_vcf, "Phones.vcf file"),
        ]
        
        for path, description in required_paths:
            if not path.exists():
                raise PathValidationError(
                    f"{description} does not exist: {path}",
                    path=path,
                    context="PathManager initialization"
                )
            
            if path.is_dir():
                if not os.access(path, os.R_OK):
                    raise PathValidationError(
                        f"{description} is not readable: {path}",
                        path=path,
                        context="PathManager initialization"
                    )
            elif path.is_file():
                if not os.access(path, os.R_OK):
                    raise PathValidationError(
                        f"{description} is not readable: {path}",
                        path=path,
                        context="PathManager initialization"
                    )
            else:
                raise PathValidationError(
                    f"{description} is not accessible: {path}",
                    path=path,
                    context="PathManager initialization"
                )
        
        logger.info("✅ All critical paths validated successfully")
    
    def ensure_output_directories(self) -> None:
        """Create all necessary output directories."""
        logger.info("Ensuring output directories exist...")
        
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.attachments_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"✅ Output directories created/verified:")
            logger.info(f"  {self.output_dir}")
            logger.info(f"  {self.attachments_dir}")
            
        except Exception as e:
            raise PathValidationError(
                f"Failed to create output directories: {e}",
                context="ensure_output_directories"
            )
    
    def get_attachment_source_path(self, filename: str) -> Optional[Path]:
        """
        Get absolute source path for attachment filename.
        
        Args:
            filename: The attachment filename to find
            
        Returns:
            Absolute Path to the source file, or None if not found
        """
        if not self._index_built:
            logger.warning("File location index not built. Call build_file_location_index() first.")
            return None
        
        return self._file_location_index.get(filename)
    
    def get_attachment_dest_path(self, filename: str) -> Path:
        """
        Get absolute destination path for attachment filename.
        
        Args:
            filename: The attachment filename
            
        Returns:
            Absolute Path for the destination file
        """
        return self.attachments_dir / filename
    
    def build_file_location_index(self, filenames: List[str]) -> Dict[str, Path]:
        """
        Build file location index for all attachment files.
        
        Args:
            filenames: List of attachment filenames to index
            
        Returns:
            Dictionary mapping filename to full source Path
        """
        logger.info(f"Building file location index for {len(filenames)} files...")
        
        try:
            filename_set = set(filenames)
            file_index = {}
            
            # Single directory tree walk to find all files
            logger.info("Scanning directory tree for file locations...")
            for root, dirs, files in os.walk(self.processing_dir):
                # Find all matching files in this directory
                for file in files:
                    if file in filename_set:
                        source_file = Path(root) / file
                        if source_file.exists():
                            file_index[file] = source_file.resolve()
                            
                            # Log progress every 1000 files
                            if len(file_index) % 1000 == 0:
                                logger.info(f"Indexed {len(file_index)}/{len(filenames)} files...")
            
            self._file_location_index = file_index
            self._index_built = True
            
            logger.info(f"✅ File location index completed: {len(file_index)}/{len(filenames)} files found")
            return file_index
            
        except Exception as e:
            logger.error(f"❌ Error building file location index: {e}")
            raise
    
    def get_path_context(self, operation: str, source: Optional[Path] = None, 
                        destination: Optional[Path] = None) -> PathContext:
        """
        Get context information for path operations.
        
        Args:
            operation: Description of the operation being performed
            source: Source path (if applicable)
            destination: Destination path (if applicable)
            
        Returns:
            PathContext object with operation details
        """
        return PathContext(
            operation=operation,
            source=source,
            destination=destination,
            working_directory=Path.cwd()
        )
    
    def log_path_operation(self, context: PathContext) -> None:
        """
        Log path operation details for debugging.
        
        Args:
            context: PathContext object with operation details
        """
        logger.debug(f"Path operation: {context.operation}")
        if context.source:
            logger.debug(f"  Source: {context.source}")
        if context.destination:
            logger.debug(f"  Destination: {context.destination}")
        logger.debug(f"  Working directory: {context.working_directory}")
    
    def validate_path_exists(self, path: Path, description: str, context: str = "") -> None:
        """
        Validate that a path exists and is accessible.
        
        Args:
            path: Path to validate
            description: Human-readable description of the path
            context: Context where validation is occurring
            
        Raises:
            PathValidationError: If path validation fails
        """
        if not path.exists():
            raise PathValidationError(
                f"{description} does not exist: {path}",
                path=path,
                context=context
            )
        
        if not os.access(path, os.R_OK):
            raise PathValidationError(
                f"{description} is not readable: {path}",
                path=path,
                context=context
            )
    
    def get_relative_path(self, path: Path, base: Path) -> str:
        """
        Get relative path from base directory.
        
        Args:
            path: Path to get relative path for
            base: Base directory to calculate relative path from
            
        Returns:
            Relative path string
        """
        try:
            return str(path.relative_to(base))
        except ValueError:
            # If path is not relative to base, return absolute path
            return str(path)
    
    def is_subpath(self, path: Path, base: Path) -> bool:
        """
        Check if path is a subpath of base directory.
        
        Args:
            path: Path to check
            base: Base directory
            
        Returns:
            True if path is a subpath of base, False otherwise
        """
        try:
            path.relative_to(base)
            return True
        except ValueError:
            return False
    
    def get_common_ancestor(self, path1: Path, path2: Path) -> Optional[Path]:
        """
        Get common ancestor directory for two paths.
        
        Args:
            path1: First path
            path2: Second path
            
        Returns:
            Common ancestor Path, or None if no common ancestor
        """
        try:
            # Get all parent directories for both paths
            parents1 = set(path1.parents)
            parents2 = set(path2.parents)
            
            # Find intersection (common ancestors)
            common = parents1.intersection(parents2)
            
            if common:
                # Return the deepest common ancestor
                return max(common, key=lambda p: len(p.parts))
            
            return None
            
        except Exception:
            return None
