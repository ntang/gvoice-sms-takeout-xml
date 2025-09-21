#!/usr/bin/env python3
"""
Test script to verify that CLI date and phone filtering integration is working.

This script tests that CLI arguments are properly parsed and applied to the
filtering system through the configuration and patching system.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from core.processing_config import ConfigurationBuilder
from core.sms_patch import patch_sms_module, unpatch_sms_module

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_cli_date_filtering():
    """Test that CLI date filtering arguments are properly processed."""
    logger.info("🧪 Testing CLI date filtering integration...")
    
    # Simulate CLI arguments for date filtering
    cli_args = {
        'processing_dir': Path('/tmp/test'),
        'older_than': '2023-01-01',
        'newer_than': '2024-12-31',
        'test_mode': False
    }
    
    # Build configuration from CLI args (same as CLI does)
    config = ConfigurationBuilder.from_cli_args(cli_args)
    
    logger.info(f"Configuration created with older_than: {config.older_than}")
    logger.info(f"Configuration created with newer_than: {config.newer_than}")
    
    # Patch the SMS module
    patcher = patch_sms_module(config)
    
    try:
        # Import SMS module after patching
        import sms
        
        # Check that date filter variables are set from CLI args
        assert sms.DATE_FILTER_OLDER_THAN == datetime(2023, 1, 1), f"Expected 2023-01-01, got {sms.DATE_FILTER_OLDER_THAN}"
        assert sms.DATE_FILTER_NEWER_THAN == datetime(2024, 12, 31), f"Expected 2024-12-31, got {sms.DATE_FILTER_NEWER_THAN}"
        
        logger.info("✅ CLI date filtering arguments are properly processed and applied")
        
        # Test the filtering function works with CLI-set values
        old_timestamp = int(datetime(2022, 6, 15, 12, 0, 0).timestamp() * 1000)
        should_skip = sms.should_skip_message_by_date(old_timestamp)
        assert should_skip, "Message from 2022 should be skipped with CLI-set older-than filter"
        
        logger.info("✅ Date filtering logic works with CLI-set configuration")
        
    finally:
        # Clean up
        unpatch_sms_module(patcher)

def test_cli_phone_filtering():
    """Test that CLI phone filtering arguments are properly processed."""
    logger.info("🧪 Testing CLI phone filtering integration...")
    
    # Simulate CLI arguments for phone filtering
    cli_args = {
        'processing_dir': Path('/tmp/test'),
        'filter_numbers_without_aliases': True,
        'filter_non_phone_numbers': True,
        'skip_filtered_contacts': False,  # Test different value
        'include_service_codes': False,
        'test_mode': False
    }
    
    # Build configuration from CLI args
    config = ConfigurationBuilder.from_cli_args(cli_args)
    
    logger.info(f"Configuration created with filter_numbers_without_aliases: {config.filter_numbers_without_aliases}")
    logger.info(f"Configuration created with skip_filtered_contacts: {config.skip_filtered_contacts}")
    
    # Patch the SMS module
    patcher = patch_sms_module(config)
    
    try:
        # Import SMS module after patching
        import sms
        
        # Check that phone filter variables are set from CLI args
        assert sms.FILTER_NUMBERS_WITHOUT_ALIASES == True, f"Expected True, got {sms.FILTER_NUMBERS_WITHOUT_ALIASES}"
        assert sms.FILTER_NON_PHONE_NUMBERS == True, f"Expected True, got {sms.FILTER_NON_PHONE_NUMBERS}"
        assert sms.SKIP_FILTERED_CONTACTS == False, f"Expected False, got {sms.SKIP_FILTERED_CONTACTS}"
        assert sms.INCLUDE_SERVICE_CODES == False, f"Expected False, got {sms.INCLUDE_SERVICE_CODES}"
        
        logger.info("✅ CLI phone filtering arguments are properly processed and applied")
        
    finally:
        # Clean up
        unpatch_sms_module(patcher)

def test_cli_combined_filtering():
    """Test that CLI can handle both date and phone filtering together."""
    logger.info("🧪 Testing CLI combined filtering integration...")
    
    # Simulate CLI arguments for combined filtering
    cli_args = {
        'processing_dir': Path('/tmp/test'),
        'older_than': '2023-06-01',
        'newer_than': '2024-06-30',
        'filter_numbers_without_aliases': True,
        'filter_non_phone_numbers': False,
        'skip_filtered_contacts': True,
        'include_service_codes': True,
        'test_mode': True,
        'test_limit': 50
    }
    
    # Build configuration from CLI args
    config = ConfigurationBuilder.from_cli_args(cli_args)
    
    logger.info(f"Configuration created with combined filters:")
    logger.info(f"  older_than: {config.older_than}")
    logger.info(f"  newer_than: {config.newer_than}")
    logger.info(f"  filter_numbers_without_aliases: {config.filter_numbers_without_aliases}")
    logger.info(f"  skip_filtered_contacts: {config.skip_filtered_contacts}")
    logger.info(f"  test_mode: {config.test_mode}")
    
    # Patch the SMS module
    patcher = patch_sms_module(config)
    
    try:
        # Import SMS module after patching
        import sms
        
        # Check all filter variables are set correctly
        assert sms.DATE_FILTER_OLDER_THAN == datetime(2023, 6, 1), f"Expected 2023-06-01, got {sms.DATE_FILTER_OLDER_THAN}"
        assert sms.DATE_FILTER_NEWER_THAN == datetime(2024, 6, 30), f"Expected 2024-06-30, got {sms.DATE_FILTER_NEWER_THAN}"
        assert sms.FILTER_NUMBERS_WITHOUT_ALIASES == True, f"Expected True, got {sms.FILTER_NUMBERS_WITHOUT_ALIASES}"
        assert sms.FILTER_NON_PHONE_NUMBERS == False, f"Expected False, got {sms.FILTER_NON_PHONE_NUMBERS}"
        assert sms.SKIP_FILTERED_CONTACTS == True, f"Expected True, got {sms.SKIP_FILTERED_CONTACTS}"
        assert sms.INCLUDE_SERVICE_CODES == True, f"Expected True, got {sms.INCLUDE_SERVICE_CODES}"
        assert sms.TEST_MODE == True, f"Expected True, got {sms.TEST_MODE}"
        assert sms.TEST_LIMIT == 50, f"Expected 50, got {sms.TEST_LIMIT}"
        
        logger.info("✅ CLI combined filtering arguments are properly processed and applied")
        
    finally:
        # Clean up
        unpatch_sms_module(patcher)

def main():
    """Run all CLI filtering tests."""
    logger.info("🚀 Starting CLI filtering integration tests...")
    
    try:
        test_cli_date_filtering()
        test_cli_phone_filtering()
        test_cli_combined_filtering()
        
        logger.info("🎉 All CLI filtering tests passed! CLI integration is working correctly.")
        return 0
        
    except Exception as e:
        logger.error(f"❌ CLI test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
