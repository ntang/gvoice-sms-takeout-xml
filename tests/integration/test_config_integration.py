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
        assert config.max_workers > 0
        assert config.chunk_size > 0
        assert config.buffer_size >= 1024
    
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
            'output_format': 'xml'
        }
        
        cli_config = ConfigurationBuilder.from_cli_args(cli_args)
        assert cli_config.processing_dir == current_dir
        assert cli_config.enable_phone_prompts is True
        assert cli_config.output_format == "xml"
    
    def test_configuration_serialization_roundtrip(self):
        """Test that configuration can be serialized and deserialized correctly."""
        processing_dir = Path("/tmp/test")
        config = ProcessingConfig(
            processing_dir=processing_dir,
            output_format="xml",
            max_workers=8,
            enable_phone_prompts=True,
            strict_mode=True
        )
        
        # Serialize to dict
        config_dict = config.to_dict()
        
        # Verify serialization
        assert config_dict["processing_dir"] == "/tmp/test"
        assert config_dict["output_format"] == "xml"
        assert config_dict["max_workers"] == 8
        assert config_dict["enable_phone_prompts"] is True
        assert config_dict["strict_mode"] is True
        
        # Deserialize from dict
        restored_config = ProcessingConfig.from_dict(config_dict)
        
        # Verify deserialization
        assert restored_config.processing_dir == config.processing_dir
        assert restored_config.output_format == config.output_format
        assert restored_config.max_workers == config.max_workers
        assert restored_config.enable_phone_prompts == config.enable_phone_prompts
        assert restored_config.strict_mode == config.strict_mode
    
    def test_configuration_validation(self):
        """Test that configuration validation works correctly."""
        # Test valid configuration
        valid_config = ProcessingConfig(
            processing_dir=Path("/tmp/test"),
            max_workers=4,
            chunk_size=500,
            buffer_size=2048
        )
        assert valid_config.max_workers == 4
        
        # Test invalid configuration
        with pytest.raises(ValueError, match="max_workers must be >= 1"):
            ProcessingConfig(processing_dir=Path("/tmp/test"), max_workers=0)
        
        with pytest.raises(ValueError, match="buffer_size must be >= 1024"):
            ProcessingConfig(processing_dir=Path("/tmp/test"), buffer_size=512)
    
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
        assert test_config.enable_performance_monitoring is False
        
        # Test production preset
        prod_config = ConfigurationBuilder.create_with_presets(processing_dir, "production")
        assert prod_config.test_mode is False
        assert prod_config.full_run is True
        assert prod_config.enable_performance_monitoring is True


if __name__ == "__main__":
    pytest.main([__file__])
