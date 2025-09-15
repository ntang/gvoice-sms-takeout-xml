"""
Unit tests for the processing configuration module.

Tests the Configuration Object Pattern implementation including
ProcessingConfig, ConfigurationDefaults, and ConfigurationBuilder.
"""

import pytest
from pathlib import Path
from datetime import datetime
from core.processing_config import (
    ProcessingConfig,
    ConfigurationDefaults,
    ConfigurationBuilder
)


class TestProcessingConfig:
    """Test the ProcessingConfig class."""
    
    def test_basic_config_creation(self):
        """Test basic configuration creation with required parameters."""
        config = ProcessingConfig(processing_dir=Path("/tmp/test"))
        
        assert config.processing_dir == Path("/tmp/test")
        assert config.output_dir == Path("/tmp/test/conversations")
        assert config.output_format == "html"
        assert config.max_workers == 16
        assert config.enable_phone_prompts is False
    
    def test_custom_config_creation(self):
        """Test configuration creation with custom values."""
        config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            output_format="xml",
            max_workers=8,
            enable_phone_prompts=True,
            strict_mode=True
        )
        
        assert config.output_format == "xml"
        assert config.max_workers == 8
        assert config.enable_phone_prompts is True
        assert config.strict_mode is True
    
    def test_output_directory_auto_generation(self):
        """Test that output directory is auto-generated if not provided."""
        config = ProcessingConfig(processing_dir=Path("/tmp/test"))
        assert config.output_dir == Path("/tmp/test/conversations")
    
    def test_custom_output_directory(self):
        """Test custom output directory setting."""
        config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/custom/output")
        )
        assert config.output_dir == Path("/tmp/custom/output")
    
    def test_numeric_validation(self):
        """Test numeric constraint validation."""
        # Test valid values
        config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            max_workers=1,
            chunk_size=1,
            batch_size=1,
            buffer_size=1024,
            cache_size=100,
            memory_threshold=100
        )
        assert config.max_workers == 1
        
        # Test invalid max_workers
        with pytest.raises(ValueError, match="max_workers must be >= 1"):
            ProcessingConfig(processing_dir=Path("/tmp/test"), max_workers=0)
        
        # Test invalid buffer_size
        with pytest.raises(ValueError, match="buffer_size must be >= 1024"):
            ProcessingConfig(processing_dir=Path("/tmp/test"), buffer_size=512)
    
    def test_date_range_validation(self):
        """Test date range validation."""
        # Test valid date range
        older = datetime(2023, 1, 1)
        newer = datetime(2023, 12, 31)
        config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            older_than=older,
            newer_than=newer
        )
        assert config.older_than == older
        assert config.newer_than == newer
        
        # Test invalid date range
        with pytest.raises(ValueError, match="older_than.*must be before.*newer_than"):
            ProcessingConfig(
                processing_dir=Path("/tmp/test"),
                older_than=newer,  # Swapped
                newer_than=older
            )
    
    def test_output_format_validation(self):
        """Test output format validation."""
        # Test valid formats
        config1 = ProcessingConfig(processing_dir=Path("/tmp/test"), output_format="html")
        config2 = ProcessingConfig(processing_dir=Path("/tmp/test"), output_format="xml")
        assert config1.output_format == "html"
        assert config2.output_format == "xml"
        
        # Test invalid format
        with pytest.raises(ValueError, match="output_format must be 'html' or 'xml'"):
            ProcessingConfig(processing_dir=Path("/tmp/test"), output_format="json")
    
    def test_effective_value_methods(self):
        """Test effective value calculation methods."""
        config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            test_mode=True,
            test_limit=50,
            enable_phone_prompts=True,
            output_format="xml"
        )
        
        assert config.is_test_mode() is True
        assert config.get_test_limit() == 50
        assert config.should_enable_phone_prompts() is False  # Disabled in test mode
        assert config.get_output_format() == "xml"
        assert config.get_processing_directory() == Path("/tmp/test")
        assert config.get_output_directory() == Path("/tmp/test/conversations")
    
    def test_serialization_methods(self):
        """Test configuration serialization and deserialization."""
        config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            output_format="xml",
            max_workers=8,
            enable_phone_prompts=True
        )
        
        # Test to_dict
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["processing_dir"] == "/tmp/test"
        assert config_dict["output_format"] == "xml"
        assert config_dict["max_workers"] == 8
        assert config_dict["enable_phone_prompts"] is True
        
        # Test from_dict
        restored_config = ProcessingConfig.from_dict(config_dict)
        assert restored_config.processing_dir == config.processing_dir
        assert restored_config.output_format == config.output_format
        assert restored_config.max_workers == config.max_workers
        assert restored_config.enable_phone_prompts == config.enable_phone_prompts


class TestConfigurationDefaults:
    """Test the ConfigurationDefaults class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        defaults = ConfigurationDefaults.get_defaults()
        
        assert defaults["max_workers"] == 16
        assert defaults["chunk_size"] == 1000
        assert defaults["enable_phone_prompts"] is False
        assert defaults["strict_mode"] is False
        assert defaults["test_mode"] is False
    
    def test_test_presets(self):
        """Test test mode preset values."""
        test_presets = ConfigurationDefaults.get_test_presets()
        
        assert test_presets["test_mode"] is True
        assert test_presets["test_limit"] == 100
        assert test_presets["full_run"] is False
        assert test_presets["enable_phone_prompts"] is False
        assert test_presets["strict_mode"] is True
        assert test_presets["enable_performance_monitoring"] is False
    
    def test_production_presets(self):
        """Test production mode preset values."""
        prod_presets = ConfigurationDefaults.get_production_presets()
        
        assert prod_presets["test_mode"] is False
        assert prod_presets["full_run"] is True
        assert prod_presets["enable_performance_monitoring"] is True
        assert prod_presets["enable_progress_logging"] is True
        assert prod_presets["strict_mode"] is False


class TestConfigurationBuilder:
    """Test the ConfigurationBuilder class."""
    
    def test_from_cli_args_basic(self):
        """Test building configuration from basic CLI arguments."""
        cli_args = {
            'processing_dir': '/tmp/test',
            'output_format': 'xml',
            'max_workers': 8,
            'phone_prompts': True
        }
        
        config = ConfigurationBuilder.from_cli_args(cli_args)
        
        assert config.processing_dir == Path("/tmp/test")
        assert config.output_format == "xml"
        assert config.max_workers == 8
        assert config.enable_phone_prompts is True
    
    def test_from_cli_args_missing_required(self):
        """Test that missing processing_dir raises error."""
        cli_args = {
            'output_format': 'xml'
        }
        
        with pytest.raises(ValueError, match="processing_dir is required"):
            ConfigurationBuilder.from_cli_args(cli_args)
    
    def test_from_cli_args_string_path(self):
        """Test that string paths are converted to Path objects."""
        cli_args = {
            'processing_dir': '/tmp/test'
        }
        
        config = ConfigurationBuilder.from_cli_args(cli_args)
        assert isinstance(config.processing_dir, Path)
        assert config.processing_dir == Path("/tmp/test")
    
    def test_from_cli_args_date_parsing(self):
        """Test date parsing from CLI arguments."""
        cli_args = {
            'processing_dir': '/tmp/test',
            'older_than': '2023-01-01',
            'newer_than': '2023-12-31'
        }
        
        config = ConfigurationBuilder.from_cli_args(cli_args)
        
        assert config.older_than == datetime(2023, 1, 1)
        assert config.newer_than == datetime(2023, 12, 31)
    
    def test_from_cli_args_date_parsing_failure(self):
        """Test that date parsing failures are handled gracefully."""
        cli_args = {
            'processing_dir': '/tmp/test',
            'older_than': 'invalid-date'
        }
        
        # Should not raise an error, just log a warning
        config = ConfigurationBuilder.from_cli_args(cli_args)
        assert config.older_than is None
    
    def test_create_with_presets(self):
        """Test creating configuration with presets."""
        # Test default preset
        config = ConfigurationBuilder.create_with_presets(Path("/tmp/test"))
        assert config.test_mode is False
        assert config.strict_mode is False
        
        # Test test preset
        test_config = ConfigurationBuilder.create_with_presets(Path("/tmp/test"), "test")
        assert test_config.test_mode is True
        assert test_config.strict_mode is True
        
        # Test production preset
        prod_config = ConfigurationBuilder.create_with_presets(Path("/tmp/test"), "production")
        assert prod_config.test_mode is False
        assert prod_config.full_run is True
    
    def test_merge_configs(self):
        """Test merging multiple configurations."""
        config1 = ProcessingConfig(
            processing_dir=Path("/tmp/test1"),
            max_workers=4,
            enable_phone_prompts=False
        )
        
        config2 = ProcessingConfig(
            processing_dir=Path("/tmp/test2"),
            max_workers=8,
            enable_phone_prompts=True
        )
        
        merged = ConfigurationBuilder.merge_configs(config1, config2)
        
        # Later config should override earlier config
        assert merged.processing_dir == Path("/tmp/test2")
        assert merged.max_workers == 8
        assert merged.enable_phone_prompts is True
    
    def test_merge_configs_single(self):
        """Test merging single configuration."""
        config = ProcessingConfig(processing_dir=Path("/tmp/test"))
        merged = ConfigurationBuilder.merge_configs(config)
        assert merged == config
    
    def test_merge_configs_empty(self):
        """Test that merging empty configs raises error."""
        with pytest.raises(ValueError, match="At least one configuration must be provided"):
            ConfigurationBuilder.merge_configs()


class TestConfigurationIntegration:
    """Test integration between configuration components."""
    
    def test_full_configuration_flow(self):
        """Test complete configuration flow from CLI to usage."""
        # Simulate CLI arguments
        cli_args = {
            'processing_dir': '/tmp/test',
            'output_format': 'xml',
            'phone_prompts': True,
            'strict_mode': True,
            'test_mode': False
        }
        
        # Build configuration
        config = ConfigurationBuilder.from_cli_args(cli_args)
        
        # Verify configuration
        assert config.get_output_format() == "xml"
        assert config.should_enable_phone_prompts() is True
        assert config.strict_mode is True
        assert config.is_test_mode() is False
        
        # Test serialization round-trip
        config_dict = config.to_dict()
        restored_config = ProcessingConfig.from_dict(config_dict)
        
        assert restored_config.get_output_format() == config.get_output_format()
        assert restored_config.should_enable_phone_prompts() == config.should_enable_phone_prompts()
        assert restored_config.strict_mode == config.strict_mode
    
    def test_configuration_with_presets_and_overrides(self):
        """Test creating configuration with presets and CLI overrides."""
        # Start with test preset
        base_config = ConfigurationBuilder.create_with_presets(Path("/tmp/test"), "test")
        
        # Override with CLI arguments
        cli_args = {
            'processing_dir': '/tmp/test',
            'phone_prompts': True,  # Override preset
            'output_format': 'xml'  # Override preset
        }
        
        cli_config = ConfigurationBuilder.from_cli_args(cli_args)
        
        # Merge configurations
        final_config = ConfigurationBuilder.merge_configs(base_config, cli_config)
        
        # Verify merged result
        assert final_config.test_mode is True  # From preset
        assert final_config.strict_mode is True  # From preset
        assert final_config.enable_phone_prompts is True  # From CLI override
        assert final_config.output_format == "xml"  # From CLI override


if __name__ == "__main__":
    pytest.main([__file__])
