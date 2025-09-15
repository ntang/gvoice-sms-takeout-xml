"""
Shared constants to break circular imports.
Moves all global constants from sms.py to centralize configuration.
"""

import os
import threading
from pathlib import Path
from typing import Optional

# ====================================================================
# CONFIGURATION CONSTANTS
# ====================================================================

# Default file paths and names (can be overridden by command line arguments)
DEFAULT_LOG_FILENAME = "gvoice_converter.log"

# Global variables for paths (set by command line arguments)
PROCESSING_DIRECTORY = None  # Will be set based on processing directory
OUTPUT_DIRECTORY = None  # Will be set based on processing directory
LOG_FILENAME = None  # Will be set based on processing directory

# Global conversation manager
CONVERSATION_MANAGER = None

# Global phone lookup manager
PHONE_LOOKUP_MANAGER = None

# Global path manager for consistent path handling
PATH_MANAGER = None

# Global limited file list for test mode
LIMITED_HTML_FILES = None

# Global skip filtered contacts setting
SKIP_FILTERED_CONTACTS = True

# Global filtering configuration
INCLUDE_SERVICE_CODES = False  # Default: filter out service codes
DATE_FILTER_OLDER_THAN = None  # Filter out messages older than this date
DATE_FILTER_NEWER_THAN = None  # Filter out messages newer than this date
FILTER_NUMBERS_WITHOUT_ALIASES = False  # Filter out numbers without aliases
FILTER_NON_PHONE_NUMBERS = False  # Filter out non-phone numbers like shortcodes
FULL_RUN = False  # Default: not in full-run mode

# Thread safety locks
GLOBAL_STATS_LOCK = threading.Lock()
CONVERSATION_MANAGER_LOCK = threading.Lock()
PHONE_LOOKUP_MANAGER_LOCK = threading.Lock()
FILE_OPERATIONS_LOCK = threading.Lock()

# Progress logging configuration
PROGRESS_INTERVAL_PERCENT = 25  # Report progress every 25%
PROGRESS_INTERVAL_COUNT = 50  # Report every N items (used in some loops)
ENABLE_PROGRESS_LOGGING = True
MIN_PROGRESS_INTERVAL = 100

# Performance monitoring configuration
ENABLE_PERFORMANCE_MONITORING = True
PERFORMANCE_LOG_INTERVAL = 1000  # milliseconds or operation count, depending on usage

# Test mode configuration
TEST_MODE = False
TEST_LIMIT = 100

# Performance configuration - Optimized for large datasets by default
ENABLE_BATCH_PROCESSING = True
LARGE_DATASET_THRESHOLD = 5000  # Files (increased for better large dataset handling)
BATCH_SIZE_OPTIMAL = 1000  # Files per batch (increased for better efficiency)
BUFFER_SIZE_OPTIMAL = 32768  # Bytes (32KB - increased for better I/O performance)

# Advanced performance configuration for large datasets (50,000+ files) -
# High performance defaults
ENABLE_PARALLEL_PROCESSING = True
MAX_WORKERS = min(
    16, os.cpu_count() or 8
)  # Increased to 16 workers max for better parallelization
# Files per chunk for parallel processing (optimized for large datasets)
CHUNK_SIZE_OPTIMAL = 1000
MEMORY_EFFICIENT_THRESHOLD = 10000  # Increased threshold for memory-efficient mode
ENABLE_STREAMING_PARSING = True  # Use streaming for very large files
STREAMING_CHUNK_SIZE = (
    2 * 1024 * 1024
)  # 2MB chunks for streaming (increased for better performance)

# File I/O optimization - High performance defaults
FILE_READ_BUFFER_SIZE = (
    262144  # 256KB buffer for file reading (doubled for better performance)
)
# Memory mapping enabled by default for better performance on large files
ENABLE_MMAP_FOR_LARGE_FILES = True  # Use memory mapping for files > 5MB
MMAP_THRESHOLD = 5 * 1024 * 1024  # 5MB threshold for mmap

# Configuration management
def get_config_path() -> Optional[Path]:
    """Get the configuration file path from environment or default location."""
    config_path = os.environ.get('GVOICE_CONFIG_PATH')
    if config_path:
        return Path(config_path)
    
    # Default to current directory
    return Path.cwd() / "gvoice-config.txt"

def load_config() -> dict:
    """Load configuration from file or environment variables with schema validation."""
    config = {
        'default_processing_dir': os.environ.get('GVOICE_DEFAULT_DIR', '../gvoice-convert/'),
        'enable_path_validation': os.environ.get('GVOICE_ENABLE_VALIDATION', 'true').lower() == 'true',
        'enable_runtime_validation': os.environ.get('GVOICE_RUNTIME_VALIDATION', 'true').lower() == 'true',
        'validation_interval': int(os.environ.get('GVOICE_VALIDATION_INTERVAL', '10')),
        'max_workers': int(os.environ.get('GVOICE_MAX_WORKERS', '16')),
        'chunk_size': int(os.environ.get('GVOICE_CHUNK_SIZE', '1000')),
        'memory_threshold': int(os.environ.get('GVOICE_MEMORY_THRESHOLD', '10000')),
        'buffer_size': int(os.environ.get('GVOICE_BUFFER_SIZE', '32768')),
        'cache_size': int(os.environ.get('GVOICE_CACHE_SIZE', '50000')),
        'batch_size': int(os.environ.get('GVOICE_BATCH_SIZE', '1000')),
    }
    
    # Try to load from config file
    config_path = get_config_path()
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        config[key.strip()] = value.strip()
        except Exception as e:
            # Import here to avoid circular imports
            from utils.logger import logger
            logger.warning(f"Failed to load config file {config_path}: {e}")
    
    # Validate configuration using schema
    try:
        from core.app_config import validate_config_schema, validate_config_relationships, validate_config_paths
        
        # Schema validation
        schema_errors = validate_config_schema(config)
        if schema_errors:
            from utils.logger import logger
            logger.error("Configuration schema validation failed:")
            for error in schema_errors:
                logger.error(f"  - {error}")
            logger.warning("Using default configuration values")
            # Reset to defaults on validation failure
            config = {
                'default_processing_dir': '../gvoice-convert/',
                'enable_path_validation': True,
                'enable_runtime_validation': True,
                'validation_interval': 10,
                'max_workers': 16,
                'chunk_size': 1000,
                'memory_threshold': 10000,
                'buffer_size': 32768,
                'cache_size': 50000,
                'batch_size': 1000,
            }
        
        # Relationship validation
        relationship_errors = validate_config_relationships(config)
        if relationship_errors:
            from utils.logger import logger
            logger.warning("Configuration relationship validation warnings:")
            for error in relationship_errors:
                logger.warning(f"  - {error}")
        
        # Path validation
        path_errors = validate_config_paths(config)
        if path_errors:
            from utils.logger import logger
            logger.warning("Configuration path validation warnings:")
            for error in path_errors:
                logger.warning(f"  - {error}")
                
    except ImportError as e:
        from utils.logger import logger
        logger.warning(f"Could not import configuration validation: {e}")
        logger.warning("Configuration validation disabled")
    except Exception as e:
        from utils.logger import logger
        logger.warning(f"Configuration validation failed: {e}")
        logger.warning("Configuration validation disabled")
    
    return config

# Load configuration
CONFIG = load_config()

# Initialize PROCESSING_DIRECTORY from config
PROCESSING_DIRECTORY = Path(CONFIG.get('default_processing_dir', '../gvoice-convert/'))

def set_test_mode(enabled: bool, limit: int = 100):
    """Set test mode configuration."""
    global TEST_MODE, TEST_LIMIT
    TEST_MODE = enabled
    TEST_LIMIT = limit
