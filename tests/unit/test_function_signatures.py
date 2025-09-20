"""
Unit tests for the function signatures module.

Tests the updated function signatures that accept ProcessingConfig
objects for the new architecture.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.function_signatures import (
    setup_processing_paths_with_config,
    migrate_sms_module_to_configuration,
    get_effective_processing_config,
    validate_processing_config
)
from core.processing_config import ProcessingConfig


class TestFunctionSignatures:
    """Test the function signature updates."""
    
    # Legacy function tests removed - migration complete
    
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
            phone_lookup_file=Path('/tmp/test/phone_lookup.txt')
        )
    
    # Legacy setup_processing_paths_legacy tests removed - migration complete


class TestMigrationFunctions:
    """Test the migration functions."""
    
    @patch('core.function_signatures.migrate_module_to_configuration')
    def test_migrate_sms_module_to_configuration(self, mock_migrate):
        """Test migrate_sms_module_to_configuration function."""
        # Mock the migration function
        mock_config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        mock_updates = {'ENABLE_PHONE_PROMPTS': True, 'OUTPUT_FORMAT': 'html'}
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
  # Default value
        )
        
        # Call with overrides
        setup_processing_paths_with_config(
            config,
            enable_phone_prompts=True,  # Override
            buffer_size=16384,  # Override
  # Override
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
            phone_lookup_file=Path('/tmp/test/phone_lookup.txt')
        )


if __name__ == "__main__":
    pytest.main([__file__])
