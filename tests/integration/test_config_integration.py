"""
Integration tests for the configuration system.

Tests that the new configuration system can work alongside
the existing codebase without breaking functionality.
"""

import pytest
from pathlib import Path
from core.processing_config import ProcessingConfig, ConfigurationBuilder


class TestConfigurationIntegration:
    """Test integration between configuration system and existing codebase."""
    
    def test_configuration_with_existing_paths(self):
        """Test that configuration works with existing path structures."""
        # Test with a realistic processing directory path
        processing_dir = Path(__file__).parent.parent.parent / "tests" / "data" / "test_data"
        
        config = ProcessingConfig(processing_dir=processing_dir)
        
        # Verify paths are set correctly
        assert config.processing_dir == processing_dir
        assert config.output_dir == processing_dir / "conversations"
        
        # Verify default values are reasonable
        # Note: Performance settings (max_workers, chunk_size, buffer_size) are now hardcoded
        # and not exposed in the configuration object
        assert config.large_dataset is False
    
    def test_configuration_builder_with_real_paths(self):
        """Test configuration builder with real file system paths."""
        # Use the current test directory as a processing directory
        current_dir = Path(__file__).parent.parent.parent
        
        # Test creating configuration with presets
        test_config = ConfigurationBuilder.create_with_presets(current_dir, "test")
        assert test_config.test_mode is True
        assert test_config.processing_dir == current_dir
        
        # Test creating configuration with CLI args
        cli_args = {
            'processing_dir': str(current_dir),
            'phone_prompts': True,
        }
        
        cli_config = ConfigurationBuilder.from_cli_args(cli_args)
        assert cli_config.processing_dir == current_dir
        assert cli_config.enable_phone_prompts is True
    
    def test_configuration_serialization_roundtrip(self):
        """Test that configuration can be serialized and deserialized correctly."""
        processing_dir = Path("/tmp/test")
        config = ProcessingConfig(
            processing_dir=processing_dir,
            enable_phone_prompts=True,
            strict_mode=True
        )
        
        # Serialize to dict
        config_dict = config.to_dict()
        
        # Verify serialization
        assert config_dict["processing_dir"] == "/tmp/test"
        assert config_dict["enable_phone_prompts"] is True
        assert config_dict["strict_mode"] is True
        
        # Deserialize from dict
        restored_config = ProcessingConfig.from_dict(config_dict)
        
        # Verify deserialization
        assert restored_config.processing_dir == config.processing_dir
        assert restored_config.enable_phone_prompts == config.enable_phone_prompts
        assert restored_config.strict_mode == config.strict_mode
    
    def test_configuration_validation(self):
        """Test that configuration validation works correctly."""
        # Test valid configuration
        valid_config = ProcessingConfig(
            processing_dir=Path("/tmp/test")
        )
        assert valid_config.processing_dir == Path("/tmp/test")
        
        # Note: ProcessingConfig no longer validates directory existence during construction
        # Directory validation happens during processing
        nonexistent_config = ProcessingConfig(processing_dir=Path("/nonexistent/path"))
        assert nonexistent_config.processing_dir == Path("/nonexistent/path")
    
    def test_configuration_presets(self):
        """Test that configuration presets work correctly."""
        processing_dir = Path("/tmp/test")
        
        # Test default preset
        default_config = ConfigurationBuilder.create_with_presets(processing_dir, "default")
        assert default_config.test_mode is False
        assert default_config.strict_mode is False
        
        # Test test preset
        test_config = ConfigurationBuilder.create_with_presets(processing_dir, "test")
        assert test_config.test_mode is True
        assert test_config.strict_mode is True
        
        # Test production preset
        prod_config = ConfigurationBuilder.create_with_presets(processing_dir, "production")
        assert prod_config.test_mode is False
        assert prod_config.full_run is True


if __name__ == "__main__":
    pytest.main([__file__])
