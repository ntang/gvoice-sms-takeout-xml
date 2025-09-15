#!/usr/bin/env python3
"""
Demo script for the Click CLI integration with unified configuration.
"""

import click
from pathlib import Path
from core.cli_integration import create_click_group_from_config
from core.unified_config import AppConfig


def main():
    """Main demo function."""
    print("🚀 Google Voice SMS Converter - CLI Integration Demo")
    print("=" * 60)
    
    # Create the Click group
    cli_group = create_click_group_from_config(AppConfig)
    
    print(f"✅ Created CLI group: {cli_group.name}")
    print(f"📋 Number of configuration options: {len(cli_group.params)}")
    print(f"🔧 Number of subcommands: {len(cli_group.commands)}")
    
    print("\n📋 Configuration Options:")
    for i, param in enumerate(cli_group.params[:10]):  # Show first 10
        print(f"  {i+1:2d}. {param.name}: {param.help}")
    
    if len(cli_group.params) > 10:
        print(f"  ... and {len(cli_group.params) - 10} more options")
    
    print("\n🔧 Available Commands:")
    for cmd_name, cmd in cli_group.commands.items():
        print(f"  {cmd_name}: {cmd.help}")
    
    print("\n🧪 Testing Configuration Creation:")
    
    # Test creating configuration with custom values
    try:
        config = AppConfig(
            processing_dir="/demo/path",
            max_workers=4,
            test_limit=25,
            debug=True
        )
        print(f"✅ Configuration created successfully")
        print(f"   Processing dir: {config.processing_dir}")
        print(f"   Max workers: {config.max_workers}")
        print(f"   Test limit: {config.test_limit}")
        print(f"   Debug: {config.debug}")
        
        # Test validation
        errors = config.get_validation_errors()
        if errors:
            print(f"❌ Validation errors: {errors}")
        else:
            print(f"✅ Configuration validation passed")
            
    except Exception as e:
        print(f"❌ Configuration creation failed: {e}")
    
    print("\n🎯 Next Steps:")
    print("  1. Run: python demo_cli.py --help")
    print("  2. Test subcommands: python demo_cli.py validate")
    print("  3. Test configuration: python demo_cli.py --max-workers 8 --test-limit 50 validate")


if __name__ == "__main__":
    # Create the CLI group and run it
    cli_group = create_click_group_from_config(AppConfig)
    cli_group()
