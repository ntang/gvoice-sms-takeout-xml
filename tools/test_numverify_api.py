#!/usr/bin/env python3
"""
NumVerify API Test Tool
Tests the NumVerify API with a small sample of numbers to validate functionality
before using the full free tier allocation.
"""

import csv
import json
import requests
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class NumVerifyAPITester:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://apilayer.net/api/validate"
        self.test_results = {
            'api_provider': 'NumVerify',
            'test_date': datetime.now().isoformat(),
            'test_numbers': [],
            'successful_tests': 0,
            'failed_tests': 0,
            'api_working': False,
            'cost_estimate': 0.0
        }
    
    def test_single_number(self, phone_number: str) -> Dict:
        """
        Test a single phone number to validate API functionality.
        
        Args:
            phone_number: Phone number to test (e.g., +12025551234)
            
        Returns:
            Dict with test results
        """
        print(f"🧪 Testing: {phone_number}")
        
        try:
            # Remove + for NumVerify API
            clean_phone = phone_number.replace('+', '')
            
            params = {
                'access_key': self.api_key,
                'number': clean_phone,
                'country_code': '',
                'format': 1
            }
            
            print(f"   📡 Making API request...")
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            print(f"   📊 Response received: {response.status_code}")
            
            if data.get('success', False):
                result = {
                    'phone_number': phone_number,
                    'test_status': 'success',
                    'valid': data.get('valid', False),
                    'number': data.get('number', ''),
                    'local_format': data.get('local_format', ''),
                    'international_format': data.get('international_format', ''),
                    'country_prefix': data.get('country_prefix', ''),
                    'country_code': data.get('country_code', ''),
                    'country_name': data.get('country_name', ''),
                    'location': data.get('location', ''),
                    'carrier': data.get('carrier', ''),
                    'line_type': data.get('line_type', ''),
                    'raw_response': data
                }
                print(f"   ✅ Success: {data.get('country_name', 'Unknown')} - {data.get('carrier', 'Unknown carrier')}")
                return result
            else:
                error_info = data.get('error', {}).get('info', 'Unknown error')
                result = {
                    'phone_number': phone_number,
                    'test_status': 'api_error',
                    'error': error_info,
                    'raw_response': data
                }
                print(f"   ❌ API Error: {error_info}")
                return result
                
        except requests.exceptions.RequestException as e:
            result = {
                'phone_number': phone_number,
                'test_status': 'network_error',
                'error': f'Network error: {str(e)}',
                'raw_response': None
            }
            print(f"   ❌ Network Error: {str(e)}")
            return result
        except Exception as e:
            result = {
                'phone_number': phone_number,
                'test_status': 'unexpected_error',
                'error': f'Unexpected error: {str(e)}',
                'raw_response': None
            }
            print(f"   ❌ Unexpected Error: {str(e)}")
            return result
    
    def run_test_suite(self, test_numbers: List[str]) -> Dict:
        """
        Run tests on a small set of numbers.
        
        Args:
            test_numbers: List of phone numbers to test
            
        Returns:
            Dict with complete test results
        """
        print(f"🚀 NUMVERIFY API TEST SUITE")
        print(f"=" * 50)
        print(f"📊 Testing {len(test_numbers)} numbers...")
        print(f"💰 Estimated cost: ${len(test_numbers) * 0.01:.2f}")
        print()
        
        for i, phone in enumerate(test_numbers, 1):
            print(f"[{i}/{len(test_numbers)}] Testing: {phone}")
            result = self.test_single_number(phone)
            self.test_results['test_numbers'].append(result)
            
            if result['test_status'] == 'success':
                self.test_results['successful_tests'] += 1
                self.test_results['api_working'] = True
            else:
                self.test_results['failed_tests'] += 1
            
            print()  # Empty line for readability
            
            # Small delay between tests
            if i < len(test_numbers):
                time.sleep(0.5)
        
        self.test_results['cost_estimate'] = len(test_numbers) * 0.01
        return self.test_results
    
    def export_test_results(self, output_file: str):
        """Export test results to CSV and JSON files."""
        # Export CSV
        csv_file = output_file.replace('.json', '.csv')
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'phone_number', 'test_status', 'valid', 'carrier', 'line_type',
                'country_name', 'location', 'error', 'notes'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.test_results['test_numbers']:
                writer.writerow({
                    'phone_number': result['phone_number'],
                    'test_status': result['test_status'],
                    'valid': result.get('valid', ''),
                    'carrier': result.get('carrier', ''),
                    'line_type': result.get('line_type', ''),
                    'country_name': result.get('country_name', ''),
                    'location': result.get('location', ''),
                    'error': result.get('error', ''),
                    'notes': f"Test result - {result['test_status']}"
                })
        
        # Export JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Test results exported to: {csv_file}")
        print(f"💾 Detailed results exported to: {output_file}")
    
    def print_test_summary(self):
        """Print test summary."""
        print(f"\n🎯 NUMVERIFY API TEST COMPLETE!")
        print(f"=" * 50)
        print(f"📊 Total tests: {len(self.test_results['test_numbers'])}")
        print(f"✅ Successful: {self.test_results['successful_tests']}")
        print(f"❌ Failed: {self.test_results['failed_tests']}")
        print(f"💰 Cost: ${self.test_results['cost_estimate']:.2f}")
        
        if self.test_results['api_working']:
            print(f"🎉 API is working correctly! Ready for full implementation.")
        else:
            print(f"⚠️ API issues detected. Check your API key and try again.")
        
        print(f"\n📋 RECOMMENDATIONS:")
        if self.test_results['successful_tests'] > 0:
            print(f"✅ Proceed with full implementation")
            print(f"✅ API key is valid and working")
            print(f"✅ Response format is correct")
        else:
            print(f"❌ Fix API issues before full implementation")
            print(f"❌ Check API key validity")
            print(f"❌ Verify network connectivity")

def get_test_numbers() -> List[str]:
    """Get a small set of test numbers from the main dataset."""
    test_numbers = []
    
    # Try to get a sample from the main file
    main_file = Path("properly_filtered_within_date_range.csv")
    if main_file.exists():
        print(f"📁 Loading test numbers from {main_file}")
        with open(main_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 5:  # Only take first 5 numbers
                    break
                phone = row['phone_number'].strip()
                if phone:
                    test_numbers.append(phone)
    else:
        # Fallback test numbers
        print(f"📁 Using fallback test numbers")
        test_numbers = [
            "+12025551234",  # Test US number
            "+15551234567",  # Test US number
            "+18001234567",  # Test toll-free
            "+447700900123", # Test UK number
            "+33123456789"   # Test French number
        ]
    
    return test_numbers

def main():
    """Main function for NumVerify API testing."""
    print("🧪 NumVerify API Test Tool")
    print("=" * 50)
    print("This tool tests the NumVerify API with a small sample of numbers")
    print("to validate functionality before using your full free tier allocation.")
    print()
    
    # Get API key
    api_key = input("🔑 Enter your NumVerify API key: ").strip()
    if not api_key:
        print("❌ API key is required!")
        return
    
    # Get test numbers
    test_numbers = get_test_numbers()
    print(f"📊 Using {len(test_numbers)} test numbers: {', '.join(test_numbers)}")
    print()
    
    # Confirm before proceeding
    confirm = input(f"💰 This will cost ${len(test_numbers) * 0.01:.2f}. Continue? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Test cancelled.")
        return
    
    # Initialize tester
    tester = NumVerifyAPITester(api_key)
    
    try:
        # Run tests
        results = tester.run_test_suite(test_numbers)
        
        # Export results
        output_file = "numverify_test_results.json"
        tester.export_test_results(output_file)
        
        # Print summary
        tester.print_test_summary()
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrupted by user.")
        print(f"Partial results may be available.")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")

if __name__ == "__main__":
    main()
