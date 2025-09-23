"""
Test Suite for Date Filtering Fix

This module tests the date filtering functionality to ensure FilteringService
uses the correct configuration fields (exclude_older_than/exclude_newer_than)
instead of the deprecated fields (older_than/newer_than).
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

import sys
sys.path.append('.')

from core.processing_config import ProcessingConfig
from core.filtering_service import FilteringService


class TestDateFilteringFix:
    """Test suite for date filtering functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.calls_dir = self.test_dir / "Calls"
        self.calls_dir.mkdir(parents=True)
        
        # Create test config with date range 2022-08-01 to 2025-06-01
        self.config = ProcessingConfig(
            processing_dir=self.test_dir,
            include_date_range="2022-08-01_2025-06-01"
        )

    def teardown_method(self):
        """Clean up test environment after each test."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_filtering_service_uses_correct_config_fields(self):
        """
        TEST: FilteringService should check exclude_older_than/exclude_newer_than fields.
        
        This is the primary failing test that will drive our fix.
        Currently FAILS because FilteringService checks wrong fields.
        """
        service = FilteringService(self.config)
        
        # Verify config has correct values set
        assert self.config.exclude_older_than == datetime(2022, 8, 1)
        assert self.config.exclude_newer_than == datetime(2025, 6, 1)
        assert self.config.older_than is None
        assert self.config.newer_than is None
        
        # Test message from 2020 (should be filtered out - before 2022-08-01)
        timestamp_2020 = int(datetime(2020, 6, 15).timestamp() * 1000)
        should_skip_2020 = service.should_skip_by_date(timestamp_2020)
        assert should_skip_2020 == True, f"2020 message should be filtered out, but got {should_skip_2020}"
        
        # Test message from 2023 (should be included - within range)
        timestamp_2023 = int(datetime(2023, 6, 15).timestamp() * 1000)
        should_skip_2023 = service.should_skip_by_date(timestamp_2023)
        assert should_skip_2023 == False, f"2023 message should be included, but got {should_skip_2023}"
        
        # Test message from 2026 (should be filtered out - after 2025-06-01)
        timestamp_2026 = int(datetime(2026, 6, 15).timestamp() * 1000)
        should_skip_2026 = service.should_skip_by_date(timestamp_2026)
        assert should_skip_2026 == True, f"2026 message should be filtered out, but got {should_skip_2026}"