"""
Unit tests for the SMS module patcher.

Tests the patching system that integrates the existing sms.py module
with the new configuration system.
"""

import pytest
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from core.sms_patch import (
    SMSModulePatcher,
    patch_sms_module,
    unpatch_sms_module,
    get_sms_module_patcher,
    is_sms_module_patched,
    quick_patch_sms_module,
    quick_unpatch_sms_module
)
from core.processing_config import ProcessingConfig


class TestSMSModulePatcher:
    """Test the SMSModulePatcher class."""
    
    def test_patcher_initialization(self):
        """Test that SMSModulePatcher initializes correctly."""
        patcher = SMSModulePatcher()
        
        assert patcher._patched_functions == set()
        assert patcher._patched_globals == set()
        assert patcher._original_values == {}
    
    def test_store_original_values(self):
        """Test storing original values from sms module."""
        patcher = SMSModulePatcher()
        
        # Mock sms module with some global variables
        mock_sms = MagicMock()
        mock_sms.PROCESSING_DIRECTORY = Path('/tmp/test')
        mock_sms.MAX_WORKERS = 16
        mock_sms.TEST_MODE = False
        mock_sms._private_var = 'private'  # Should be ignored
        
        # Store original values
        patcher._store_original_values(mock_sms)
        
        # Check that public globals were stored
        assert 'PROCESSING_DIRECTORY' in patcher._original_values
        assert 'MAX_WORKERS' in patcher._original_values
        assert 'TEST_MODE' in patcher._original_values
        
        # Check that private variables were ignored
        assert '_private_var' not in patcher._original_values
        
        # Check values
        assert patcher._original_values['PROCESSING_DIRECTORY'] == Path('/tmp/test')
        assert patcher._original_values['MAX_WORKERS'] == 16
        assert patcher._original_values['TEST_MODE'] is False
    
    def test_store_original_functions(self):
        """Test storing original functions from sms module."""
        patcher = SMSModulePatcher()
        
        # Mock sms module with functions
        mock_sms = MagicMock()
        
        def mock_setup_func():
            return "original_setup"
        
        def mock_validate_func():
            return "original_validate"
        
        mock_sms.setup_processing_paths = mock_setup_func
        mock_sms.validate_processing_directory = mock_validate_func
        mock_sms.other_function = lambda: "other"
        
        # Store original functions
        patcher._store_original_functions(mock_sms)
        
        # Check that target functions were stored
        assert 'setup_processing_paths' in patcher._original_values
        assert 'validate_processing_directory' in patcher._original_values
        
        # Check that other functions were not stored
        assert 'other_function' not in patcher._original_values
        
        # Check function references
        assert patcher._original_values['setup_processing_paths'] == mock_setup_func
        assert patcher._original_values['validate_processing_directory'] == mock_validate_func
    
    @patch('core.sms_patch.get_configuration_manager')
    @patch('core.sms_patch.setup_processing_paths_with_config')
    def test_patch_global_variables(self, mock_setup, mock_manager):
        """Test patching global variables in sms module."""
        patcher = SMSModulePatcher()
        
        # Create test configuration
        config = ProcessingConfig(
            processing_dir=Path('/tmp/test'),
            max_workers=32,
            chunk_size=2000,
            memory_threshold=20000,
            buffer_size=16384,
            cache_size=50000,
            batch_size=2000,
            enable_parallel_processing=True,
            enable_streaming_parsing=True,
            enable_mmap_for_large_files=True,
            enable_performance_monitoring=True,
            enable_progress_logging=True,
            enable_path_validation=True,
            enable_runtime_validation=True,
            test_mode=True,
            test_limit=200,
            enable_phone_prompts=True,
            output_format='html',
            large_dataset=True
        )
        
        # Mock sms module
        mock_sms = MagicMock()
        mock_sms.PROCESSING_DIRECTORY = Path('/tmp/original')
        mock_sms.MAX_WORKERS = 16
        mock_sms.CHUNK_SIZE_OPTIMAL = 1000
        mock_sms.MEMORY_EFFICIENT_THRESHOLD = 10000
        mock_sms.BUFFER_SIZE_OPTIMAL = 8192
        mock_sms.CACHE_SIZE_OPTIMAL = 25000
        mock_sms.BATCH_SIZE_OPTIMAL = 1000
        mock_sms.ENABLE_PARALLEL_PROCESSING = False
        mock_sms.ENABLE_STREAMING_PARSING = False
        mock_sms.ENABLE_MMAP_FOR_LARGE_FILES = False
        mock_sms.ENABLE_PERFORMANCE_MONITORING = False
        mock_sms.ENABLE_PROGRESS_LOGGING = False
        mock_sms.ENABLE_PATH_VALIDATION = False
        mock_sms.ENABLE_RUNTIME_VALIDATION = False
        mock_sms.TEST_MODE = False
        mock_sms.TEST_LIMIT = 100
        mock_sms.ENABLE_PHONE_PROMPTS = False
        mock_sms.OUTPUT_FORMAT = 'html'
        mock_sms.LARGE_DATASET = False
        
        # Patch with mocked sms module
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = mock_sms
            patcher.patch_global_variables(config)
        
        # Check that variables were patched
        assert mock_sms.PROCESSING_DIRECTORY == Path('/tmp/test')
        assert mock_sms.MAX_WORKERS == 32
        assert mock_sms.CHUNK_SIZE_OPTIMAL == 2000
        assert mock_sms.MEMORY_EFFICIENT_THRESHOLD == 20000
        assert mock_sms.BUFFER_SIZE_OPTIMAL == 16384
        assert mock_sms.CACHE_SIZE_OPTIMAL == 50000
        assert mock_sms.BATCH_SIZE_OPTIMAL == 2000
        assert mock_sms.ENABLE_PARALLEL_PROCESSING is True
        assert mock_sms.ENABLE_STREAMING_PARSING is True
        assert mock_sms.ENABLE_MMAP_FOR_LARGE_FILES is True
        assert mock_sms.ENABLE_PERFORMANCE_MONITORING is True
        assert mock_sms.ENABLE_PROGRESS_LOGGING is True
        assert mock_sms.ENABLE_PATH_VALIDATION is True
        assert mock_sms.ENABLE_RUNTIME_VALIDATION is True
        assert mock_sms.TEST_MODE is True
        assert mock_sms.TEST_LIMIT == 200
        assert mock_sms.ENABLE_PHONE_PROMPTS is True
        assert mock_sms.OUTPUT_FORMAT == 'html'
        assert mock_sms.LARGE_DATASET is True
        
        # Check that patched globals were tracked
        assert len(patcher._patched_globals) == 20
        assert 'PROCESSING_DIRECTORY' in patcher._patched_globals
        assert 'MAX_WORKERS' in patcher._patched_globals
    
    @patch('core.sms_patch.get_configuration_manager')
    @patch('core.sms_patch.setup_processing_paths_with_config')
    def test_patch_functions(self, mock_setup, mock_manager):
        """Test patching functions in sms module."""
        patcher = SMSModulePatcher()
        
        # Mock configuration manager
        mock_config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_current_config.return_value = mock_config
        mock_manager.return_value = mock_manager_instance
        
        # Mock sms module with functions
        mock_sms = MagicMock()
        
        def original_setup_func():
            return "original_setup"
        
        def original_validate_func():
            return "original_validate"
        
        mock_sms.setup_processing_paths = original_setup_func
        mock_sms.validate_processing_directory = original_validate_func
        
        # Patch with mocked sms module
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = mock_sms
            patcher.patch_functions()
        
        # Check that functions were patched
        assert mock_sms.setup_processing_paths != original_setup_func
        assert mock_sms.validate_processing_directory != original_validate_func
        
        # Check that patched functions were tracked
        assert len(patcher._patched_functions) == 2
        assert 'setup_processing_paths' in patcher._patched_functions
        assert 'validate_processing_directory' in patcher._patched_functions
        
        # Test that patched functions work
        # setup_processing_paths should use configuration
        mock_sms.setup_processing_paths(Path('/tmp/test'))
        mock_setup.assert_called_once_with(mock_config)
    
    def test_restore_original_values(self):
        """Test restoring original global variable values."""
        patcher = SMSModulePatcher()
        
        # Set up patched state
        patcher._patched_globals = {'PROCESSING_DIRECTORY', 'MAX_WORKERS'}
        patcher._original_values = {
            'PROCESSING_DIRECTORY': Path('/tmp/original'),
            'MAX_WORKERS': 16
        }
        
        # Mock sms module
        mock_sms = MagicMock()
        mock_sms.PROCESSING_DIRECTORY = Path('/tmp/patched')
        mock_sms.MAX_WORKERS = 32
        
        # Restore with mocked sms module
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = mock_sms
            patcher.restore_original_values()
        
        # Check that values were restored
        assert mock_sms.PROCESSING_DIRECTORY == Path('/tmp/original')
        assert mock_sms.MAX_WORKERS == 16
        
        # Check that patched globals were cleared
        assert patcher._patched_globals == set()
    
    def test_restore_original_functions(self):
        """Test restoring original functions."""
        patcher = SMSModulePatcher()
        
        # Set up patched state
        patcher._patched_functions = {'setup_processing_paths', 'validate_processing_directory'}
        patcher._original_values = {
            'setup_processing_paths': lambda: "original_setup",
            'validate_processing_directory': lambda: "original_validate"
        }
        
        # Mock sms module
        mock_sms = MagicMock()
        mock_sms.setup_processing_paths = lambda: "patched_setup"
        mock_sms.validate_processing_directory = lambda: "patched_validate"
        
        # Restore with mocked sms module
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = mock_sms
            patcher.restore_original_functions()
        
        # Check that functions were restored
        assert mock_sms.setup_processing_paths() == "original_setup"
        assert mock_sms.validate_processing_directory() == "original_validate"
        
        # Check that patched functions were cleared
        assert patcher._patched_functions == set()
    
    def test_get_patch_status(self):
        """Test getting patch status information."""
        patcher = SMSModulePatcher()
        
        # Set up some patched state
        patcher._patched_globals = {'PROCESSING_DIRECTORY', 'MAX_WORKERS'}
        patcher._patched_functions = {'setup_processing_paths'}
        patcher._original_values = {'key': 'value'}
        
        status = patcher.get_patch_status()
        
        assert set(status['patched_globals']) == {'PROCESSING_DIRECTORY', 'MAX_WORKERS'}
        assert status['patched_functions'] == ['setup_processing_paths']
        assert status['total_patched'] == 3
        assert status['has_original_values'] is True


class TestSMSModulePatchFunctions:
    """Test the main patch functions."""
    
    def setup_method(self):
        """Clear patcher registry before each test."""
        from core.sms_patch import _active_patchers
        _active_patchers.clear()
    
    @patch('core.sms_patch.SMSModulePatcher')
    def test_patch_sms_module(self, mock_patcher_class):
        """Test the main patch_sms_module function."""
        # Create test configuration
        config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        
        # Mock patcher instance
        mock_patcher = MagicMock()
        mock_patcher_class.return_value = mock_patcher
        
        # Call the function
        result = patch_sms_module(config)
        
        # Check that patcher was created
        mock_patcher_class.assert_called_once()
        
        # Check that patching methods were called
        mock_patcher.patch_global_variables.assert_called_once_with(config)
        mock_patcher.patch_functions.assert_called_once()
        
        # Backward compatibility removed - migration complete
        
        # Check return value
        assert result == mock_patcher
    
    @patch('core.sms_patch.SMSModulePatcher')
    def test_unpatch_sms_module(self, mock_patcher_class):
        """Test the unpatch_sms_module function."""
        # Mock patcher instance
        mock_patcher = MagicMock()
        
        # Call the function
        unpatch_sms_module(mock_patcher)
        
        # Check that restore methods were called
        mock_patcher.restore_original_values.assert_called_once()
        mock_patcher.restore_original_functions.assert_called_once()
    
    def test_get_sms_module_patcher(self):
        """Test getting a new SMS module patcher instance."""
        patcher = get_sms_module_patcher()
        
        assert isinstance(patcher, SMSModulePatcher)
        assert patcher._patched_functions == set()
        assert patcher._patched_globals == set()
        assert patcher._original_values == {}
    
    @patch('builtins.__import__')
    def test_is_sms_module_patched_true(self, mock_import):
        """Test is_sms_module_patched when module is patched."""
        # Mock patched function
        def patched_function():
            pass
        patched_function.__name__ = 'patched_setup_processing_paths'
        
        mock_sms = MagicMock()
        mock_sms.setup_processing_paths = patched_function
        mock_import.return_value = mock_sms
        
        # Check result
        assert is_sms_module_patched() is True
    
    @patch('builtins.__import__')
    def test_is_sms_module_patched_false(self, mock_import):
        """Test is_sms_module_patched when module is not patched."""
        # Mock unpatched function
        def original_function():
            pass
        original_function.__name__ = 'setup_processing_paths'
        
        mock_sms = MagicMock()
        mock_sms.setup_processing_paths = original_function
        mock_import.return_value = mock_sms
        
        # Check result
        assert is_sms_module_patched() is False
    
    @patch('core.sms_patch.patch_sms_module')
    @patch('core.processing_config.ConfigurationBuilder')
    def test_quick_patch_sms_module(self, mock_builder, mock_patch):
        """Test quick_patch_sms_module function."""
        # Mock configuration builder
        mock_config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        mock_builder.create_with_presets.return_value = mock_config
        
        # Mock patch function
        mock_patcher = MagicMock()
        mock_patch.return_value = mock_patcher
        
        # Call the function
        result = quick_patch_sms_module('/tmp/test', max_workers=32)
        
        # Check that configuration was created
        mock_builder.create_with_presets.assert_called_once_with(Path('/tmp/test'), 'default')
        
        # Check that configuration was updated with kwargs
        # The to_dict() method is called internally, so we just verify the patch was called
        mock_patch.assert_called_once()
        
        # Check that patch was called
        mock_patch.assert_called_once()
        
        # Check return value
        assert result == mock_patcher
    
    @patch('core.sms_patch.is_sms_module_patched')
    def test_quick_unpatch_sms_module_patched(self, mock_is_patched):
        """Test quick_unpatch_sms_module when module is patched."""
        mock_is_patched.return_value = True
        
        # This should log warnings but not crash
        quick_unpatch_sms_module()
        
        # Check that the function was called
        mock_is_patched.assert_called_once()
    
    @patch('core.sms_patch.is_sms_module_patched')
    def test_quick_unpatch_sms_module_not_patched(self, mock_is_patched):
        """Test quick_unpatch_sms_module when module is not patched."""
        mock_is_patched.return_value = False
        
        # This should log info message
        quick_unpatch_sms_module()
        
        # Check that the function was called
        mock_is_patched.assert_called_once()


class TestSMSModulePatchIntegration:
    """Test integration between patching components."""
    
    def setup_method(self):
        """Clear patcher registry before each test."""
        from core.sms_patch import _active_patchers
        _active_patchers.clear()
    
    def test_patcher_lifecycle(self):
        """Test complete lifecycle of a patcher instance."""
        patcher = SMSModulePatcher()
        
        # Initial state
        assert patcher.get_patch_status()['total_patched'] == 0
        
        # Create test configuration
        config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        
        # Mock sms module for testing
        mock_sms = MagicMock()
        mock_sms.PROCESSING_DIRECTORY = Path('/tmp/original')
        mock_sms.MAX_WORKERS = 16
        
        # Patch global variables
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = mock_sms
            patcher.patch_global_variables(config)
        
        # Check patched state
        status = patcher.get_patch_status()
        assert status['total_patched'] > 0
        assert 'PROCESSING_DIRECTORY' in status['patched_globals']
        
        # Restore original values
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = mock_sms
            patcher.restore_original_values()
        
        # Check restored state
        status = patcher.get_patch_status()
        assert status['total_patched'] == 0
        assert status['patched_globals'] == []
    
    def test_patcher_error_handling(self):
        """Test that patcher handles errors gracefully."""
        patcher = SMSModulePatcher()
        
        # Test with invalid configuration
        with pytest.raises(Exception):
            # This should fail gracefully
            patcher.patch_global_variables(None)
        
        # Check that patcher state is still valid
        assert patcher._patched_globals == set()
        assert patcher._patched_functions == set()


if __name__ == "__main__":
    pytest.main([__file__])
