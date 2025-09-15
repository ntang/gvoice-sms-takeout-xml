"""
Unit tests for the function signatures module.

Tests the updated function signatures that accept ProcessingConfig
objects while maintaining backward compatibility.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.function_signatures import (
    setup_processing_paths_with_config,
    setup_processing_paths_legacy,
    migrate_sms_module_to_configuration,
    get_effective_processing_config,
    validate_processing_config,
    create_processing_config_from_legacy
)
from core.processing_config import ProcessingConfig


class TestFunctionSignatures:
    """Test the function signature updates."""
    
    def test_create_processing_config_from_legacy_basic(self):
        """Test creating ProcessingConfig from basic legacy parameters."""
        config = create_processing_config_from_legacy(
            '/tmp/test',
            enable_phone_prompts=True,
            output_format='xml'
        )
        
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is True
        assert config.output_format == 'xml'
        assert config.test_mode is False  # Default preset
    
    def test_create_processing_config_from_legacy_with_preset(self):
        """Test creating ProcessingConfig from legacy parameters with test preset."""
        config = create_processing_config_from_legacy(
            '/tmp/test',
            enable_phone_prompts=True,
            output_format='xml',
            preset='test'
        )
        
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is True
        assert config.output_format == 'xml'
        assert config.test_mode is True  # Test preset
        assert config.strict_mode is True  # Test preset
    
    def test_create_processing_config_from_legacy_string_path(self):
        """Test creating ProcessingConfig from string path."""
        config = create_processing_config_from_legacy(
            '/tmp/test',
            buffer_size=16384,
            batch_size=500
        )
        
        assert config.processing_dir == Path('/tmp/test')
        assert config.buffer_size == 16384
        assert config.batch_size == 500
    
    def test_create_processing_config_from_legacy_path_object(self):
        """Test creating ProcessingConfig from Path object."""
        config = create_processing_config_from_legacy(
            Path('/tmp/test'),
            cache_size=50000,
            large_dataset=True
        )
        
        assert config.processing_dir == Path('/tmp/test')
        assert config.cache_size == 50000
        assert config.large_dataset is True
    
    def test_validate_processing_config_valid(self):
        """Test validation of valid processing configuration."""
        # Create a mock config with existing directory
        config = ProcessingConfig(processing_dir=Path.cwd())
        
        # Mock the directory structure
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True), \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.write_text'), \
             patch('pathlib.Path.unlink'), \
             patch('pathlib.Path.rglob', return_value=['file1.html', 'file2.html']):
            
            result = validate_processing_config(config)
            assert result is True
    
    def test_validate_processing_config_invalid_directory(self):
        """Test validation of configuration with invalid directory."""
        # Create a mock config with non-existent directory
        config = ProcessingConfig(processing_dir=Path('/non/existent/path'))
        
        with patch('pathlib.Path.exists', return_value=False):
            result = validate_processing_config(config)
            assert result is False
    
    def test_validate_processing_config_not_directory(self):
        """Test validation of configuration where path is not a directory."""
        # Create a mock config where path is not a directory
        config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=False):
            
            result = validate_processing_config(config)
            assert result is False
    
    def test_validate_processing_config_write_permission_failure(self):
        """Test validation when write permissions fail."""
        config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True), \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.write_text', side_effect=PermissionError("Permission denied")):
            
            result = validate_processing_config(config)
            assert result is False
    
    def test_get_effective_processing_config_no_config(self):
        """Test getting effective config when none is set."""
        # Clear any existing configuration
        from core.configuration_manager import get_configuration_manager
        manager = get_configuration_manager()
        manager.set_current_config(None)
        
        result = get_effective_processing_config()
        assert result is None
    
    def test_get_effective_processing_config_with_config(self):
        """Test getting effective config when one is set."""
        from core.configuration_manager import get_configuration_manager, set_global_configuration
        
        # Set a configuration
        config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        set_global_configuration(config)
        
        result = get_effective_processing_config()
        assert result == config
        assert result.processing_dir == Path('/tmp/test')


class TestSetupProcessingPaths:
    """Test the setup_processing_paths functions."""
    
    @patch('core.function_signatures.set_global_configuration')
    @patch('sms.setup_processing_paths')
    def test_setup_processing_paths_with_config(self, mock_setup, mock_set_global):
        """Test setup_processing_paths_with_config function."""
        config = ProcessingConfig(
            processing_dir=Path('/tmp/test'),
            enable_phone_prompts=True,
            buffer_size=16384,
            batch_size=500,
            cache_size=50000,
            large_dataset=True,
            output_format='xml'
        )
        
        setup_processing_paths_with_config(config)
        
        # Verify global configuration was set
        mock_set_global.assert_called_once_with(config)
        
        # Verify original function was called with correct parameters
        mock_setup.assert_called_once_with(
            processing_dir=Path('/tmp/test'),
            enable_phone_prompts=True,
            buffer_size=16384,
            batch_size=500,
            cache_size=50000,
            large_dataset=True,
            output_format='xml',
            phone_lookup_file=Path('/tmp/test/phone_lookup.txt')
        )
    
    @patch('core.function_signatures.setup_processing_paths_with_config')
    def test_setup_processing_paths_legacy(self, mock_setup_with_config):
        """Test setup_processing_paths_legacy function."""
        setup_processing_paths_legacy(
            '/tmp/test',
            enable_phone_prompts=True,
            buffer_size=16384,
            batch_size=500,
            cache_size=50000,
            large_dataset=True,
            output_format='xml'
        )
        
        # Verify the new function was called
        mock_setup_with_config.assert_called_once()
        
        # Get the config that was passed
        call_args = mock_setup_with_config.call_args
        config = call_args[0][0]  # First positional argument
        
        # Verify the config was created correctly
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is True
        assert config.buffer_size == 16384
        assert config.batch_size == 500
        assert config.cache_size == 50000
        assert config.large_dataset is True
        assert config.output_format == 'xml'
    
    @patch('core.function_signatures.setup_processing_paths_with_config')
    def test_setup_processing_paths_legacy_with_path_object(self, mock_setup_with_config):
        """Test setup_processing_paths_legacy with Path object."""
        setup_processing_paths_legacy(
            Path('/tmp/test'),
            enable_phone_prompts=False,
            output_format='html'
        )
        
        # Verify the new function was called
        mock_setup_with_config.assert_called_once()
        
        # Get the config that was passed
        call_args = mock_setup_with_config.call_args
        config = call_args[0][0]  # First positional argument
        
        # Verify the config was created correctly
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is False
        assert config.output_format == 'html'
    
    @patch('core.function_signatures.setup_processing_paths_with_config')
    def test_setup_processing_paths_legacy_with_overrides(self, mock_setup_with_config):
        """Test setup_processing_paths_legacy with parameter overrides."""
        setup_processing_paths_legacy(
            '/tmp/test',
            enable_phone_prompts=True,
            buffer_size=32768,
            preset='test'
        )
        
        # Verify the new function was called
        mock_setup_with_config.assert_called_once()
        
        # Get the config that was passed
        call_args = mock_setup_with_config.call_args
        config = call_args[0][0]  # First positional argument
        
        # Verify the config was created correctly with test preset
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is True
        assert config.buffer_size == 32768
        assert config.test_mode is True  # From test preset
        assert config.strict_mode is True  # From test preset


class TestMigrationFunctions:
    """Test the migration functions."""
    
    @patch('core.function_signatures.migrate_module_to_configuration')
    def test_migrate_sms_module_to_configuration(self, mock_migrate):
        """Test migrate_sms_module_to_configuration function."""
        # Mock the migration function
        mock_config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        mock_updates = {'ENABLE_PHONE_PROMPTS': True, 'OUTPUT_FORMAT': 'xml'}
        mock_migrate.return_value = (mock_config, mock_updates)
        
        # Test the migration
        result = migrate_sms_module_to_configuration('/tmp/test', 'test')
        
        # Verify the result
        assert result == mock_config
        assert result.processing_dir == Path('/tmp/test')
        
        # Verify the migration function was called
        mock_migrate.assert_called_once()
        
        # Get the call arguments
        call_args = mock_migrate.call_args
        module_arg = call_args[0][0]  # First positional argument
        processing_dir_arg = call_args[0][1]  # Second positional argument
        preset_arg = call_args[0][2]  # Third positional argument
        
        # Verify the arguments
        assert module_arg.__name__ == 'sms'  # Should be the sms module
        assert processing_dir_arg == Path('/tmp/test')
        assert preset_arg == 'test'
    
    @patch('core.function_signatures.migrate_module_to_configuration')
    def test_migrate_sms_module_to_configuration_with_path_object(self, mock_migrate):
        """Test migrate_sms_module_to_configuration with Path object."""
        # Mock the migration function
        mock_config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        mock_updates = {'ENABLE_PHONE_PROMPTS': False}
        mock_migrate.return_value = (mock_config, mock_updates)
        
        # Test the migration with Path object
        result = migrate_sms_module_to_configuration(Path('/tmp/test'), 'default')
        
        # Verify the result
        assert result == mock_config
        assert result.processing_dir == Path('/tmp/test')
        
        # Verify the migration function was called
        mock_migrate.assert_called_once()
        
        # Get the call arguments
        call_args = mock_migrate.call_args
        processing_dir_arg = call_args[0][1]  # Second positional argument
        preset_arg = call_args[0][2]  # Third positional argument
        
        # Verify the arguments
        assert processing_dir_arg == Path('/tmp/test')
        assert preset_arg == 'default'


class TestConfigurationOverrides:
    """Test configuration override functionality."""
    
    @patch('core.function_signatures.set_global_configuration')
    @patch('sms.setup_processing_paths')
    def test_setup_processing_paths_with_config_overrides(self, mock_setup, mock_set_global):
        """Test setup_processing_paths_with_config with parameter overrides."""
        config = ProcessingConfig(
            processing_dir=Path('/tmp/test'),
            enable_phone_prompts=False,  # Default value
            buffer_size=8192,  # Default value
            output_format='html'  # Default value
        )
        
        # Call with overrides
        setup_processing_paths_with_config(
            config,
            enable_phone_prompts=True,  # Override
            buffer_size=16384,  # Override
            output_format='xml'  # Override
        )
        
        # Verify global configuration was set
        mock_set_global.assert_called_once_with(config)
        
        # Verify original function was called with override values
        mock_setup.assert_called_once_with(
            processing_dir=Path('/tmp/test'),
            enable_phone_prompts=True,  # Override value
            buffer_size=16384,  # Override value
            batch_size=1000,  # Default from config
            cache_size=25000,  # Default from config
            large_dataset=False,  # Default from config
            output_format='xml',  # Override value
            phone_lookup_file=Path('/tmp/test/phone_lookup.txt')
        )
    
    @patch('core.function_signatures.set_global_configuration')
    @patch('sms.setup_processing_paths')
    def test_setup_processing_paths_with_config_no_overrides(self, mock_setup, mock_set_global):
        """Test setup_processing_paths_with_config without parameter overrides."""
        config = ProcessingConfig(
            processing_dir=Path('/tmp/test'),
            enable_phone_prompts=True,
            buffer_size=16384,
            batch_size=500,
            cache_size=50000,
            large_dataset=True,
            output_format='xml'
        )
        
        # Call without overrides
        setup_processing_paths_with_config(config)
        
        # Verify global configuration was set
        mock_set_global.assert_called_once_with(config)
        
        # Verify original function was called with config values
        mock_setup.assert_called_once_with(
            processing_dir=Path('/tmp/test'),
            enable_phone_prompts=True,  # From config
            buffer_size=16384,  # From config
            batch_size=500,  # From config
            cache_size=50000,  # From config
            large_dataset=True,  # From config
            output_format='xml',  # From config
            phone_lookup_file=Path('/tmp/test/phone_lookup.txt')
        )


if __name__ == "__main__":
    pytest.main([__file__])
