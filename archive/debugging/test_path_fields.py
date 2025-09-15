#!/usr/bin/env python3
"""
Test script for Path field behavior in Pydantic.
"""

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class TestPathStringDefault(BaseModel):
    """Test Path field with string default."""
    path: Path = Field(
        default='/default/path',
        description="Path with string default"
    )


class TestPathPathDefault(BaseModel):
    """Test Path field with Path default."""
    path: Path = Field(
        default=Path('/default/path'),
        description="Path with Path default"
    )


class TestPathStringDefaultSettings(BaseSettings):
    """Test Path field with string default in pydantic-settings."""
    model_config = SettingsConfigDict(
        env_prefix="TEST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
        str_strip_whitespace=True,
        case_sensitive=False,
    )
    
    path: Path = Field(
        default='/default/path',
        description="Path with string default"
    )


class TestPathPathDefaultSettings(BaseSettings):
    """Test Path field with Path default in pydantic-settings."""
    model_config = SettingsConfigDict(
        env_prefix="TEST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
        str_strip_whitespace=True,
        case_sensitive=False,
    )
    
    path: Path = Field(
        default=Path('/default/path'),
        description="Path with Path default"
    )


def test_path_string_default():
    """Test Path field with string default."""
    print("🧪 Testing Path Field with String Default:")
    print("=" * 50)
    
    # Test 1: No arguments
    model1 = TestPathStringDefault()
    print(f"1. No args: {model1.path}")
    
    # Test 2: With explicit path
    model2 = TestPathStringDefault(path='/custom/path')
    print(f"2. With path: {model2.path}")
    
    # Test 3: Comparison
    print(f"   Same value: {model1.path == model2.path}")
    print(f"   Expected: {model1.path == Path('/default/path')}")
    print(f"   Custom: {model2.path == Path('/custom/path')}")
    print()


def test_path_path_default():
    """Test Path field with Path default."""
    print("🧪 Testing Path Field with Path Default:")
    print("=" * 50)
    
    # Test 1: No arguments
    model1 = TestPathPathDefault()
    print(f"1. No args: {model1.path}")
    
    # Test 2: With explicit path
    model2 = TestPathPathDefault(path='/custom/path')
    print(f"2. With path: {model2.path}")
    
    # Test 3: Comparison
    print(f"   Same value: {model1.path == model2.path}")
    print(f"   Expected: {model1.path == Path('/default/path')}")
    print(f"   Custom: {model2.path == Path('/custom/path')}")
    print()


def test_path_string_default_settings():
    """Test Path field with string default in pydantic-settings."""
    print("🧪 Testing Path Field with String Default (pydantic-settings):")
    print("=" * 50)
    
    # Test 1: No arguments
    model1 = TestPathStringDefaultSettings()
    print(f"1. No args: {model1.path}")
    
    # Test 2: With explicit path
    model2 = TestPathStringDefaultSettings(path='/custom/path')
    print(f"2. With path: {model2.path}")
    
    # Test 3: Comparison
    print(f"   Same value: {model1.path == model2.path}")
    print(f"   Expected: {model1.path == Path('/default/path')}")
    print(f"   Custom: {model2.path == Path('/custom/path')}")
    print()


def test_path_path_default_settings():
    """Test Path field with Path default in pydantic-settings."""
    print("🧪 Testing Path Field with Path Default (pydantic-settings):")
    print("=" * 50)
    
    # Test 1: No arguments
    model1 = TestPathPathDefaultSettings()
    print(f"1. No args: {model1.path}")
    
    # Test 2: With explicit path
    model2 = TestPathPathDefaultSettings(path='/custom/path')
    print(f"2. With path: {model2.path}")
    
    # Test 3: Comparison
    print(f"   Same value: {model1.path == model2.path}")
    print(f"   Expected: {model1.path == Path('/default/path')}")
    print(f"   Custom: {model2.path == Path('/custom/path')}")
    print()


def test_field_inspection():
    """Inspect the field definitions."""
    print("🔍 Field Inspection:")
    print("=" * 50)
    
    # String default
    string_field = TestPathStringDefault.model_fields['path']
    print(f"Path field with string default:")
    print(f"  Default: {string_field.default}")
    print(f"  Default factory: {string_field.default_factory}")
    
    # Path default
    path_field = TestPathPathDefault.model_fields['path']
    print(f"Path field with Path default:")
    print(f"  Default: {path_field.default}")
    print(f"  Default factory: {path_field.default_factory}")
    
    # String default settings
    string_settings_field = TestPathStringDefaultSettings.model_fields['path']
    print(f"Path field with string default (settings):")
    print(f"  Default: {string_settings_field.default}")
    print(f"  Default factory: {string_settings_field.default_factory}")
    
    # Path default settings
    path_settings_field = TestPathPathDefaultSettings.model_fields['path']
    print(f"Path field with Path default (settings):")
    print(f"  Default: {path_settings_field.default}")
    print(f"  Default factory: {path_settings_field.default_factory}")
    print()


if __name__ == "__main__":
    test_field_inspection()
    test_path_string_default()
    test_path_path_default()
    test_path_string_default_settings()
    test_path_path_default_settings()
