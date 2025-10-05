"""
Unit tests for filtering migration system.

This test suite validates the migration framework that enables safe transition
from global variable-based filtering to parameterized filtering.
"""

import pytest
import os
from datetime import datetime
from unittest.mock import Mock, patch
from pathlib import Path

from core.migration_flags import MigrationFlags, reset_migration_flags
from core.filtering_migration import FilteringMigrationValidator, reset_migration_validator
from core.processing_config import ProcessingConfig


class TestMigrationFlags:
    """Test suite for migration flags system."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        # Clear environment variables that might affect tests
        self.env_vars_to_clear = [
            'GVOICE_USE_PARAMETERIZED_FILTERING',
            'GVOICE_VALIDATE_FILTERING_CONSISTENCY',
            'GVOICE_ENABLE_FILTERING_COMPARISON',
            'GVOICE_FALLBACK_TO_GLOBAL_ON_ERROR',
            'GVOICE_MIGRATION_PHASE'
        ]
        self.original_env = {}
        for var in self.env_vars_to_clear:
            self.original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        # Restore original environment variables
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

        # Reset global flags
        reset_migration_flags()

    def test_migration_flags_default_values(self):
        """Test that migration flags have correct default values."""
        flags = MigrationFlags()

        assert flags.use_parameterized_filtering
        assert flags.validate_filtering_consistency
        assert flags.enable_filtering_comparison == False
        assert flags.fallback_to_global_on_error
        assert flags.log_filtering_differences
        assert flags.enable_filtering_metrics == False
        assert flags.max_validation_samples == 1000
        assert flags.migration_phase == 'complete'
        assert flags.enable_legacy_support

    def test_migration_flags_environment_override(self):
        """Test that environment variables override default values."""
        os.environ['GVOICE_USE_PARAMETERIZED_FILTERING'] = 'false'
        os.environ['GVOICE_VALIDATE_FILTERING_CONSISTENCY'] = 'false'
        os.environ['GVOICE_ENABLE_FILTERING_COMPARISON'] = 'true'
        os.environ['GVOICE_MIGRATION_PHASE'] = 'testing'
        os.environ['GVOICE_MAX_VALIDATION_SAMPLES'] = '500'

        flags = MigrationFlags()

        assert flags.use_parameterized_filtering == False
        assert flags.validate_filtering_consistency == False
        assert flags.enable_filtering_comparison
        assert flags.migration_phase == 'testing'
        assert flags.max_validation_samples == 500

    def test_migration_flags_boolean_parsing(self):
        """Test that boolean environment variables are parsed correctly."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('1', True),
            ('yes', True),
            ('on', True),
            ('false', False),
            ('False', False),
            ('0', False),
            ('no', False),
            ('off', False),
            ('invalid', False)  # Invalid values default to False
        ]

        for env_value, expected in test_cases:
            os.environ['GVOICE_USE_PARAMETERIZED_FILTERING'] = env_value
            flags = MigrationFlags()
            assert flags.use_parameterized_filtering == expected

    def test_migration_flags_update_runtime(self):
        """Test that migration flags can be updated at runtime."""
        flags = MigrationFlags()

        original_value = flags.use_parameterized_filtering
        flags.update_flag('use_parameterized_filtering', not original_value)

        assert flags.use_parameterized_filtering == (not original_value)

    def test_migration_flags_is_migration_complete(self):
        """Test migration completion detection."""
        flags = MigrationFlags()

        # Set flags for complete migration
        flags.update_flag('use_parameterized_filtering', True)
        flags.update_flag('enable_filtering_comparison', False)
        flags.update_flag('enable_legacy_support', False)
        flags.update_flag('migration_phase', 'complete')

        assert flags.is_migration_complete()

        # Test incomplete migration
        flags.update_flag('enable_legacy_support', True)
        assert flags.is_migration_complete() == False

    def test_migration_flags_summary(self):
        """Test that flag summary returns all flags."""
        flags = MigrationFlags()
        summary = flags.get_flag_summary()

        expected_flags = [
            'use_parameterized_filtering',
            'validate_filtering_consistency',
            'enable_filtering_comparison',
            'fallback_to_global_on_error',
            'log_filtering_differences',
            'enable_filtering_metrics',
            'max_validation_samples',
            'migration_phase',
            'enable_legacy_support'
        ]

        for flag in expected_flags:
            assert flag in summary


class TestFilteringMigrationValidator:
    """Test suite for filtering migration validator."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.test_dir = Path("/tmp/test_migration")
        self.config = ProcessingConfig(
            processing_dir=self.test_dir,
            exclude_older_than=datetime(2023, 1, 1),
            exclude_newer_than=datetime(2024, 12, 31),
            filter_numbers_without_aliases=True,
            filter_non_phone_numbers=True,
            include_service_codes=False
        )
        self.mock_phone_lookup = Mock()
        self.mock_phone_lookup.has_alias.return_value = True

        reset_migration_validator()

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        reset_migration_validator()

    def test_validator_initialization(self):
        """Test that migration validator initializes correctly."""
        validator = FilteringMigrationValidator()

        assert validator.validation_samples == 0
        assert validator.validation_errors == 0
        assert 'global_filtering_time' in validator.performance_metrics
        assert 'parameterized_filtering_time' in validator.performance_metrics

    def test_date_filtering_validation_consistent(self):
        """Test date filtering validation when results are consistent."""
        validator = FilteringMigrationValidator()

        # Test with old timestamp (should be skipped)
        old_timestamp = int(datetime(2022, 6, 15).timestamp() * 1000)
        param_result, global_result, validation_passed = validator.validate_date_filtering(
            old_timestamp, self.config
        )

        assert param_result  # Should be skipped
        assert global_result  # Should be skipped
        assert validation_passed
        assert validator.validation_samples == 1
        assert validator.validation_errors == 0

    def test_date_filtering_validation_no_config(self):
        """Test date filtering validation when no config is provided."""
        validator = FilteringMigrationValidator()

        timestamp = int(datetime(2023, 6, 15).timestamp() * 1000)
        param_result, global_result, validation_passed = validator.validate_date_filtering(
            timestamp, None
        )

        assert param_result == False  # No filtering
        assert global_result == False
        assert validation_passed
        assert validator.validation_samples == 0  # No validation performed

    def test_phone_filtering_validation_consistent(self):
        """Test phone filtering validation when results are consistent."""
        validator = FilteringMigrationValidator()

        # Test with phone number that has alias
        self.mock_phone_lookup.has_alias.return_value = True
        param_result, global_result, validation_passed = validator.validate_phone_filtering(
            "+1234567890", self.mock_phone_lookup, self.config
        )

        assert param_result == False  # Should not be skipped (has alias)
        assert global_result == False  # Should not be skipped (has alias)
        assert validation_passed
        assert validator.validation_samples == 1
        assert validator.validation_errors == 0

    def test_phone_filtering_validation_without_alias(self):
        """Test phone filtering validation for number without alias."""
        validator = FilteringMigrationValidator()

        # Test with phone number that has no alias
        self.mock_phone_lookup.has_alias.return_value = False
        param_result, global_result, validation_passed = validator.validate_phone_filtering(
            "+1234567890", self.mock_phone_lookup, self.config
        )

        assert param_result  # Should be skipped (no alias)
        assert global_result  # Should be skipped (no alias)
        assert validation_passed
        assert validator.validation_samples == 1
        assert validator.validation_errors == 0

    def test_phone_filtering_validation_short_code(self):
        """Test phone filtering validation for short codes."""
        validator = FilteringMigrationValidator()

        # Test with short code
        param_result, global_result, validation_passed = validator.validate_phone_filtering(
            "555-SHORT", self.mock_phone_lookup, self.config
        )

        assert param_result  # Should be skipped (non-phone number)
        assert global_result  # Should be skipped (non-phone number)
        assert validation_passed

    def test_validation_error_handling(self):
        """Test validation error handling and fallback behavior."""
        validator = FilteringMigrationValidator()

        # Test with invalid timestamp that might cause errors
        invalid_timestamp = -1
        param_result, global_result, validation_passed = validator.validate_date_filtering(
            invalid_timestamp, self.config
        )

        # Should handle gracefully
        assert isinstance(param_result, bool)
        assert isinstance(global_result, bool)
        assert isinstance(validation_passed, bool)

    def test_validation_metrics_collection(self):
        """Test that validation metrics are collected correctly."""
        validator = FilteringMigrationValidator()

        # Perform some validations
        timestamp = int(datetime(2023, 6, 15).timestamp() * 1000)
        validator.validate_date_filtering(timestamp, self.config)
        validator.validate_phone_filtering("+1234567890", self.mock_phone_lookup, self.config)

        metrics = validator.get_validation_summary()

        assert metrics['validation_samples'] == 2
        assert metrics['validation_errors'] == 0
        assert metrics['error_rate'] == 0.0
        assert 'performance_metrics' in metrics
        assert metrics['performance_metrics']['total_validations'] == 2

    def test_migration_safety_assessment(self):
        """Test migration safety assessment."""
        validator = FilteringMigrationValidator()

        # Not enough samples initially
        assert validator.is_migration_safe() == False

        # Add enough successful validations
        timestamp = int(datetime(2023, 6, 15).timestamp() * 1000)
        for _ in range(15):
            validator.validate_date_filtering(timestamp, self.config)

        assert validator.is_migration_safe()

        # Simulate some errors
        validator.validation_errors = 5  # 5 errors out of 15 samples = 33% error rate
        assert validator.is_migration_safe() == False

    def test_validation_metrics_reset(self):
        """Test that validation metrics can be reset."""
        validator = FilteringMigrationValidator()

        # Perform some validations
        timestamp = int(datetime(2023, 6, 15).timestamp() * 1000)
        validator.validate_date_filtering(timestamp, self.config)

        assert validator.validation_samples > 0

        # Reset metrics
        validator.reset_validation_metrics()

        assert validator.validation_samples == 0
        assert validator.validation_errors == 0
        assert validator.performance_metrics['total_validations'] == 0

    def test_non_phone_number_detection(self):
        """Test non-phone number detection logic."""
        validator = FilteringMigrationValidator()

        # Test various non-phone number patterns
        assert validator._is_non_phone_number("555-SHORT")
        assert validator._is_non_phone_number("12345")  # Short code
        assert validator._is_non_phone_number("INFO")  # Contains letters
        assert validator._is_non_phone_number("+1234567890") == False  # Valid phone

    def test_service_code_detection(self):
        """Test service code detection logic."""
        validator = FilteringMigrationValidator()

        # Test various service code patterns
        assert validator._is_service_code("SERVICE")
        assert validator._is_service_code("CODE")
        assert validator._is_service_code("12345")  # Short number
        assert validator._is_service_code("+1234567890") == False  # Valid phone


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
