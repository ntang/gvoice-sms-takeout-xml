#!/usr/bin/env python3
"""
Minimal test to isolate the pydantic-settings issue.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from pydantic import Field, field_validator


class MinimalConfig(BaseSettings):
    """Minimal configuration to test the issue."""
    
    processing_dir: Path = Path('/default/path')
    
    class Config:
        env_prefix = "GVOICE_"
        env_file = ".env"
        extra = "ignore"


class MinimalConfigNew(BaseSettings):
    """Minimal configuration with new SettingsConfigDict style."""
    
    model_config = SettingsConfigDict(
        env_prefix="GVOICE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
        str_strip_whitespace=True,
        case_sensitive=False,
    )
    
    processing_dir: Path = Path('/default/path')


class MinimalConfigNoValidate(BaseSettings):
    """Minimal configuration with validate_default=False."""
    
    model_config = SettingsConfigDict(
        env_prefix="GVOICE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=False,
        str_strip_whitespace=True,
        case_sensitive=False,
    )
    
    processing_dir: Path = Path('/default/path')


class MinimalConfigWithAlias(BaseSettings):
    """Minimal configuration with alias field."""
    
    model_config = SettingsConfigDict(
        env_prefix="GVOICE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
        str_strip_whitespace=True,
        case_sensitive=False,
    )
    
    processing_dir: Path = Field(
        default=Path('/default/path'),
        description="Test path field",
        alias="processing_directory"
    )


class MinimalConfigWithValidator(BaseSettings):
    """Minimal configuration with field validator."""
    
    model_config = SettingsConfigDict(
        env_prefix="GVOICE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
        str_strip_whitespace=True,
        case_sensitive=False,
    )
    
    processing_dir: Path = Field(
        default=Path('/default/path'),
        description="Test path field"
    )
    
    @field_validator('processing_dir', mode='before')
    @classmethod
    def validate_processing_dir(cls, v):
        """Convert string to Path and resolve to absolute path."""
        if isinstance(v, str):
            v = Path(v)
        if isinstance(v, Path):
            return v.resolve()
        return v


def test_minimal():
    """Test the minimal configuration."""
    print("🧪 Testing Minimal Configuration (old style):")
    print("=" * 40)
    
    # Test 1: No arguments
    config1 = MinimalConfig()
    print(f"1. No args: {config1.processing_dir}")
    
    # Test 2: With explicit path
    config2 = MinimalConfig(processing_dir='/custom/path')
    print(f"2. With path: {config2.processing_dir}")
    
    # Test 3: Comparison
    print(f"   Same value: {config1.processing_dir == config2.processing_dir}")
    print(f"   Expected: {config1.processing_dir == Path('/default/path')}")
    print(f"   Custom: {config2.processing_dir == Path('/custom/path')}")
    print()


def test_minimal_new():
    """Test the minimal configuration with new style."""
    print("🧪 Testing Minimal Configuration (new style):")
    print("=" * 40)
    
    # Test 1: No arguments
    config1 = MinimalConfigNew()
    print(f"1. No args: {config1.processing_dir}")
    
    # Test 2: With explicit path
    config2 = MinimalConfigNew(processing_dir='/custom/path')
    print(f"2. With path: {config2.processing_dir}")
    
    # Test 3: Comparison
    print(f"   Same value: {config1.processing_dir == config2.processing_dir}")
    print(f"   Expected: {config1.processing_dir == Path('/default/path')}")
    print(f"   Custom: {config2.processing_dir == Path('/custom/path')}")
    print()


def test_minimal_no_validate():
    """Test the minimal configuration with validate_default=False."""
    print("🧪 Testing Minimal Configuration (validate_default=False):")
    print("=" * 40)
    
    # Test 1: No arguments
    config1 = MinimalConfigNoValidate()
    print(f"1. No args: {config1.processing_dir}")
    
    # Test 2: With explicit path
    config2 = MinimalConfigNoValidate(processing_dir='/custom/path')
    print(f"2. With path: {config2.processing_dir}")
    
    # Test 3: Comparison
    print(f"   Same value: {config1.processing_dir == config2.processing_dir}")
    print(f"   Expected: {config1.processing_dir == Path('/default/path')}")
    print(f"   Custom: {config2.processing_dir == Path('/custom/path')}")
    print()


def test_minimal_with_alias():
    """Test the minimal configuration with alias field."""
    print("🧪 Testing Minimal Configuration (with alias):")
    print("=" * 40)
    
    # Test 1: No arguments
    config1 = MinimalConfigWithAlias()
    print(f"1. No args: {config1.processing_dir}")
    
    # Test 2: With explicit path
    config2 = MinimalConfigWithAlias(processing_dir='/custom/path')
    print(f"2. With path: {config2.processing_dir}")
    
    # Test 3: Comparison
    print(f"   Same value: {config1.processing_dir == config2.processing_dir}")
    print(f"   Expected: {config1.processing_dir == Path('/default/path')}")
    print(f"   Custom: {config2.processing_dir == Path('/custom/path')}")
    print()


def test_minimal_with_validator():
    """Test the minimal configuration with field validator."""
    print("🧪 Testing Minimal Configuration (with validator):")
    print("=" * 40)
    
    # Test 1: No arguments
    config1 = MinimalConfigWithValidator()
    print(f"1. No args: {config1.processing_dir}")
    
    # Test 2: With explicit path
    config2 = MinimalConfigWithValidator(processing_dir='/custom/path')
    print(f"2. With path: {config2.processing_dir}")
    
    # Test 3: Comparison
    print(f"   Same value: {config1.processing_dir == config2.processing_dir}")
    print(f"   Expected: {config1.processing_dir == Path('/default/path')}")
    print(f"   Custom: {config2.processing_dir == Path('/custom/path')}")
    print()


if __name__ == "__main__":
    test_minimal()
    test_minimal_new()
    test_minimal_no_validate()
    test_minimal_with_alias()
    test_minimal_with_validator()
