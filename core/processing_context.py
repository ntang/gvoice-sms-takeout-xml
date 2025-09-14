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
    
    # Performance settings
    enable_batch_processing: bool = True
    large_dataset_threshold: int = 5000
    batch_size_optimal: int = 1000
    buffer_size_optimal: int = 32768
    enable_parallel_processing: bool = True
    max_workers: int = 16
    chunk_size_optimal: int = 1000
    memory_efficient_threshold: int = 10000
    enable_streaming_parsing: bool = True
    streaming_chunk_size: int = 2 * 1024 * 1024
    file_read_buffer_size: int = 262144
    enable_mmap_for_large_files: bool = True
    mmap_threshold: int = 5 * 1024 * 1024
    
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
        FILTER_NON_PHONE_NUMBERS, FULL_RUN, ENABLE_BATCH_PROCESSING, LARGE_DATASET_THRESHOLD,
        BATCH_SIZE_OPTIMAL, BUFFER_SIZE_OPTIMAL, ENABLE_PARALLEL_PROCESSING, MAX_WORKERS,
        CHUNK_SIZE_OPTIMAL, MEMORY_EFFICIENT_THRESHOLD, ENABLE_STREAMING_PARSING,
        STREAMING_CHUNK_SIZE, FILE_READ_BUFFER_SIZE, ENABLE_MMAP_FOR_LARGE_FILES,
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
        test_mode=TEST_MODE,
        test_limit=TEST_LIMIT,
        limited_html_files=None,  # Will be set later if needed
        skip_filtered_contacts=SKIP_FILTERED_CONTACTS,
        include_service_codes=INCLUDE_SERVICE_CODES,
        date_filter_older_than=DATE_FILTER_OLDER_THAN,
        date_filter_newer_than=DATE_FILTER_NEWER_THAN,
        filter_numbers_without_aliases=FILTER_NUMBERS_WITHOUT_ALIASES,
        filter_non_phone_numbers=FILTER_NON_PHONE_NUMBERS,
        full_run=FULL_RUN,
        enable_batch_processing=ENABLE_BATCH_PROCESSING,
        large_dataset_threshold=LARGE_DATASET_THRESHOLD,
        batch_size_optimal=BATCH_SIZE_OPTIMAL,
        buffer_size_optimal=BUFFER_SIZE_OPTIMAL,
        enable_parallel_processing=ENABLE_PARALLEL_PROCESSING,
        max_workers=MAX_WORKERS,
        chunk_size_optimal=CHUNK_SIZE_OPTIMAL,
        memory_efficient_threshold=MEMORY_EFFICIENT_THRESHOLD,
        enable_streaming_parsing=ENABLE_STREAMING_PARSING,
        streaming_chunk_size=STREAMING_CHUNK_SIZE,
        file_read_buffer_size=FILE_READ_BUFFER_SIZE,
        enable_mmap_for_large_files=ENABLE_MMAP_FOR_LARGE_FILES,
        mmap_threshold=MMAP_THRESHOLD,
        progress_interval_percent=PROGRESS_INTERVAL_PERCENT,
        progress_interval_count=PROGRESS_INTERVAL_COUNT,
        enable_progress_logging=ENABLE_PROGRESS_LOGGING,
        min_progress_interval=MIN_PROGRESS_INTERVAL,
        enable_performance_monitoring=ENABLE_PERFORMANCE_MONITORING,
        performance_log_interval=PERFORMANCE_LOG_INTERVAL,
    )
