"""
Unit tests for the backward compatibility module.

Tests the backward compatibility layer that allows existing code to
continue working while gradually transitioning to the new configuration system.
"""

import pytest
import warnings
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.backward_compatibility import (
    BackwardCompatibilityManager,
    get_backward_compatibility_manager,
    setup_processing_paths_legacy_compat,
    validate_processing_directory_legacy_compat,
    create_legacy_compatibility_config,
    enable_backward_compatibility,
    disable_backward_compatibility,
    is_backward_compatibility_enabled
)
from core.processing_config import ProcessingConfig


class TestBackwardCompatibilityManager:
    """Test the BackwardCompatibilityManager class."""
    
    def test_manager_initialization(self):
        """Test that BackwardCompatibilityManager initializes correctly."""
        manager = BackwardCompatibilityManager()
        
        # Check that legacy functions were registered during initialization
        assert 'setup_processing_paths' in manager._legacy_functions
        assert 'validate_processing_directory' in manager._legacy_functions
        assert manager._global_variable_mappings == {}
        assert manager._migration_warnings == set()
    
    def test_register_legacy_function(self):
        """Test registering a custom legacy function wrapper."""
        manager = BackwardCompatibilityManager()
        
        def custom_wrapper():
            return "custom"
        
        manager.register_legacy_function('custom_function', custom_wrapper)
        
        assert 'custom_function' in manager._legacy_functions
        assert manager._legacy_functions['custom_function'] == custom_wrapper
    
    def test_get_legacy_function(self):
        """Test getting a legacy function wrapper."""
        manager = BackwardCompatibilityManager()
        
        # Get existing function
        func = manager.get_legacy_function('setup_processing_paths')
        assert func is not None
        
        # Try to get non-existent function
        with pytest.raises(ValueError, match="Unknown legacy function"):
            manager.get_legacy_function('non_existent_function')
    
    def test_create_config_from_legacy_params(self):
        """Test creating configuration from legacy parameters."""
        manager = BackwardCompatibilityManager()
        
        config = manager._create_config_from_legacy_params(
            processing_dir='/tmp/test',
            enable_phone_prompts=True,
            buffer_size=16384,
            batch_size=500,
            cache_size=50000,
            large_dataset=True,
            preset='test'
        )
        
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is True
        assert config.buffer_size == 16384
        assert config.batch_size == 500
        assert config.cache_size == 50000
        assert config.large_dataset is True
        assert config.output_format == 'html'
        assert config.test_mode is True  # From test preset
        assert config.strict_mode is True  # From test preset
    
    def test_create_config_from_legacy_params_with_path_object(self):
        """Test creating configuration from legacy parameters with Path object."""
        manager = BackwardCompatibilityManager()
        
        config = manager._create_config_from_legacy_params(
            processing_dir=Path('/tmp/test'),
            enable_phone_prompts=False,
        )
        
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is False
        assert config.output_format == 'html'
        assert config.test_mode is False  # Default preset
    
    def test_show_migration_warning(self):
        """Test that migration warnings are shown correctly."""
        manager = BackwardCompatibilityManager()
        
        # Show warning first time
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager._show_migration_warning('test_func', 'Use new_func instead')
            
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "test_func" in str(w[0].message)
            assert "Use new_func instead" in str(w[0].message)
        
        # Show warning again (should not duplicate)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager._show_migration_warning('test_func', 'Use new_func instead')
            
            # Should not show duplicate warning
            assert len(w) == 0
    
    @patch('core.function_signatures.setup_processing_paths_with_config')
    def test_setup_processing_paths_legacy_wrapper(self, mock_setup):
        """Test the legacy wrapper for setup_processing_paths."""
        manager = BackwardCompatibilityManager()
        
        # Test with deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            manager._setup_processing_paths_legacy_wrapper(
                '/tmp/test',
                enable_phone_prompts=True,
                buffer_size=16384,
            )
            
            # Check that deprecation warning was shown
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
        
        # Check that the new function was called
        mock_setup.assert_called_once()
        
        # Get the config that was passed
        call_args = mock_setup.call_args
        config = call_args[0][0]  # First positional argument
        
        # Verify the config was created correctly
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is True
        assert config.buffer_size == 16384
        assert config.output_format == 'html'
    
    @patch('core.function_signatures.validate_processing_config')
    def test_validate_processing_directory_legacy_wrapper(self, mock_validate):
        """Test the legacy wrapper for validate_processing_directory."""
        manager = BackwardCompatibilityManager()
        
        # Mock the validation function
        mock_validate.return_value = True
        
        # Test with deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            result = manager._validate_processing_directory_legacy_wrapper('/tmp/test')
            
            # Check that deprecation warning was shown
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
        
        # Check that the new function was called
        mock_validate.assert_called_once()
        
        # Get the config that was passed
        call_args = mock_validate.call_args
        config = call_args[0][0]  # First positional argument
        
        # Verify the config was created correctly
        assert config.processing_dir == Path('/tmp/test')
        
        # Check the result
        assert result is True
    
    @patch('core.backward_compatibility.migrate_module_to_configuration')
    def test_migrate_legacy_globals(self, mock_migrate):
        """Test migrating legacy global variables."""
        manager = BackwardCompatibilityManager()
        
        # Mock the migration function
        mock_config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        mock_updates = {'ENABLE_PHONE_PROMPTS': True, 'OUTPUT_FORMAT': 'html'}
        mock_migrate.return_value = (mock_config, mock_updates)
        
        # Test migration
        result = manager.migrate_legacy_globals(MagicMock(), '/tmp/test')
        
        # Check that the migration function was called
        mock_migrate.assert_called_once()
        
        # Check the result
        assert result == mock_config
        assert result.processing_dir == Path('/tmp/test')


class TestBackwardCompatibilityFunctions:
    """Test the backward compatibility functions."""
    
    def test_get_backward_compatibility_manager(self):
        """Test getting the global backward compatibility manager."""
        manager = get_backward_compatibility_manager()
        assert isinstance(manager, BackwardCompatibilityManager)
    
    @patch('core.function_signatures.setup_processing_paths_with_config')
    def test_setup_processing_paths_legacy_compat(self, mock_setup):
        """Test the legacy-compatible setup_processing_paths function."""
        # Test the function
        setup_processing_paths_legacy_compat(
            '/tmp/test',
            enable_phone_prompts=True,
            buffer_size=16384,
        )
        
        # Check that the new function was called
        mock_setup.assert_called_once()
        
        # Get the config that was passed
        call_args = mock_setup.call_args
        config = call_args[0][0]  # First positional argument
        
        # Verify the config was created correctly
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is True
        assert config.buffer_size == 16384
        assert config.output_format == 'html'
    
    @patch('core.function_signatures.validate_processing_config')
    def test_validate_processing_directory_legacy_compat(self, mock_validate):
        """Test the legacy-compatible validate_processing_directory function."""
        # Mock the validation function
        mock_validate.return_value = True
        
        # Test the function
        result = validate_processing_directory_legacy_compat('/tmp/test')
        
        # Check that the new function was called
        mock_validate.assert_called_once()
        
        # Get the config that was passed
        call_args = mock_validate.call_args
        config = call_args[0][0]  # First positional argument
        
        # Verify the config was created correctly
        assert config.processing_dir == Path('/tmp/test')
        
        # Check the result
        assert result is True
    
    def test_create_legacy_compatibility_config(self):
        """Test creating configuration from legacy parameters."""
        config = create_legacy_compatibility_config(
            '/tmp/test',
            enable_phone_prompts=True,
            buffer_size=16384,
            batch_size=500,
            cache_size=50000,
            large_dataset=True,
            preset='test'
        )
        
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is True
        assert config.buffer_size == 16384
        assert config.batch_size == 500
        assert config.cache_size == 50000
        assert config.large_dataset is True
        assert config.output_format == 'html'
        assert config.test_mode is True  # From test preset
        assert config.strict_mode is True  # From test preset
    
    def test_create_legacy_compatibility_config_with_path_object(self):
        """Test creating configuration from legacy parameters with Path object."""
        config = create_legacy_compatibility_config(
            Path('/tmp/test'),
            enable_phone_prompts=False,
        )
        
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is False
        assert config.output_format == 'html'
        assert config.test_mode is False  # Default preset


class TestBackwardCompatibilityMode:
    """Test backward compatibility mode enabling/disabling."""
    
    def test_enable_backward_compatibility(self):
        """Test enabling backward compatibility mode."""
        # Mock the sms module
        mock_sms = MagicMock()
        
        with patch.dict('sys.modules', {'sms': mock_sms}):
            enable_backward_compatibility()
            
            # Check that the functions were patched
            assert mock_sms.setup_processing_paths == setup_processing_paths_legacy_compat
            assert mock_sms.validate_processing_directory == validate_processing_directory_legacy_compat
    
    def test_disable_backward_compatibility(self):
        """Test disabling backward compatibility mode."""
        # Mock the sms module
        mock_sms = MagicMock()
        
        with patch.dict('sys.modules', {'sms': mock_sms}):
            disable_backward_compatibility()
            
            # Check that warnings were logged (function doesn't actually restore)
            # This test mainly ensures the function doesn't crash
    
    def test_is_backward_compatibility_enabled(self):
        """Test checking if backward compatibility mode is enabled."""
        # Mock the sms module with compatibility enabled
        mock_sms = MagicMock()
        mock_sms.setup_processing_paths = setup_processing_paths_legacy_compat
        
        with patch.dict('sys.modules', {'sms': mock_sms}):
            result = is_backward_compatibility_enabled()
            assert result is True
        
        # Mock the sms module with compatibility disabled
        mock_sms = MagicMock()
        mock_sms.setup_processing_paths = lambda: None
        
        with patch.dict('sys.modules', {'sms': mock_sms}):
            result = is_backward_compatibility_enabled()
            assert result is False
        
        # Test with import error
        with patch.dict('sys.modules', {}, clear=True):
            result = is_backward_compatibility_enabled()
            assert result is False


class TestBackwardCompatibilityIntegration:
    """Test integration between backward compatibility components."""
    
    def test_manager_with_legacy_functions(self):
        """Test that the manager works with legacy functions."""
        manager = get_backward_compatibility_manager()
        
        # Test setup_processing_paths wrapper
        setup_wrapper = manager.get_legacy_function('setup_processing_paths')
        assert setup_wrapper is not None
        
        # Test validate_processing_directory wrapper
        validate_wrapper = manager.get_legacy_function('validate_processing_directory')
        assert validate_wrapper is not None
    
    def test_legacy_function_registration(self):
        """Test registering and using custom legacy functions."""
        manager = get_backward_compatibility_manager()
        
        def custom_wrapper():
            return "custom_result"
        
        # Register custom function
        manager.register_legacy_function('custom_func', custom_wrapper)
        
        # Get and use the function
        func = manager.get_legacy_function('custom_func')
        result = func()
        
        assert result == "custom_result"
    
    def test_config_creation_integration(self):
        """Test that configuration creation works with the manager."""
        manager = get_backward_compatibility_manager()
        
        config = manager._create_config_from_legacy_params(
            '/tmp/test',
            enable_phone_prompts=True,
        )
        
        assert config.processing_dir == Path('/tmp/test')
        assert config.enable_phone_prompts is True
        assert config.output_format == 'html'
        assert isinstance(config, ProcessingConfig)


if __name__ == "__main__":
    pytest.main([__file__])
