#!/usr/bin/env python3
"""
Test script to compare regular Pydantic vs pydantic-settings behavior.
"""

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class TestPydanticModel(BaseModel):
    """Regular Pydantic model for comparison."""
    path: Path = Field(
        default_factory=lambda: Path.cwd().parent / 'test',
        description="Test path field"
    )


class TestPydanticSettings(BaseSettings):
    """Pydantic-settings model for comparison."""
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
        default_factory=lambda: Path.cwd().parent / 'test',
        description="Test path field"
    )


class TestPydanticSettingsSimple(BaseSettings):
    """Pydantic-settings model with simple default."""
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
        default=Path.cwd().parent / 'test',
        description="Test path field"
    )


class TestStringField(BaseSettings):
    """Test with a string field to see if it's Path-specific."""
    model_config = SettingsConfigDict(
        env_prefix="TEST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
        str_strip_whitespace=True,
        case_sensitive=False,
    )
    
    text: str = Field(
        default="default text",
        description="Test string field"
    )


def test_regular_pydantic():
    """Test regular Pydantic behavior."""
    print("🧪 Testing Regular Pydantic Model:")
    print("=" * 40)
    
    # Test 1: No arguments
    model1 = TestPydanticModel()
    print(f"1. No args: {model1.path}")
    
    # Test 2: With explicit path
    model2 = TestPydanticModel(path='/custom/test/path')
    print(f"2. With path: {model2.path}")
    
    # Test 3: Comparison
    print(f"   Same object: {model1.path is model2.path}")
    print(f"   Same value: {model1.path == model2.path}")
    print(f"   Expected: {model1.path == Path.cwd().parent / 'test'}")
    print(f"   Custom: {model2.path == Path('/custom/test/path')}")
    print()


def test_pydantic_settings():
    """Test pydantic-settings behavior."""
    print("🧪 Testing Pydantic-Settings Model (default_factory):")
    print("=" * 40)
    
    # Test 1: No arguments
    model1 = TestPydanticSettings()
    print(f"1. No args: {model1.path}")
    
    # Test 2: With explicit path
    model2 = TestPydanticSettings(path='/custom/test/path')
    print(f"2. With path: {model2.path}")
    
    # Test 3: Comparison
    print(f"   Same object: {model1.path is model2.path}")
    print(f"   Same value: {model1.path == model2.path}")
    print(f"   Expected: {model1.path == Path.cwd().parent / 'test'}")
    print(f"   Custom: {model2.path == Path('/custom/test/path')}")
    print()


def test_pydantic_settings_simple():
    """Test pydantic-settings behavior with simple default."""
    print("🧪 Testing Pydantic-Settings Model (simple default):")
    print("=" * 40)
    
    # Test 1: No arguments
    model1 = TestPydanticSettingsSimple()
    print(f"1. No args: {model1.path}")
    
    # Test 2: With explicit path
    model2 = TestPydanticSettingsSimple(path='/custom/test/path')
    print(f"2. With path: {model2.path}")
    
    # Test 3: Comparison
    print(f"   Same object: {model1.path is model2.path}")
    print(f"   Same value: {model1.path == model2.path}")
    print(f"   Expected: {model1.path == Path.cwd().parent / 'test'}")
    print(f"   Custom: {model2.path == Path('/custom/test/path')}")
    print()


def test_string_field():
    """Test with a string field to see if it's Path-specific."""
    print("🧪 Testing String Field:")
    print("=" * 40)
    
    # Test 1: No arguments
    model1 = TestStringField()
    print(f"1. No args: {model1.text}")
    
    # Test 2: With explicit text
    model2 = TestStringField(text='custom text')
    print(f"2. With text: {model2.text}")
    
    # Test 3: Comparison
    print(f"   Same object: {model1.text is model2.text}")
    print(f"   Same value: {model1.text == model2.text}")
    print(f"   Expected: {model1.text == 'default text'}")
    print(f"   Custom: {model2.text == 'custom text'}")
    print()


def test_field_inspection():
    """Inspect the field definitions."""
    print("🔍 Field Inspection:")
    print("=" * 40)
    
    # Regular Pydantic
    pydantic_field = TestPydanticModel.model_fields['path']
    print(f"Regular Pydantic field:")
    print(f"  Default: {pydantic_field.default}")
    print(f"  Default factory: {pydantic_field.default_factory}")
    print(f"  Has default: {hasattr(pydantic_field, 'has_default')}")
    
    # Pydantic-settings
    settings_field = TestPydanticSettings.model_fields['path']
    print(f"Pydantic-settings field (default_factory):")
    print(f"  Default: {settings_field.default}")
    print(f"  Default factory: {settings_field.default_factory}")
    print(f"  Has default: {hasattr(settings_field, 'has_default')}")
    
    # Pydantic-settings simple
    settings_simple_field = TestPydanticSettingsSimple.model_fields['path']
    print(f"Pydantic-settings field (simple default):")
    print(f"  Default: {settings_simple_field.default}")
    print(f"  Default factory: {settings_simple_field.default_factory}")
    print(f"  Has default: {hasattr(settings_simple_field, 'has_default')}")
    
    # String field
    string_field = TestStringField.model_fields['text']
    print(f"String field:")
    print(f"  Default: {string_field.default}")
    print(f"  Default factory: {string_field.default_factory}")
    print(f"  Has default: {hasattr(string_field, 'has_default')}")
    print()


if __name__ == "__main__":
    test_field_inspection()
    test_regular_pydantic()
    test_pydantic_settings()
    test_pydantic_settings_simple()
    test_string_field()
