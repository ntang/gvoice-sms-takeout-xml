#!/usr/bin/env python3
"""
Test runner script for sms.py unit tests

This script provides multiple ways to run the test suite:
1. Basic unittest runner
2. Pytest with coverage (if available)
3. Quick validation tests

Usage:
    python3 run_tests.py                    # Run basic tests
    python3 run_tests.py --pytest          # Run with pytest (if installed)
    python3 run_tests.py --coverage        # Run with coverage report
    python3 run_tests.py --quick           # Run quick validation only
"""

import sys
import subprocess

# os import removed - not used
from pathlib import Path


def run_basic_tests():
    """Run tests using the built-in unittest module."""
    print("🧪 Running basic unit tests...")
    try:
        import test_sms
        import unittest

        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_sms)

        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        return result.wasSuccessful()
    except Exception as e:
        print(f"❌ Error running basic tests: {e}")
        return False


def run_pytest_tests():
    """Run tests using pytest if available."""
    print("🚀 Running tests with pytest...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "test_sms_unified.py", "-v", "--tb=short"],
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pytest not found. Install with: pip install pytest")
        return False


def run_coverage_tests():
    """Run tests with coverage reporting."""
    print("📊 Running tests with coverage...")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "test_sms_unified.py",
                "--cov=sms",
                "--cov-report=term-missing",
                "--cov-report=html",
            ],
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pytest-cov not found. Install with: pip install pytest-cov")
        return False


def run_quick_validation():
    """Run quick validation tests."""
    print("⚡ Running quick validation tests...")

    try:
        # Test 1: Module import
        import sms

        print("✅ SMS module imports successfully")

        # Test 2: Configuration validation (with default paths)
        # Use the command-line interface to get proper test mode features
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "sms.py",
                "--test-mode",
                "--test-limit",
                "5",
                "--output-format",
                "xml",
                str(Path.cwd()),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print("✅ Configuration validation passes")
        else:
            print(f"⚠️  Configuration validation had issues: {result.stderr}")
            # Fall back to direct call for basic validation
            sms.setup_processing_paths(Path.cwd(), output_format="xml")
            sms.validate_configuration()
            print("✅ Configuration validation passes (fallback)")

        # Test 3: XML escaping
        test_text = "Hello & World <test>"
        escaped = sms.escape_xml(test_text)
        expected = "Hello &amp; World &lt;test&gt;"
        assert escaped == expected, f"Expected '{expected}', got '{escaped}'"
        print("✅ XML escaping works correctly")

        # Test 4: Time formatting
        elapsed_seconds = 3661  # 1 hour, 1 minute, 1 second
        formatted = sms.format_elapsed_time(elapsed_seconds)
        expected = "1 hours, 1 minutes"
        assert formatted == expected, f"Expected '{expected}', got '{formatted}'"
        print("✅ Time formatting works correctly")

        # Test 5: ConversionStats dataclass
        stats = sms.ConversionStats(num_sms=100, num_img=25, num_vcf=10)
        assert stats.num_sms == 100
        assert stats.num_img == 25
        assert stats.num_vcf == 10
        print("✅ ConversionStats dataclass works correctly")

        print("✅ All quick validation tests passed!")
        return True

    except Exception as e:
        print(f"❌ Quick validation failed: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are available."""
    print("🔍 Checking dependencies...")

    required_modules = [
        "unittest",
        "tempfile",
        "shutil",
        "os",
        "sys",
        "pathlib",
        "datetime",
        "phonenumbers",
        "bs4",
        "logging",
    ]

    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            missing_modules.append(module)

    if missing_modules:
        print(f"\n⚠️  Missing modules: {', '.join(missing_modules)}")
        print("Install with: pip install -r test_requirements.txt")
        return False

    print("✅ All required dependencies are available")
    return True


def main():
    """Main test runner function."""
    print("🧪 SMS.py Unit Test Runner")
    print("=" * 50)

    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install missing dependencies.")
        return 1

    # Parse command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg == "--pytest":
            success = run_pytest_tests()
        elif arg == "--coverage":
            success = run_coverage_tests()
        elif arg == "--quick":
            success = run_quick_validation()
        elif arg == "--help" or arg == "-h":
            print(__doc__)
            return 0
        else:
            print(f"❌ Unknown argument: {arg}")
            print("Use --help for usage information")
            return 1
    else:
        # Default: run basic tests
        success = run_basic_tests()

    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed successfully!")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
