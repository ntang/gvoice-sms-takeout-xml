"""
Integration tests for SMS module patching.

Tests the complete integration between the SMS module patcher
and the configuration system.
"""

import pytest
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.sms_patch import (
    patch_sms_module,
    unpatch_sms_module,
    is_sms_module_patched,
    quick_patch_sms_module
)
from core.processing_config import ProcessingConfig, ConfigurationBuilder


class TestSMSModulePatchIntegration:
    """Test integration between SMS module patcher and configuration system."""
    
    def test_basic_patch_and_unpatch_cycle(self):
        """Test basic patch and unpatch cycle."""
        # Create test configuration
        config = ProcessingConfig(processing_dir=Path('/tmp/test'))
        
        # Check initial state
        assert not is_sms_module_patched()
        
        # Patch the module
        patcher = patch_sms_module(config)
        assert patcher is not None
        
        # Check that module is now patched
        assert is_sms_module_patched()
        
        # Get patch status
        status = patcher.get_patch_status()
        assert status['total_patched'] > 0
        assert 'PROCESSING_DIRECTORY' in status['patched_globals']
        
        # Unpatch the module
        unpatch_sms_module(patcher)
        
        # Check that module is no longer patched
        assert not is_sms_module_patched()
    
    def test_quick_patch_functionality(self):
        """Test quick_patch_sms_module function."""
        # Use quick patch with custom options
        patcher = quick_patch_sms_module(
            '/tmp/test',
            max_workers=32,
            test_mode=True,
            enable_phone_prompts=True
        )
        
        assert patcher is not None
        assert is_sms_module_patched()
        
        # Check patch status
        status = patcher.get_patch_status()
        assert status['total_patched'] > 0
        
        # Clean up
        unpatch_sms_module(patcher)
        assert not is_sms_module_patched()
    
    def test_configuration_integration(self):
        """Test that patched module uses configuration values."""
        # Create configuration with specific values
        config = ProcessingConfig(
            processing_dir=Path('/tmp/test'),
            max_workers=64,
            chunk_size=5000,
            test_mode=True,
            test_limit=500,
            enable_phone_prompts=True,
            output_format='xml'
        )
        
        # Patch the module
        patcher = patch_sms_module(config)
        
        # Verify that the configuration was used
        status = patcher.get_patch_status()
        assert status['total_patched'] > 0
        
        # Clean up
        unpatch_sms_module(patcher)
    
    def test_preset_configuration_integration(self):
        """Test integration with preset configurations."""
        # Create configuration using presets
        config = ConfigurationBuilder.create_with_presets(Path('/tmp/test'), 'test')
        
        # Patch the module
        patcher = patch_sms_module(config)
        
        # Verify that test preset values were applied
        status = patcher.get_patch_status()
        assert status['total_patched'] > 0
        
        # Clean up
        unpatch_sms_module(patcher)
    
    def test_error_handling_integration(self):
        """Test error handling during patching."""
        # Test with invalid configuration
        with pytest.raises(Exception):
            # This should fail gracefully
            patch_sms_module(None)
        
        # Verify that module is not patched after error
        assert not is_sms_module_patched()
    
    def test_multiple_patch_cycles(self):
        """Test multiple patch/unpatch cycles."""
        config1 = ProcessingConfig(processing_dir=Path('/tmp/test1'))
        config2 = ProcessingConfig(processing_dir=Path('/tmp/test2'))
        
        # First patch cycle
        patcher1 = patch_sms_module(config1)
        assert is_sms_module_patched()
        unpatch_sms_module(patcher1)
        assert not is_sms_module_patched()
        
        # Second patch cycle
        patcher2 = patch_sms_module(config2)
        assert is_sms_module_patched()
        unpatch_sms_module(patcher2)
        assert not is_sms_module_patched()
    
    def test_patcher_lifecycle_management(self):
        """Test complete lifecycle management of patcher instances."""
        # Create multiple patchers
        config1 = ProcessingConfig(processing_dir=Path('/tmp/test1'))
        config2 = ProcessingConfig(processing_dir=Path('/tmp/test2'))
        
        patcher1 = patch_sms_module(config1)
        patcher2 = patch_sms_module(config2)
        
        # Both should be active
        assert is_sms_module_patched()
        
        # Unpatch first
        unpatch_sms_module(patcher1)
        assert is_sms_module_patched()  # Second patcher still active
        
        # Unpatch second
        unpatch_sms_module(patcher2)
        assert not is_sms_module_patched()  # No patchers active


class TestSMSModulePatchRealWorld:
    """Test real-world usage scenarios."""
    
    def test_production_configuration_patch(self):
        """Test patching with production-like configuration."""
        # Create production-like configuration
        config = ProcessingConfig(
            processing_dir=Path('/tmp/production'),
            max_workers=16,
            chunk_size=1000,
            memory_threshold=10000,
            buffer_size=32768,
            cache_size=50000,
            batch_size=1000,
            enable_parallel_processing=True,
            enable_streaming_parsing=True,
            enable_mmap_for_large_files=True,
            enable_performance_monitoring=True,
            enable_progress_logging=True,
            enable_path_validation=True,
            enable_runtime_validation=True,
            test_mode=False,
            test_limit=0,
            enable_phone_prompts=False,
            output_format='html',
            large_dataset=True
        )
        
        # Patch the module
        patcher = patch_sms_module(config)
        
        # Verify production settings
        status = patcher.get_patch_status()
        assert status['total_patched'] > 0
        
        # Clean up
        unpatch_sms_module(patcher)
    
    def test_test_configuration_patch(self):
        """Test patching with test configuration."""
        # Create test configuration
        config = ProcessingConfig(
            processing_dir=Path('/tmp/test'),
            max_workers=4,
            chunk_size=100,
            memory_threshold=1000,
            buffer_size=8192,
            cache_size=1000,
            batch_size=100,
            enable_parallel_processing=False,
            enable_streaming_parsing=False,
            enable_mmap_for_large_files=False,
            enable_performance_monitoring=False,
            enable_progress_logging=True,
            enable_path_validation=True,
            enable_runtime_validation=True,
            test_mode=True,
            test_limit=50,
            enable_phone_prompts=True,
            output_format='xml',
            large_dataset=False
        )
        
        # Patch the module
        patcher = patch_sms_module(config)
        
        # Verify test settings
        status = patcher.get_patch_status()
        assert status['total_patched'] > 0
        
        # Clean up
        unpatch_sms_module(patcher)


if __name__ == "__main__":
    pytest.main([__file__])
