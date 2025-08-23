"""
Configuration module for SMS/MMS processing.

This module contains configuration constants and settings used throughout the application.
"""

import logging
from pathlib import Path
from typing import Dict, Any

# Logging configuration
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# File processing settings
DEFAULT_BUFFER_SIZE = 8192
DEFAULT_BATCH_SIZE = 1000
DEFAULT_OUTPUT_FORMAT = "xml"
DEFAULT_ENCODING = "utf-8"

# Performance settings
LARGE_DATASET_THRESHOLD = 100000
MEMORY_THRESHOLD = 50000
BATCH_SAVE_INTERVAL = 100

# File patterns
HTML_FILE_PATTERN = "*.html"
XML_FILE_PATTERN = "*.xml"
SMS_FILE_PATTERN = "*Text*.html"
CALL_FILE_PATTERN = "*Placed*.html"
VOICEMAIL_FILE_PATTERN = "*Voicemail*.html"

# Output settings
CONVERSATIONS_DIR = "conversations"
ATTACHMENTS_DIR = "attachments"
INDEX_FILE = "index.html"

# Phone number settings
DEFAULT_COUNTRY_CODE = "US"
PHONE_NUMBER_MIN_LENGTH = 7
PHONE_NUMBER_MAX_LENGTH = 15

# Phone filtering settings
FILTER_NUMBERS_WITHOUT_ALIASES = False  # Default: include all numbers
EXCLUDE_NUMBERS_WITHOUT_ALIASES = False  # Alternative name for the same setting
FILTER_NON_PHONE_NUMBERS = False  # Default: include all numbers (even shortcodes)

# Date filtering
DEFAULT_DATE_FORMAT = "%Y-%m-%d"
TIMESTAMP_PATTERNS = [
    r'(\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}Z)',  # 2024-01-01T12_00_00Z
    r'(\d{4}-\d{2}-\d{2})',  # 2024-01-01
    r'(\d{8})',  # 20240101
    r'(\d{4}_\d{2}_\d{2})',  # 2024_01_01
]

# HTML parsing settings
BEAUTIFUL_SOUP_PARSER = "html.parser"
XML_PARSER = "xml"

# Service codes to filter out
SERVICE_CODES = [
    "VERIZON",
    "AT&T",
    "T-MOBILE",
    "SPRINT",
    "GOOGLE",
    "FACEBOOK",
    "TWITTER",
    "INSTAGRAM",
    "WHATSAPP",
    "TELEGRAM",
    "SIGNAL",
    "DISCORD",
    "SLACK",
    "TEAMS",
    "ZOOM",
    "SKYPE",
    "VIBER",
    "LINE",
    "WECHAT",
    "KIK",
    "SNAPCHAT",
    "TIKTOK",
    "LINKEDIN",
    "YOUTUBE",
    "NETFLIX",
    "SPOTIFY",
    "UBER",
    "LYFT",
    "DOORDASH",
    "GRUBHUB",
    "AMAZON",
    "EBAY",
    "PAYPAL",
    "VENMO",
    "CASHAPP",
    "ROBINHOOD",
    "COINBASE",
    "BINANCE",
    "CHASE",
    "BANK OF AMERICA",
    "WELLS FARGO",
    "CITIBANK",
    "AMERICAN EXPRESS",
    "VISA",
    "MASTERCARD",
    "DISCOVER",
    "CAPITAL ONE",
    "USAA",
    "NAVY FEDERAL",
    "PENTAGON FEDERAL",
    "ALLIANT",
    "SCHWAB",
    "FIDELITY",
    "VANGUARD",
    "BLACKROCK",
    "STATE FARM",
    "ALLSTATE",
    "GEICO",
    "PROGRESSIVE",
    "LIBERTY MUTUAL",
    "NATIONWIDE",
    "TRAVELERS",
    "HARTFORD",
    "FARMERS",
    "AMERICAN FAMILY",
    "ERIE",
    "SAFECO",
    "METLIFE",
    "PRUDENTIAL",
    "NEW YORK LIFE",
    "NORTHWESTERN MUTUAL",
    "MASS MUTUAL",
    "GUARDIAN",
    "JOHN HANCOCK",
    "PRINCIPAL",
    "LINCOLN FINANCIAL",
    "TRANSAMERICA",
    "BRIGHTHOUSE",
    "VOYA",
    "AXA",
    "ALLIANZ",
    "GENERALI",
    "ZURICH",
    "SWISS RE",
    "MUNICH RE",
    "HANNOVER RE",
    "SCOR",
    "BERKSHIRE HATHAWAY",
    "AIG",
    "CHUBB",
    "ACE",
    "XL",
    "CATLIN",
    "AMLIN",
    "HISCOX",
    "BEAZLEY",
    "RSA",
    "AVIVA",
    "PRUDENTIAL PLC",
    "LEGAL & GENERAL",
    "STANDARD LIFE",
    "ABERDEEN",
    "SCHRODERS",
    "M&G",
    "JUPITER",
    "INVESCO",
    "ABERDEEN STANDARD",
    "BLACKROCK",
    "VANGUARD",
    "STATE STREET",
    "BANK OF NEW YORK MELLON",
    "NORTHERN TRUST",
    "BROWN BROTHERS HARRIMAN",
    "CITI",
    "GOLDMAN SACHS",
    "MORGAN STANLEY",
    "JP MORGAN",
    "BANK OF AMERICA MERRILL LYNCH",
    "WELLS FARGO SECURITIES",
    "UBS",
    "CREDIT SUISSE",
    "DEUTSCHE BANK",
    "BARCLAYS",
    "HSBC",
    "ROYAL BANK OF SCOTLAND",
    "LLOYDS",
    "STANDARD CHARTERED",
    "SANTANDER",
    "BBVA",
    "BNP PARIBAS",
    "SOCIETE GENERALE",
    "CREDIT AGRICOLE",
    "AXA",
    "ALLIANZ",
    "GENERALI",
    "ZURICH",
    "SWISS RE",
    "MUNICH RE",
    "HANNOVER RE",
    "SCOR",
    "BERKSHIRE HATHAWAY",
    "AIG",
    "CHUBB",
    "ACE",
    "XL",
    "CATLIN",
    "AMLIN",
    "HISCOX",
    "BEAZLEY",
    "RSA",
    "AVIVA",
    "PRUDENTIAL PLC",
    "LEGAL & GENERAL",
    "STANDARD LIFE",
    "ABERDEEN",
    "SCHRODERS",
    "M&G",
    "JUPITER",
    "INVESCO",
    "ABERDEEN STANDARD",
    "BLACKROCK",
    "VANGUARD",
    "STATE STREET",
    "BANK OF NEW YORK MELLON",
    "NORTHERN TRUST",
    "BROWN BROTHERS HARRIMAN",
    "CITI",
    "GOLDMAN SACHS",
    "MORGAN STANLEY",
    "JP MORGAN",
    "BANK OF AMERICA MERRILL LYNCH",
    "WELLS FARGO SECURITIES",
    "UBS",
    "CREDIT SUISSE",
    "DEUTSCHE BANK",
    "BARCLAYS",
    "HSBC",
    "ROYAL BANK OF SCOTLAND",
    "LLOYDS",
    "STANDARD CHARTERED",
    "SANTANDER",
    "BBVA",
    "BNP PARIBAS",
    "SOCIETE GENERALE",
    "CREDIT AGRICOLE",
]

# Default configuration
DEFAULT_CONFIG = {
    "buffer_size": DEFAULT_BUFFER_SIZE,
    "batch_size": DEFAULT_BATCH_SIZE,
    "output_format": DEFAULT_OUTPUT_FORMAT,
    "encoding": DEFAULT_ENCODING,
    "enable_prompts": True,
    "strict_mode": False,
    "include_service_codes": False,
    "newer_than": None,
    "older_than": None,
    "test_mode": False,
    "test_limit": 0,
    "large_dataset": False,
}

def get_config() -> Dict[str, Any]:
    """Get default configuration."""
    return DEFAULT_CONFIG.copy()

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize configuration values."""
    validated = config.copy()
    
    # Validate buffer size
    if not isinstance(validated.get("buffer_size"), int) or validated["buffer_size"] <= 0:
        validated["buffer_size"] = DEFAULT_BUFFER_SIZE
    
    # Validate batch size
    if not isinstance(validated.get("batch_size"), int) or validated["batch_size"] <= 0:
        validated["batch_size"] = DEFAULT_BATCH_SIZE
    
    # Validate output format
    if validated.get("output_format") not in ["xml", "html"]:
        validated["output_format"] = DEFAULT_OUTPUT_FORMAT
    
    # Validate encoding
    if not validated.get("encoding"):
        validated["encoding"] = DEFAULT_ENCODING
    
    # Validate boolean flags
    for key in ["enable_prompts", "strict_mode", "include_service_codes", "test_mode", "large_dataset"]:
        if not isinstance(validated.get(key), bool):
            validated[key] = DEFAULT_CONFIG[key]
    
    # Validate test limit
    if not isinstance(validated.get("test_limit"), int) or validated["test_limit"] < 0:
        validated["test_limit"] = DEFAULT_CONFIG["test_limit"]
    
    return validated

def get_output_directory(base_dir: Path, config: Dict[str, Any]) -> Path:
    """Get output directory based on configuration."""
    output_dir = base_dir / CONVERSATIONS_DIR
    if config.get("output_format") == "html":
        output_dir = output_dir / "html"
    else:
        output_dir = output_dir / "xml"
    
    return output_dir

def get_attachments_directory(base_dir: Path) -> Path:
    """Get attachments directory."""
    return base_dir / ATTACHMENTS_DIR

def get_index_file_path(output_dir: Path) -> Path:
    """Get index file path."""
    return output_dir / INDEX_FILE
