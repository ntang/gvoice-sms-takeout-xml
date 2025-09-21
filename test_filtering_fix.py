#!/usr/bin/env python3
"""
Test script to verify that date and phone filtering fixes are working.

This script tests the SMS module patching to ensure that filtering
global variables are properly set from configuration.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from core.processing_config import ProcessingConfig, ConfigurationBuilder
from core.sms_patch import patch_sms_module, unpatch_sms_module
from core.configuration_manager import set_global_configuration

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_date_filtering():
    """Test that date filtering global variables are properly set."""
    logger.info("🧪 Testing date filtering configuration...")
    
    # Create a configuration with date filters
    config = ProcessingConfig(
        processing_dir=Path("/tmp/test"),
        older_than=datetime(2023, 1, 1),
        newer_than=datetime(2024, 12, 31)
    )
    
    # Patch the SMS module
    patcher = patch_sms_module(config)
    
    try:
        # Import SMS module after patching
        import sms
        
        # Check that date filter variables are set
        assert sms.DATE_FILTER_OLDER_THAN == datetime(2023, 1, 1), f"Expected 2023-01-01, got {sms.DATE_FILTER_OLDER_THAN}"
        assert sms.DATE_FILTER_NEWER_THAN == datetime(2024, 12, 31), f"Expected 2024-12-31, got {sms.DATE_FILTER_NEWER_THAN}"
        
        logger.info("✅ Date filtering global variables are properly set")
        
        # Test the filtering function
        # Message from 2022 should be skipped (older than 2023)
        old_timestamp = int(datetime(2022, 6, 15, 12, 0, 0).timestamp() * 1000)
        should_skip_old = sms.should_skip_message_by_date(old_timestamp)
        assert should_skip_old, "Message from 2022 should be skipped"
        
        # Message from 2023 should NOT be skipped
        current_timestamp = int(datetime(2023, 6, 15, 12, 0, 0).timestamp() * 1000)
        should_skip_current = sms.should_skip_message_by_date(current_timestamp)
        assert not should_skip_current, "Message from 2023 should NOT be skipped"
        
        # Message from 2025 should be skipped (newer than 2024)
        future_timestamp = int(datetime(2025, 1, 15, 12, 0, 0).timestamp() * 1000)
        should_skip_future = sms.should_skip_message_by_date(future_timestamp)
        assert should_skip_future, "Message from 2025 should be skipped"
        
        logger.info("✅ Date filtering logic is working correctly")
        
    finally:
        # Clean up
        unpatch_sms_module(patcher)

def test_phone_filtering():
    """Test that phone filtering global variables are properly set."""
    logger.info("🧪 Testing phone filtering configuration...")
    
    # Create a configuration with phone filters
    config = ProcessingConfig(
        processing_dir=Path("/tmp/test"),
        filter_numbers_without_aliases=True,
        filter_non_phone_numbers=True,
        skip_filtered_contacts=True,
        include_service_codes=False
    )
    
    # Patch the SMS module
    patcher = patch_sms_module(config)
    
    try:
        # Import SMS module after patching
        import sms
        
        # Check that phone filter variables are set
        assert sms.FILTER_NUMBERS_WITHOUT_ALIASES == True, f"Expected True, got {sms.FILTER_NUMBERS_WITHOUT_ALIASES}"
        assert sms.FILTER_NON_PHONE_NUMBERS == True, f"Expected True, got {sms.FILTER_NON_PHONE_NUMBERS}"
        assert sms.SKIP_FILTERED_CONTACTS == True, f"Expected True, got {sms.SKIP_FILTERED_CONTACTS}"
        assert sms.INCLUDE_SERVICE_CODES == False, f"Expected False, got {sms.INCLUDE_SERVICE_CODES}"
        
        logger.info("✅ Phone filtering global variables are properly set")
        
    finally:
        # Clean up
        unpatch_sms_module(patcher)

def test_shared_constants_update():
    """Test that shared_constants module is also updated."""
    logger.info("🧪 Testing shared_constants module update...")
    
    # Create a configuration with filters
    config = ProcessingConfig(
        processing_dir=Path("/tmp/test"),
        older_than=datetime(2023, 1, 1),
        filter_numbers_without_aliases=True
    )
    
    # Patch the SMS module
    patcher = patch_sms_module(config)
    
    try:
        # Import shared_constants after patching
        from core import shared_constants
        
        # Check that shared_constants variables are set
        assert shared_constants.DATE_FILTER_OLDER_THAN == datetime(2023, 1, 1), f"Expected 2023-01-01, got {shared_constants.DATE_FILTER_OLDER_THAN}"
        assert shared_constants.FILTER_NUMBERS_WITHOUT_ALIASES == True, f"Expected True, got {shared_constants.FILTER_NUMBERS_WITHOUT_ALIASES}"
        
        logger.info("✅ shared_constants module is properly updated")
        
    finally:
        # Clean up
        unpatch_sms_module(patcher)

def main():
    """Run all filtering tests."""
    logger.info("🚀 Starting filtering fix verification tests...")
    
    try:
        test_date_filtering()
        test_phone_filtering()
        test_shared_constants_update()
        
        logger.info("🎉 All filtering tests passed! The fix is working correctly.")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
