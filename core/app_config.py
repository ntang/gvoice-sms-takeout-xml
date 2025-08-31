"""
Configuration module for Google Voice SMS Takeout XML Converter.

This module centralizes all configuration constants used throughout the application.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import os

# ====================================================================
# CONFIGURATION SCHEMA
# ====================================================================

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "default_processing_dir": {
            "type": "string",
            "description": "Default directory for processing Google Voice data"
        },
        "enable_path_validation": {
            "type": "boolean",
            "description": "Enable comprehensive path validation during processing"
        },
        "enable_runtime_validation": {
            "type": "boolean",
            "description": "Enable runtime validation during processing"
        },
        "validation_interval": {
            "type": "integer",
            "minimum": 1,
            "maximum": 3600,
            "description": "Interval in seconds for runtime validation checks"
        },
        "max_workers": {
            "type": "integer",
            "minimum": 1,
            "maximum": 32,
            "description": "Maximum number of parallel workers"
        },
        "chunk_size": {
            "type": "integer",
            "minimum": 50,
            "maximum": 5000,
            "description": "Chunk size for parallel processing"
        },
        "memory_threshold": {
            "type": "integer",
            "minimum": 100,
            "maximum": 1000000,
            "description": "Threshold for switching to memory-efficient mode"
        },
        "buffer_size": {
            "type": "integer",
            "minimum": 1024,
            "maximum": 1048576,
            "description": "File I/O buffer size in bytes"
        },
        "cache_size": {
            "type": "integer",
            "minimum": 1000,
            "maximum": 1000000,
            "description": "LRU cache size for performance optimization"
        },
        "batch_size": {
            "type": "integer",
            "minimum": 100,
            "maximum": 10000,
            "description": "Batch size for processing large datasets"
        }
    },
    "required": ["default_processing_dir"],
    "additionalProperties": False
}

# ====================================================================
# CONFIGURATION VALIDATION FUNCTIONS
# ====================================================================

def validate_config_schema(config: Dict[str, Any]) -> List[str]:
    """
    Validate configuration against the schema.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required fields
    if "default_processing_dir" not in config:
        errors.append("Missing required field: default_processing_dir")

    # Validate field types and constraints
    for key, value in config.items():
        if key not in CONFIG_SCHEMA["properties"]:
            errors.append(f"Unknown configuration key: {key}")
            continue

        prop_schema = CONFIG_SCHEMA["properties"][key]
        expected_type = prop_schema["type"]

        # Type validation
        if expected_type == "boolean" and not isinstance(value, bool):
            if isinstance(value, str):
                # Try to convert string to boolean
                if value.lower() not in ["true", "false", "1", "0", "yes", "no"]:
                    errors.append(f"Invalid boolean value for {key}: {value}")
            else:
                errors.append(f"Invalid type for {key}: expected boolean, got {type(value).__name__}")

        elif expected_type == "integer" and not isinstance(value, int):
            try:
                int(value)
            except (ValueError, TypeError):
                errors.append(f"Invalid integer value for {key}: {value}")

        elif expected_type == "string" and not isinstance(value, str):
            errors.append(f"Invalid type for {key}: expected string, got {type(value).__name__}")

    # Validate integer constraints
    for key, value in config.items():
        if key in CONFIG_SCHEMA["properties"]:
            prop_schema = CONFIG_SCHEMA["properties"][key]
            if prop_schema["type"] == "integer":
                try:
                    int_value = int(value)
                    if "minimum" in prop_schema and int_value < prop_schema["minimum"]:
                        errors.append(f"Value for {key} ({int_value}) is below minimum ({prop_schema['minimum']})")
                    if "maximum" in prop_schema and int_value > prop_schema["maximum"]:
                        errors.append(f"Value for {key} ({int_value}) is above maximum ({prop_schema['maximum']})")
                except (ValueError, TypeError):
                    pass  # Already caught in type validation

    return errors

def validate_config_relationships(config: Dict[str, Any]) -> List[str]:
    """
    Validate relationships between configuration values.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Validate worker and chunk size relationship
    if "max_workers" in config and "chunk_size" in config:
        try:
            max_workers = int(config["max_workers"])
            chunk_size = int(config["chunk_size"])

            # Ensure chunk size is reasonable for the number of workers
            if chunk_size < max_workers * 10:
                errors.append(f"Chunk size ({chunk_size}) is too small for {max_workers} workers. "
                            f"Consider chunk_size >= {max_workers * 10}")
        except (ValueError, TypeError):
            pass  # Already caught in schema validation

    # Validate memory threshold and batch size relationship
    if "memory_threshold" in config and "batch_size" in config:
        try:
            memory_threshold = int(config["memory_threshold"])
            batch_size = int(config["batch_size"])

            # Ensure batch size doesn't exceed memory threshold
            if batch_size > memory_threshold:
                errors.append(f"Batch size ({batch_size}) exceeds memory threshold ({memory_threshold}). "
                            f"This may cause memory issues.")
        except (ValueError, TypeError):
            pass  # Already caught in schema validation

    return errors

def validate_config_paths(config: Dict[str, Any]) -> List[str]:
    """
    Validate that configuration paths are accessible.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if "default_processing_dir" in config:
        try:
            processing_dir = Path(config["default_processing_dir"])
            if processing_dir.exists() and not processing_dir.is_dir():
                errors.append(f"Processing directory path exists but is not a directory: {processing_dir}")
            elif not processing_dir.exists():
                # Check if parent directory is writable for creation
                parent_dir = processing_dir.parent
                if parent_dir.exists() and not os.access(parent_dir, os.W_OK):
                    errors.append(f"Cannot create processing directory - parent directory not writable: {parent_dir}")
        except Exception as e:
            errors.append(f"Error validating processing directory path: {e}")

    return errors

# ====================================================================
# SUPPORTED FILE TYPES
# ====================================================================

SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif"}
SUPPORTED_VCARD_TYPES = {".vcf"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_TYPES | SUPPORTED_VCARD_TYPES

# ====================================================================
# MMS MESSAGE TYPE CONSTANTS
# ====================================================================

MMS_TYPE_SENT = 128
MMS_TYPE_RECEIVED = 132

# ====================================================================
# MESSAGE BOX CONSTANTS
# ====================================================================

MESSAGE_BOX_SENT = 2
MESSAGE_BOX_RECEIVED = 1

# ====================================================================
# PARTICIPANT TYPE CODES FOR MMS
# ====================================================================

PARTICIPANT_TYPE_SENDER = 137
PARTICIPANT_TYPE_RECEIVED = 151

# ====================================================================
# HASH-BASED FALLBACK CONFIGURATION
# ====================================================================

UNKNOWN_NUMBER_PREFIX = "UN_"
UNKNOWN_NUMBER_HASH_LENGTH = 22  # Base64 encoded MD5 length
UNKNOWN_NUMBER_PATTERN = f"^{UNKNOWN_NUMBER_PREFIX}[a-f0-9_-]{{{UNKNOWN_NUMBER_HASH_LENGTH}}}$"

# ====================================================================
# DEFAULT VALUES AND THRESHOLDS
# ====================================================================

DEFAULT_FALLBACK_TIME = 1000  # milliseconds
MIN_PHONE_NUMBER_LENGTH = 7
FILENAME_TRUNCATE_LENGTH = 50

# ====================================================================
# MMS PLACEHOLDER MESSAGES
# ====================================================================

MMS_PLACEHOLDER_MESSAGES = {"MMS Sent", "MMS Received"}

# ====================================================================
# HTML PARSING CONSTANTS
# ====================================================================

HTML_PARSER = "html.parser"
GROUP_CONVERSATION_MARKER = "Group Conversation"

# ====================================================================
# ERROR MESSAGES
# ====================================================================

ERROR_NO_MESSAGES = "No messages found in HTML file"
ERROR_NO_PARTICIPANTS = "Could not find participant phone number"
ERROR_NO_SENDER = "Unable to determine sender in MMS with multiple participants"

# ====================================================================
# CONFIGURATION EXPORT
# ====================================================================

DEFAULT_CONFIG = {
    "SUPPORTED_IMAGE_TYPES": SUPPORTED_IMAGE_TYPES,
    "SUPPORTED_VCARD_TYPES": SUPPORTED_VCARD_TYPES,
    "MMS_TYPE_SENT": MMS_TYPE_SENT,
    "MMS_TYPE_RECEIVED": MMS_TYPE_RECEIVED,
    "MESSAGE_BOX_SENT": MESSAGE_BOX_SENT,
    "MESSAGE_BOX_RECEIVED": MESSAGE_BOX_RECEIVED,
    "PARTICIPANT_TYPE_SENDER": PARTICIPANT_TYPE_SENDER,
    "PARTICIPANT_TYPE_RECEIVED": PARTICIPANT_TYPE_RECEIVED,
    "UNKNOWN_NUMBER_PREFIX": UNKNOWN_NUMBER_PREFIX,
    "UNKNOWN_NUMBER_HASH_LENGTH": UNKNOWN_NUMBER_HASH_LENGTH,
    "UNKNOWN_NUMBER_PATTERN": UNKNOWN_NUMBER_PATTERN,
}
