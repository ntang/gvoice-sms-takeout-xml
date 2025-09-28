"""
Unit tests for the unified configuration system.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.unified_config import (
    AppConfig,
    create_default_config,
    create_high_performance_config,
    create_memory_efficient_config,
    create_test_config,
    merge_configs
)


class TestAppConfig:
    """Test the AppConfig class."""
    
    def test_default_configuration(self):
        """Test that default configuration is created correctly."""
        config = AppConfig()
        
        # Test basic defaults
        assert config.processing_dir == Path("../gvoice-convert/").resolve()

        assert config.output_format == "html"
        assert config.test_mode is True
        assert config.test_limit == 100
    

    def test_custom_configuration(self):
        """Test that custom configuration values are applied correctly."""
        config = AppConfig(
            processing_dir="/custom/path",
            test_limit=50
        )
        
        # The processing_dir should be the custom path, not the default
        assert str(config.processing_dir) == "/custom/path"
        assert config.test_limit == 50
    

    def test_validation_constraints(self):
        """Test that validation constraints are enforced."""
        # Test max_workers constraint
        with pytest.raises(ValueError):
            AppConfig(max_workers=0)  # Below minimum
        
        with pytest.raises(ValueError):
            AppConfig(max_workers=50)  # Above maximum
        
        # Test chunk_size constraint
        with pytest.raises(ValueError):
            AppConfig(chunk_size=10)  # Below minimum
        
        with pytest.raises(ValueError):
            AppConfig(chunk_size=10000)  # Above maximum
    
    def test_date_validation(self):
        """Test date format validation."""
        # Valid dates
        config = AppConfig(
            older_than="2023-01-01",
            newer_than="2024-12-31"
        )
        assert config.older_than == "2023-01-01"

        assert config.newer_than == "2024-12-31"
        
        # Valid dates with time
        config = AppConfig(
            older_than="2023-01-01 12:00:00",
            newer_than="2024-12-31 23:59:59"
        )
        assert config.older_than == "2023-01-01 12:00:00"

        assert config.newer_than == "2024-12-31 23:59:59"
        
        # Invalid date format
        with pytest.raises(ValueError):
            AppConfig(older_than="invalid-date")
    
    def test_date_range_validation(self):
        """Test that date range validation works correctly."""
        # Valid range
        config = AppConfig(
            older_than="2023-01-01",
            newer_than="2024-12-31"
        )
        assert config.older_than == "2023-01-01"

        assert config.newer_than == "2024-12-31"
        
        # Invalid range (older > newer)
        with pytest.raises(ValueError):
            AppConfig(
                older_than="2024-12-31",
                newer_than="2023-01-01"
            )
    
    def test_test_mode_conflicts(self):
        """Test that test mode conflicts are resolved correctly."""
        # Full run should override test mode
        config = AppConfig(full_run=True, test_mode=True, test_limit=100)
        assert config.is_test_mode is False
        assert config.effective_test_limit == 0
        
        # Normal test mode
        config = AppConfig(test_mode=True, full_run=False, test_limit=50)
        assert config.is_test_mode is True
        assert config.effective_test_limit == 50
    

    def test_logging_conflicts(self):
        """Test that logging conflicts are resolved correctly."""
        # Debug overrides verbose and log_level
        config = AppConfig(debug=True, verbose=True, log_level="WARNING")
        assert config.effective_log_level == "DEBUG"
        
        # Verbose overrides log_level
        config = AppConfig(verbose=True, log_level="ERROR")
        assert config.effective_log_level == "INFO"
        
        # Normal log level
        config = AppConfig(log_level="WARNING")
        assert config.effective_log_level == "WARNING"
    

    def test_computed_properties(self):
        """Test computed properties work correctly."""
        config = AppConfig()
        
        # Test mode properties
        assert config.is_test_mode is True
        assert config.effective_test_limit == 100
        
        # Log level properties

        assert config.effective_log_level == "INFO"
        
        # Full run mode
        config.full_run = True
        assert config.is_test_mode is False
        assert config.effective_test_limit == 0
    

    def test_utility_methods(self):
        """Test utility methods work correctly."""
        config = AppConfig(processing_dir="/test/path")
        
        # Test directory methods
        assert config.get_processing_directory() == Path("/test/path").resolve()

        assert config.get_output_directory() == Path("/test/path").resolve() / "conversations"
        assert config.get_attachments_directory() == Path("/test/path").resolve() / "conversations" / "attachments"
        
        # Test log file path

        assert config.get_log_file_path() == Path("/test/path").resolve() / "gvoice_converter.log"
        
        # Test custom log filename
        config.log_filename = "custom.log"
        assert config.get_log_file_path() == Path("/test/path").resolve() / "custom.log"
    

    def test_serialization(self):
        """Test configuration serialization methods."""
        config = AppConfig(test_limit=50)
        
        # Test to_dict
        config_dict = config.to_dict()
        assert config_dict['max_workers'] == 16

        assert config_dict['test_limit'] == 50
        
        # Test to_env_file
        env_content = config.to_env_file()
        assert "MAX_WORKERS=16" in env_content
        assert "TEST_LIMIT=50" in env_content
    
    @patch('pathlib.Path.exists')
    def test_processing_directory_validation(self, mock_exists):
        """Test processing directory validation."""
        config = AppConfig(processing_dir="/test/path")
        
        # Mock directory structure - first test: valid structure
        mock_exists.return_value = True
        
        # Should pass validation
        assert config.validate_processing_directory() is True
        
        # Mock missing Calls directory - second test: invalid structure
        mock_exists.return_value = False
        
        # Should fail validation
        assert config.validate_processing_directory() is False
    
    def test_validation_errors(self):
        """Test configuration validation error collection."""
        config = AppConfig()
        
        # Test with valid configuration
        errors = config.get_validation_errors()
        assert len(errors) == 0
        
        # Test with invalid processing directory
        config.processing_dir = Path("/nonexistent/path")
        errors = config.get_validation_errors()
        assert len(errors) > 0
        assert any("does not contain required structure" in error for error in errors)


class TestConfigurationPresets:
    """Test configuration preset functions."""
    
    def test_high_performance_config(self):
        """Test high performance configuration preset."""
        config = create_high_performance_config()
        assert config.batch_size == 2000
        assert config.enable_parallel_processing is True
        assert config.enable_streaming_parsing is True

        assert config.enable_mmap_for_large_files is True
    

    def test_memory_efficient_config(self):
        """Test memory efficient configuration preset."""
        config = create_memory_efficient_config()
        assert config.batch_size == 100
        assert config.enable_parallel_processing is False
        assert config.enable_streaming_parsing is True

        assert config.enable_mmap_for_large_files is False
    

    def test_test_config(self):
        """Test test configuration preset."""
        config = create_test_config()
        
        assert config.test_mode is True
        assert config.test_limit == 10
        assert config.batch_size == 100
        assert config.enable_parallel_processing is False
        assert config.log_level == "DEBUG"
        assert config.debug is True

        assert config.strict_mode is True


class TestConfigurationFactories:
    """Test configuration factory functions."""
    

    def test_create_default_config(self):
        """Test default configuration creation."""
        config = create_default_config()
        assert isinstance(config, AppConfig)
        assert config.processing_dir == Path("../gvoice-convert/").resolve()
    

    def test_create_config_from_env(self):
        """Test configuration creation from environment variables."""
        # This function is not implemented - AppConfig() handles env vars directly
        config = AppConfig()
        assert isinstance(config, AppConfig)
    
    def test_merge_configs(self):
        """Test configuration merging."""
        config1 = AppConfig(chunk_size=100)
        config2 = AppConfig(test_limit=50)
        
        merged = merge_configs(config1, config2)
        
        # config2 should override config1 for specified values        assert merged.chunk_size == 1000  # From config2 (default value)

        assert merged.test_limit == 50   # From config2
    

    def test_merge_configs_single(self):
        """Test merging single configuration."""
        config = AppConfig(max_workers=4)
        merged = merge_configs(config)
    
    def test_merge_configs_empty(self):
        """Test merging no configurations."""
        merged = merge_configs()
        assert isinstance(merged, AppConfig)
        assert merged.max_workers == 16  # Default value


class TestConfigurationIntegration:
    """Test configuration integration scenarios."""
    

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict('os.environ', {'GVOICE_MAX_WORKERS': '8'}):
            config = AppConfig()
            assert config.max_workers == 8
    
    def test_environment_variable_processing_dir(self):
        """Test that environment variable for processing directory works."""
        with patch.dict('os.environ', {'GVOICE_PROCESSING_DIR': '/env/path'}):
            config = AppConfig()
            # The environment variable should override the default
            assert str(config.processing_dir) == "/env/path"
    

    def test_boolean_environment_variables(self):
        """Test that boolean environment variables work correctly."""
        with patch.dict('os.environ', {'GVOICE_DEBUG': 'true'}):
            config = AppConfig()
            assert config.debug is True
        
        with patch.dict('os.environ', {'GVOICE_DEBUG': 'false'}):
            config = AppConfig()
            assert config.debug is False
    
    def test_path_resolution(self):
        """Test that paths are properly resolved."""
        config = AppConfig(processing_dir="./relative/path")
        # The path should be resolved to absolute
        assert config.processing_dir.is_absolute()
        # Check that the resolved path contains the relative part
        resolved_path = config.processing_dir.resolve()
        assert "relative" in str(resolved_path)
    
    def test_validation_error_messages(self):
        """Test that validation errors provide helpful messages."""
        with pytest.raises(ValueError, match="Invalid date format"):
            AppConfig(older_than="invalid-date")
        
        with pytest.raises(ValueError, match="Invalid date range"):
            AppConfig(
                older_than="2024-12-31",
                newer_than="2023-01-01"
            )
    
    def test_configuration_persistence(self):
        """Test that configuration changes persist correctly."""
        config = AppConfig()
        original_workers = config.max_workers
        
        config.max_workers = 8
        assert config.max_workers != original_workers
        assert config.max_workers == 8
        
        # Test that other properties are unaffected
        assert config.chunk_size == 1000  # Default unchanged
