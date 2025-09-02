"""
Unit tests for the configuration integration layer.

Tests the ConfigurationManager, ConfigurationHooks, and
ConfigurationMigration utilities.
"""

import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.configuration_manager import (
    ConfigurationManager, get_configuration_manager,
    set_global_configuration, get_global_configuration
)
from core.configuration_hooks import (
    ConfigurationIntegrator, ConfigurationValidator,
    with_configuration_validation, require_configuration,
    configuration_driven, is_phone_prompts_enabled
)
from core.configuration_migration import (
    ConfigurationMigrationHelper, get_migration_helper,
    migrate_module_to_configuration, validate_module_migration
)
from core.processing_config import ProcessingConfig, ConfigurationBuilder


class TestConfigurationManager:
    """Test the ConfigurationManager class."""
    
    def test_manager_initialization(self):
        """Test that ConfigurationManager initializes correctly."""
        manager = ConfigurationManager()
        
        assert manager._config_cache == {}
        assert manager._default_config is None
        assert manager._current_config is None
        assert manager._cache_ttl == 300
        assert manager._validation_interval == 60
    
    def test_set_and_get_default_config(self):
        """Test setting and getting default configuration."""
        manager = ConfigurationManager()
        config = ProcessingConfig(processing_dir=Path("/tmp/test"))
        
        manager.set_default_config(config)
        retrieved_config = manager.get_default_config()
        
        assert retrieved_config == config
        assert retrieved_config.processing_dir == Path("/tmp/test")
    
    def test_set_and_get_current_config(self):
        """Test setting and getting current configuration."""
        manager = ConfigurationManager()
        config = ProcessingConfig(processing_dir=Path("/tmp/test"))
        
        manager.set_current_config(config)
        retrieved_config = manager.get_current_config()
        
        assert retrieved_config == config
        assert retrieved_config.processing_dir == Path("/tmp/test")
    
    def test_get_effective_config_with_current(self):
        """Test getting effective configuration when current is set."""
        manager = ConfigurationManager()
        config = ProcessingConfig(processing_dir=Path("/tmp/test"))
        
        manager.set_current_config(config)
        effective_config = manager.get_effective_config()
        
        assert effective_config == config
    
    def test_get_effective_config_with_fallback(self):
        """Test getting effective configuration with fallback to default."""
        manager = ConfigurationManager()
        default_config = ProcessingConfig(processing_dir=Path("/tmp/default"))
        
        manager.set_default_config(default_config)
        effective_config = manager.get_effective_config()
        
        assert effective_config == default_config
    
    def test_get_effective_config_no_config(self):
        """Test getting effective configuration when none is available."""
        manager = ConfigurationManager()
        
        with pytest.raises(RuntimeError, match="No configuration available"):
            manager.get_effective_config()
    
    def test_build_config_from_preset(self):
        """Test building configuration from preset."""
        manager = ConfigurationManager()
        config = manager.build_config_from_preset(Path("/tmp/test"), "test")
        
        assert config.test_mode is True
        assert config.strict_mode is True
        assert config.processing_dir == Path("/tmp/test")
    
    def test_build_config_from_cli(self):
        """Test building configuration from CLI arguments."""
        manager = ConfigurationManager()
        cli_args = {
            'processing_dir': '/tmp/test',
            'phone_prompts': True,
            'output_format': 'xml'
        }
        
        config = manager.build_config_from_cli(cli_args)
        
        assert config.processing_dir == Path("/tmp/test")
        assert config.enable_phone_prompts is True
        assert config.output_format == "xml"
    
    def test_merge_configurations(self):
        """Test merging multiple configurations."""
        manager = ConfigurationManager()
        
        config1 = ProcessingConfig(processing_dir=Path("/tmp/test1"), max_workers=4)
        config2 = ProcessingConfig(processing_dir=Path("/tmp/test2"), max_workers=8)
        
        merged = manager.merge_configurations(config1, config2)
        
        # Later config should override earlier config
        assert merged.processing_dir == Path("/tmp/test2")
        assert merged.max_workers == 8
    
    def test_build_complete_configuration(self):
        """Test building complete configuration from all sources."""
        manager = ConfigurationManager()
        cli_args = {
            'processing_dir': '/tmp/test',
            'phone_prompts': True
        }
        
        config = manager.build_complete_configuration(
            '/tmp/test', cli_args, 'test', use_environment=False
        )
        
        assert config.test_mode is True
        assert config.enable_phone_prompts is True
        assert config.processing_dir == Path("/tmp/test")
    
    def test_configuration_caching(self):
        """Test that configurations are cached correctly."""
        manager = ConfigurationManager()
        
        # Build configuration twice
        config1 = manager.build_config_from_preset(Path("/tmp/test"), "test")
        config2 = manager.build_config_from_preset(Path("/tmp/test"), "test")
        
        # Should be the same object (cached)
        assert config1 is config2
        
        # Check cache stats
        stats = manager.get_cache_stats()
        assert stats['cache_size'] > 0
    
    def test_cache_clearing(self):
        """Test that cache can be cleared."""
        manager = ConfigurationManager()
        
        # Build some configurations
        manager.build_config_from_preset(Path("/tmp/test"), "test")
        assert manager.get_cache_stats()['cache_size'] > 0
        
        # Clear cache
        manager.clear_cache()
        assert manager.get_cache_stats()['cache_size'] == 0


class TestConfigurationHooks:
    """Test the configuration hooks and decorators."""
    
    def test_configuration_integrator_creation(self):
        """Test that ConfigurationIntegrator can be created."""
        integrator = ConfigurationIntegrator()
        assert integrator is not None
    
    def test_phone_prompts_setting_without_config(self):
        """Test phone prompts setting when no configuration is available."""
        # Should fall back to default value
        result = is_phone_prompts_enabled()
        assert result is False
    
    def test_configuration_validator_creation(self):
        """Test that ConfigurationValidator can be created."""
        validator = ConfigurationValidator()
        assert validator is not None
    
    def test_validate_output_format(self):
        """Test output format validation."""
        validator = ConfigurationValidator()
        
        assert validator.validate_output_format("html") is True
        assert validator.validate_output_format("xml") is True
        assert validator.validate_output_format("json") is False
    
    def test_validate_max_workers(self):
        """Test max workers validation."""
        validator = ConfigurationValidator()
        
        assert validator.validate_max_workers(1) is True
        assert validator.validate_max_workers(16) is True
        assert validator.validate_max_workers(64) is True
        assert validator.validate_max_workers(0) is False
        assert validator.validate_max_workers(65) is False
    
    def test_validate_buffer_size(self):
        """Test buffer size validation."""
        validator = ConfigurationValidator()
        
        assert validator.validate_buffer_size(1024) is True
        assert validator.validate_buffer_size(32768) is True
        assert validator.validate_buffer_size(1048576) is True
        assert validator.validate_buffer_size(512) is False
        assert validator.validate_buffer_size(2097152) is False


class TestConfigurationMigration:
    """Test the configuration migration utilities."""
    
    def test_migration_helper_creation(self):
        """Test that ConfigurationMigrationHelper can be created."""
        helper = get_migration_helper()
        assert helper is not None
    
    def test_global_variable_mapping(self):
        """Test global variable to configuration field mapping."""
        helper = get_migration_helper()
        mapping = helper.get_global_variable_mapping()
        
        # Check some key mappings
        assert mapping['ENABLE_PHONE_PROMPTS'] == 'enable_phone_prompts'
        assert mapping['ENABLE_TEST_MODE'] == 'test_mode'
        assert mapping['OUTPUT_FORMAT'] == 'output_format'
        
        # Check reverse mapping
        reverse_mapping = helper.get_reverse_mapping()
        assert reverse_mapping['enable_phone_prompts'] == 'ENABLE_PHONE_PROMPTS'
    
    def test_migratable_globals_list(self):
        """Test that migratable globals list is correct."""
        helper = get_migration_helper()
        globals_list = helper.get_migratable_globals()
        
        # Should contain expected global variables
        assert 'ENABLE_PHONE_PROMPTS' in globals_list
        assert 'ENABLE_TEST_MODE' in globals_list
        assert 'OUTPUT_FORMAT' in globals_list
        assert 'MAX_WORKERS' in globals_list
        
        # Should not contain non-migratable variables
        assert 'NON_EXISTENT_VAR' not in globals_list
    
    def test_mapping_functions(self):
        """Test mapping functions work correctly."""
        helper = get_migration_helper()
        
        # Test forward mapping
        assert helper.map_global_variable('ENABLE_PHONE_PROMPTS') == 'enable_phone_prompts'
        assert helper.map_global_variable('NON_EXISTENT') is None
        
        # Test reverse mapping
        assert helper.map_configuration_field('enable_phone_prompts') == 'ENABLE_PHONE_PROMPTS'
        assert helper.map_configuration_field('non_existent') is None


class TestConfigurationIntegration:
    """Test integration between configuration components."""
    
    def setup_method(self):
        """Set up test method - clear global configuration."""
        # Clear any existing global configuration
        try:
            manager = get_configuration_manager()
            manager.set_current_config(None)
        except:
            pass
    
    def test_manager_with_hooks_integration(self):
        """Test that ConfigurationManager works with ConfigurationHooks."""
        manager = get_configuration_manager()
        
        # Set up a configuration
        config = ProcessingConfig(processing_dir=Path("/tmp/test"))
        manager.set_current_config(config)
        
        # Test that hooks can access the configuration
        integrator = ConfigurationIntegrator()
        phone_prompts = integrator.get_phone_prompts_setting()
        
        # Should get the value from configuration
        assert phone_prompts == config.enable_phone_prompts
    
    def test_migration_with_manager_integration(self):
        """Test that migration utilities work with ConfigurationManager."""
        manager = get_configuration_manager()
        helper = get_migration_helper()
        
        # Create a simple object with some global variables (not MagicMock)
        class MockModule:
            ENABLE_PHONE_PROMPTS = True
            OUTPUT_FORMAT = "xml"
        
        mock_module = MockModule()
        
        # Create migration configuration
        config = helper.create_migration_config(mock_module, Path("/tmp/test"), "default")
        
        # Check that global values were migrated
        assert config.enable_phone_prompts is True
        assert config.output_format == "xml"
        
        # Set as current configuration
        manager.set_current_config(config)
        
        # Verify integration
        current_config = manager.get_current_config()
        assert current_config == config
    
    def test_complete_workflow(self):
        """Test complete configuration workflow from CLI to usage."""
        manager = get_configuration_manager()
        
        # Clear any existing configuration first
        manager.set_current_config(None)
        manager.set_default_config(None)
        
        # Build configuration from CLI
        cli_args = {
            'processing_dir': '/tmp/test',
            'phone_prompts': True,
            'output_format': 'xml'
        }
        
        config = manager.build_complete_configuration(
            '/tmp/test', cli_args, 'test', use_environment=False
        )
        
        # Set as global configuration
        set_global_configuration(config)
        
        # Verify configuration is set
        assert manager.get_current_config() == config
        
        # Test that hooks can access it
        phone_prompts = is_phone_prompts_enabled()
        
        # In test mode, phone prompts should be disabled (this is correct behavior)
        assert phone_prompts is False
        
        # But the underlying config should have phone_prompts enabled
        assert config.enable_phone_prompts is True
        
        # Test that manager can access it
        current_config = get_global_configuration()
        assert current_config == config
        
        # Test configuration values
        assert current_config.enable_phone_prompts is True
        assert current_config.output_format == "xml"
        assert current_config.test_mode is True


class TestConfigurationDecorators:
    """Test configuration decorators."""
    
    def setup_method(self):
        """Set up test method - clear global configuration."""
        # Clear any existing global configuration
        try:
            manager = get_configuration_manager()
            manager.set_current_config(None)
        except:
            pass
    
    def test_with_configuration_validation_decorator(self):
        """Test the with_configuration_validation decorator."""
        @with_configuration_validation
        def test_function():
            return "success"
        
        # Should execute without error
        result = test_function()
        assert result == "success"
    
    def test_require_configuration_decorator(self):
        """Test the require_configuration decorator."""
        @require_configuration
        def test_function():
            return "success"
        
        # Should fail when no configuration is available
        with pytest.raises(RuntimeError, match="Configuration required"):
            test_function()
    
    def test_configuration_driven_decorator(self):
        """Test the configuration_driven decorator."""
        @configuration_driven('enable_phone_prompts', default_value=False)
        def test_function(**kwargs):
            return kwargs.get('config_enable_phone_prompts', 'not_found')
        
        # Should use default value when no configuration
        result = test_function()
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
