"""
Improved Utilities Module

This module provides enhanced utilities using well-maintained Python libraries
to replace custom implementations while maintaining the same interface.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# New libraries
import tqdm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pydantic_settings import BaseSettings
from pydantic import field_validator, ConfigDict
from send2trash import send2trash

logger = logging.getLogger(__name__)

# Feature flags for gradual rollout
USE_IMPROVED_UTILS = True  # Can be controlled via environment variable

# ====================================================================
# IMPROVED FILE OPERATIONS
# ====================================================================

def copy_file_safely(source: Path, dest: Path, preserve_metadata: bool = True) -> bool:
    """
    Copy file with automatic fallback and validation.
    
    Args:
        source: Source file path
        dest: Destination file path
        preserve_metadata: Whether to preserve file metadata (timestamps, permissions)
    
    Returns:
        bool: True if copy succeeded, False otherwise
    """
    if not USE_IMPROVED_UTILS:
        # Fallback to old behavior
        return _legacy_copy_file(source, dest, preserve_metadata)
    
    try:
        # Ensure destination directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Use shutil.copy2 for metadata preservation, fallback to copy
        if preserve_metadata:
            try:
                shutil.copy2(source, dest)
            except OSError as e:
                if "cross-device" in str(e).lower():
                    logger.info(f"Cross-device copy detected for {source.name}, using fallback method")
                    shutil.copy(source, dest)
                else:
                    raise
        else:
            shutil.copy(source, dest)
        
        # Verify copy succeeded
        if dest.exists() and dest.stat().st_size == source.stat().st_size:
            logger.debug(f"Successfully copied {source.name} to {dest}")
            return True
        else:
            logger.error(f"Copy verification failed for {source.name}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to copy {source.name}: {e}")
        return False

def _legacy_copy_file(source: Path, dest: Path, preserve_metadata: bool) -> bool:
    """Legacy file copy implementation for fallback."""
    try:
        if preserve_metadata:
            shutil.copy2(source, dest)
        else:
            shutil.copy(source, dest)
        return True
    except Exception as e:
        logger.error(f"Legacy copy failed for {source.name}: {e}")
        return False

def ensure_directory_with_permissions(path: Path, mode: int = 0o755) -> bool:
    """
    Ensure directory exists with proper permissions.
    
    Args:
        path: Directory path to create
        mode: Unix permissions mode
    
    Returns:
        bool: True if directory is ready, False otherwise
    """
    if not USE_IMPROVED_UTILS:
        # Fallback to old behavior
        return _legacy_ensure_directory(path, mode)
    
    try:
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(mode)
        
        # Test write access
        test_file = path / ".test_write"
        test_file.write_text("test")
        test_file.unlink()
        
        logger.debug(f"Directory ready: {path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create/access directory {path}: {e}")
        return False

def _legacy_ensure_directory(path: Path, mode: int) -> bool:
    """Legacy directory creation for fallback."""
    try:
        path.mkdir(exist_ok=True, mode=mode)
        return True
    except Exception as e:
        logger.error(f"Legacy directory creation failed for {path}: {e}")
        return False

def safe_delete_file(file_path: Path, use_trash: bool = True) -> bool:
    """
    Safely delete a file, optionally moving to trash.
    
    Args:
        file_path: Path to file to delete
        use_trash: Whether to move to trash instead of permanent deletion
    
    Returns:
        bool: True if deletion succeeded, False otherwise
    """
    if not USE_IMPROVED_UTILS:
        # Fallback to old behavior (permanent deletion)
        return _legacy_delete_file(file_path)
    
    try:
        if use_trash and file_path.exists():
            send2trash(str(file_path))
            logger.debug(f"Moved {file_path.name} to trash")
            return True
        elif file_path.exists():
            file_path.unlink()
            logger.debug(f"Deleted {file_path.name}")
            return True
        else:
            logger.debug(f"File {file_path.name} does not exist")
            return True
            
    except Exception as e:
        logger.error(f"Failed to delete {file_path.name}: {e}")
        return False

def _legacy_delete_file(file_path: Path) -> bool:
    """Legacy file deletion for fallback."""
    try:
        if file_path.exists():
            file_path.unlink()
            return True
        return True
    except Exception as e:
        logger.error(f"Legacy deletion failed for {file_path.name}: {e}")
        return False

# ====================================================================
# IMPROVED PROGRESS TRACKING
# ====================================================================

class ProgressTracker:
    """Enhanced progress tracking using rich library."""
    
    def __init__(self, description: str = "Processing", total: int = 0):
        self.description = description
        self.total = total
        self.console = Console()
        
    def __enter__(self):
        if USE_IMPROVED_UTILS:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console
            )
            self.progress.start()
            self.task = self.progress.add_task(self.description, total=self.total)
        else:
            self.progress = None
            self.task = None
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress:
            self.progress.stop()
    
    def update(self, advance: int = 1, description: str = None):
        """Update progress."""
        if self.progress and self.task:
            if description:
                self.progress.update(self.task, description=description)
            self.progress.advance(self.task, advance)
        else:
            # Fallback to simple logging
            logger.info(f"Progress: {advance} items processed")

def track_progress_simple(items: List[Any], description: str = "Processing") -> List[Any]:
    """
    Simple progress tracking wrapper for existing code.
    
    Args:
        items: Items to process
        description: Description for progress display
    
    Returns:
        List[Any]: Processed items
    """
    if not USE_IMPROVED_UTILS:
        # Return items unchanged for backward compatibility
        return items
    
    with ProgressTracker(description, len(items)) as tracker:
        for item in items:
            yield item
            tracker.update(1)

# ====================================================================
# IMPROVED DATE/TIME PARSING
# ====================================================================

def parse_timestamp_flexible(timestamp_str: str) -> Optional[int]:
    """
    Parse timestamp using flexible parsing with better error handling.
    
    Args:
        timestamp_str: Timestamp string in various formats
    
    Returns:
        Optional[int]: Unix timestamp in milliseconds, or None if parsing fails
    """
    if not USE_IMPROVED_UTILS:
        # Fallback to existing dateutil parsing
        return _legacy_parse_timestamp(timestamp_str)
    
    try:
        import arrow
        
        # Arrow can handle most common formats automatically
        dt = arrow.get(timestamp_str)
        return int(dt.timestamp() * 1000)  # Convert to milliseconds
        
    except ImportError:
        # Fallback to dateutil if arrow is not available
        return _legacy_parse_timestamp(timestamp_str)
    except Exception as e:
        logger.debug(f"Flexible timestamp parsing failed for '{timestamp_str}': {e}")
        return None

def _legacy_parse_timestamp(timestamp_str: str) -> Optional[int]:
    """Legacy timestamp parsing for fallback."""
    try:
        import dateutil.parser
        dt = dateutil.parser.parse(timestamp_str, fuzzy=True)
        return int(dt.timestamp() * 1000)
    except Exception as e:
        logger.debug(f"Legacy timestamp parsing failed for '{timestamp_str}': {e}")
        return None

# ====================================================================
# IMPROVED CONFIGURATION MANAGEMENT
# ====================================================================

class AppConfig(BaseSettings):
    """Enhanced configuration management using Pydantic."""
    
    # File processing settings
    supported_image_types: List[str] = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]
    supported_vcard_types: List[str] = [".vcf"]
    
    # MMS settings
    mms_type_sent: int = 128
    mms_type_received: int = 132
    
    # Message box settings
    message_box_sent: int = 2
    message_box_received: int = 1
    
    # Participant type settings
    participant_type_sender: int = 137
    participant_type_received: int = 129
    
    # Processing settings
    max_workers: int = 4
    buffer_size: int = 8192
    batch_size: int = 1000
    
    # Feature flags
    use_improved_utils: bool = True
    enable_phone_prompts: bool = False
    filter_numbers_without_aliases: bool = False
    filter_non_phone_numbers: bool = True
    
    model_config = ConfigDict(
        env_file=".env",
        env_prefix="GVOICE_",
        case_sensitive=False
    )
    
    @field_validator('supported_image_types', 'supported_vcard_types')
    @classmethod
    def validate_file_extensions(cls, v):
        """Validate file extensions start with dot."""
        for ext in v:
            if not ext.startswith('.'):
                raise ValueError(f"File extension must start with '.': {ext}")
        return v
    
    @field_validator('max_workers')
    @classmethod
    def validate_max_workers(cls, v):
        """Validate max workers is positive."""
        if v <= 0:
            raise ValueError("max_workers must be positive")
        return v

def load_config() -> AppConfig:
    """
    Load application configuration.
    
    Returns:
        AppConfig: Loaded configuration
    """
    if not USE_IMPROVED_UTILS:
        # Return default config for backward compatibility
        return AppConfig()
    
    try:
        return AppConfig()
    except Exception as e:
        logger.warning(f"Failed to load enhanced config, using defaults: {e}")
        return AppConfig()

# ====================================================================
# IMPROVED LOGGING AND OUTPUT
# ====================================================================

def create_rich_table(title: str, columns: List[str]) -> Table:
    """
    Create a rich table for better output formatting.
    
    Args:
        title: Table title
        columns: Column headers
    
    Returns:
        Table: Rich table object
    """
    if not USE_IMPROVED_UTILS:
        # Return None for backward compatibility
        return None
    
    table = Table(title=title)
    for column in columns:
        table.add_column(column)
    return table

def display_processing_summary(stats: Dict[str, Any]) -> None:
    """
    Display processing summary using rich formatting.
    
    Args:
        stats: Processing statistics
    """
    if not USE_IMPROVED_UTILS:
        # Fallback to simple logging
        logger.info(f"Processing completed: {stats}")
        return
    
    console = Console()
    
    # Create summary table
    table = Table(title="Processing Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            table.add_row(key.replace("_", " ").title(), str(value))
        elif value:
            table.add_row(key.replace("_", " ").title(), str(value))
    
    # Display summary
    console.print(table)
    
    # Create success panel
    success_panel = Panel(
        "✅ Processing completed successfully!",
        title="Status",
        border_style="green"
    )
    console.print(success_panel)

# ====================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# ====================================================================

def get_legacy_config() -> Dict[str, Any]:
    """Get configuration in legacy format for backward compatibility."""
    config = load_config()
    return {
        "SUPPORTED_IMAGE_TYPES": config.supported_image_types,
        "SUPPORTED_VCARD_TYPES": config.supported_vcard_types,
        "MMS_TYPE_SENT": config.mms_type_sent,
        "MMS_TYPE_RECEIVED": config.mms_type_received,
        "MESSAGE_BOX_SENT": config.message_box_sent,
        "MESSAGE_BOX_RECEIVED": config.message_box_received,
        "PARTICIPANT_TYPE_SENDER": config.participant_type_sender,
        "PARTICIPANT_TYPE_RECEIVED": config.participant_type_received,
    }
