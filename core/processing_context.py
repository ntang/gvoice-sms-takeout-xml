"""
Processing context to replace global variables.
Simple data class to pass around instead of using global state.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.conversation_manager import ConversationManager
    from core.phone_lookup import PhoneLookupManager
    from core.path_manager import PathManager
    from core.processing_config import ProcessingConfig

@dataclass
class ProcessingContext:
    """Simple context object to pass around instead of globals."""
    # Core managers
    conversation_manager: 'ConversationManager'
    phone_lookup_manager: 'PhoneLookupManager'
    path_manager: 'PathManager'
    
    # Configuration
    config: 'ProcessingConfig'
    
    # Paths
    processing_dir: Path
    output_dir: Path
    log_filename: str
    
    # Test mode settings
    test_mode: bool = False
    test_limit: int = 100
    limited_html_files: Optional[list] = None
    
    # Filtering settings
    skip_filtered_contacts: bool = True
    include_service_codes: bool = False
    date_filter_older_than: Optional[str] = None
    date_filter_newer_than: Optional[str] = None
    filter_numbers_without_aliases: bool = False
    filter_non_phone_numbers: bool = False
    full_run: bool = False
    
    # Performance settings are now hardcoded in shared_constants.py for optimal defaults
    
    # Progress logging settings
    progress_interval_percent: int = 25
    progress_interval_count: int = 50
    enable_progress_logging: bool = True
    min_progress_interval: int = 100
    
    # Performance monitoring settings
    enable_performance_monitoring: bool = True
    performance_log_interval: int = 1000

def create_processing_context(config: 'ProcessingConfig') -> 'ProcessingContext':
    """Create a ProcessingContext from a ProcessingConfig."""
    from core.conversation_manager import ConversationManager
    from core.phone_lookup import PhoneLookupManager
    from core.path_manager import PathManager
    from core.shared_constants import (
        TEST_MODE, TEST_LIMIT, SKIP_FILTERED_CONTACTS, INCLUDE_SERVICE_CODES,
        DATE_FILTER_OLDER_THAN, DATE_FILTER_NEWER_THAN, FILTER_NUMBERS_WITHOUT_ALIASES,
        FILTER_NON_PHONE_NUMBERS, FULL_RUN, LARGE_DATASET_THRESHOLD,
        MMAP_THRESHOLD, PROGRESS_INTERVAL_PERCENT, PROGRESS_INTERVAL_COUNT,
        ENABLE_PROGRESS_LOGGING, MIN_PROGRESS_INTERVAL, ENABLE_PERFORMANCE_MONITORING,
        PERFORMANCE_LOG_INTERVAL
    )
    
    # Create managers
    conversation_manager = ConversationManager(
        output_dir=config.output_dir,
        output_format=config.output_format
    )
    
    phone_lookup_manager = PhoneLookupManager(
        lookup_file=config.phone_lookup_file,
        enable_prompts=config.enable_phone_prompts
    )
    
    path_manager = PathManager(
        processing_dir=config.processing_dir,
        output_dir=config.output_dir
    )
    
    return ProcessingContext(
        conversation_manager=conversation_manager,
        phone_lookup_manager=phone_lookup_manager,
        path_manager=path_manager,
        config=config,
        processing_dir=config.processing_dir,
        output_dir=config.output_dir,
        log_filename=config.log_filename,
        test_mode=config.test_mode,
        test_limit=config.test_limit,
        limited_html_files=None,  # Will be set later if needed
        skip_filtered_contacts=config.skip_filtered_contacts,
        include_service_codes=config.include_service_codes,
        date_filter_older_than=config.older_than,
        date_filter_newer_than=config.newer_than,
        filter_numbers_without_aliases=config.filter_numbers_without_aliases,
        filter_non_phone_numbers=config.filter_non_phone_numbers,
        full_run=config.full_run,
        # large_dataset_threshold is now hardcoded in shared_constants.py
        # mmap_threshold is now hardcoded in shared_constants.py
        progress_interval_percent=PROGRESS_INTERVAL_PERCENT,
        progress_interval_count=PROGRESS_INTERVAL_COUNT,
        enable_progress_logging=ENABLE_PROGRESS_LOGGING,
        min_progress_interval=MIN_PROGRESS_INTERVAL,
        enable_performance_monitoring=ENABLE_PERFORMANCE_MONITORING,
        performance_log_interval=PERFORMANCE_LOG_INTERVAL,
    )
