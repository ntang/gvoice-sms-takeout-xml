#!/usr/bin/env python3
"""
DEPRECATED: This test file has been replaced by test_sms_unified.py

For better performance and maintainability, please use:
  python test_sms_unified.py --basic      # Basic tests only
  python test_sms_unified.py --full       # Full test suite
  python test_sms_unified.py --help       # See all options

This file will be removed in a future version.
"""

import sys
import os

# Add the current directory to the path so we can import sms
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the module under test
import sms

# Import tests from unified file
from test_sms_unified import TestSMSBasic, TestSMSAdvanced, TestSMSIntegration

if __name__ == "__main__":
    print("DEPRECATED: This test file has been replaced by test_sms_unified.py")
    print("Please use: python test_sms_unified.py --help")
    print()

    # For backward compatibility, run basic tests
    import unittest

    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSMSBasic))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    sys.exit(0 if result.wasSuccessful() else 1)
