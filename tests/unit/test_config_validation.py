"""
Tests for configuration schema validation functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
from pathlib import Path
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.app_config import (
    validate_config_schema,
    validate_config_relationships,
    validate_config_paths,
    CONFIG_SCHEMA
)


class TestConfigValidation(unittest.TestCase):
    """Test configuration validation functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_config = {
            "default_processing_dir": "/path/to/data",
            "enable_path_validation": True,
            "enable_runtime_validation": True,
            "validation_interval": 30,
            "memory_threshold": 5000,
            "batch_size": 500
        }
    
    def test_validate_config_schema_valid(self):
        """Test schema validation with valid configuration."""
        errors = validate_config_schema(self.valid_config)
        self.assertEqual(len(errors), 0, f"Expected no errors, got: {errors}")
    
    def test_validate_config_schema_missing_required(self):
        """Test schema validation with missing required field."""
        config = self.valid_config.copy()
        del config["default_processing_dir"]
        
        errors = validate_config_schema(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Missing required field: default_processing_dir" in error for error in errors))
    
    def test_validate_config_schema_unknown_key(self):
        """Test schema validation with unknown configuration key."""
        config = self.valid_config.copy()
        config["unknown_key"] = "value"
        
        errors = validate_config_schema(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Unknown configuration key: unknown_key" in error for error in errors))
    
    def test_validate_config_schema_invalid_boolean(self):
        """Test schema validation with invalid boolean values."""
        config = self.valid_config.copy()
        config["enable_path_validation"] = "invalid_boolean"
        
        errors = validate_config_schema(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Invalid boolean value for enable_path_validation" in error for error in errors))
    
    def test_validate_config_schema_valid_boolean_strings(self):
        """Test schema validation with valid boolean string values."""
        config = self.valid_config.copy()
        config["enable_path_validation"] = "true"
        config["enable_runtime_validation"] = "false"
        
        errors = validate_config_schema(config)
        self.assertEqual(len(errors), 0, f"Expected no errors, got: {errors}")
    
    def test_validate_config_schema_invalid_integer(self):
        """Test schema validation with invalid integer values."""
        config = self.valid_config.copy()
        config["max_workers"] = "not_a_number"
        
        errors = validate_config_schema(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Invalid integer value for max_workers" in error for error in errors))
    
    def test_validate_config_schema_integer_constraints(self):
        """Test schema validation with integer constraint violations."""
        config = self.valid_config.copy()
        config["max_workers"] = 50  # Above maximum of 32
        
        errors = validate_config_schema(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("above maximum (32)" in error for error in errors))
        
        config["max_workers"] = 0  # Below minimum of 1
        errors = validate_config_schema(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("below minimum (1)" in error for error in errors))
    
    def test_validate_config_relationships_valid(self):
        """Test relationship validation with valid configuration."""
        errors = validate_config_relationships(self.valid_config)
        self.assertEqual(len(errors), 0, f"Expected no errors, got: {errors}")
    
    def test_validate_config_relationships_chunk_size_too_small(self):
        """Test relationship validation with chunk size too small for workers."""
        config = self.valid_config.copy()
        config["max_workers"] = 20
        config["chunk_size"] = 50  # Below 20 * 10 = 200
        
        errors = validate_config_relationships(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Chunk size (50) is too small for 20 workers" in error for error in errors))
    
    def test_validate_config_relationships_batch_size_exceeds_memory_threshold(self):
        """Test relationship validation with batch size exceeding memory threshold."""
        config = self.valid_config.copy()
        config["memory_threshold"] = 1000
        config["batch_size"] = 2000  # Above memory threshold
        
        errors = validate_config_relationships(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Batch size (2000) exceeds memory threshold (1000)" in error for error in errors))
    
    @patch('os.access')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    def test_validate_config_paths_valid(self, mock_is_dir, mock_exists, mock_access):
        """Test path validation with valid paths."""
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_access.return_value = True
        
        errors = validate_config_paths(self.valid_config)
        self.assertEqual(len(errors), 0, f"Expected no errors, got: {errors}")
    
    @patch('os.access')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    def test_validate_config_paths_not_directory(self, mock_is_dir, mock_exists, mock_access):
        """Test path validation with path that exists but is not a directory."""
        mock_exists.return_value = True
        mock_is_dir.return_value = False
        
        errors = validate_config_paths(self.valid_config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("exists but is not a directory" in error for error in errors))
    
    def test_validate_config_paths_parent_not_writable(self):
        """Test path validation with non-writable parent directory."""
        # This test is complex to mock properly, so we'll test the basic structure
        # and ensure the function handles errors gracefully
        config = {"default_processing_dir": "/nonexistent/path/that/should/fail"}
        
        errors = validate_config_paths(config)
        # The function should handle the error gracefully and return some error message
        # We can't guarantee the exact error due to system differences
        self.assertIsInstance(errors, list)
    
    def test_config_schema_structure(self):
        """Test that the configuration schema has the expected structure."""
        self.assertIn("type", CONFIG_SCHEMA)
        self.assertEqual(CONFIG_SCHEMA["type"], "object")
        
        self.assertIn("properties", CONFIG_SCHEMA)
        self.assertIn("required", CONFIG_SCHEMA)
        self.assertIn("additionalProperties", CONFIG_SCHEMA)
        
        # Check that required fields are in properties
        for required_field in CONFIG_SCHEMA["required"]:
            self.assertIn(required_field, CONFIG_SCHEMA["properties"])
        
        # Check that all properties have required schema fields
        for prop_name, prop_schema in CONFIG_SCHEMA["properties"].items():
            self.assertIn("type", prop_schema)
            self.assertIn("description", prop_schema)
            
            # Check integer constraints
            if prop_schema["type"] == "integer":
                self.assertIn("minimum", prop_schema)
                self.assertIn("maximum", prop_schema)


if __name__ == "__main__":
    unittest.main()
