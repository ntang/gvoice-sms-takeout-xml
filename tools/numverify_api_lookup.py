#!/usr/bin/env python3
"""
NumVerify API Lookup Tool
Looks up phone numbers using NumVerify API to identify commercial/spam numbers.
"""

import csv
import json
import requests
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class NumVerifyAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Use HTTP (not HTTPS) for free tier - free tier doesn't support SSL
        self.base_url = "http://apilayer.net/api/validate"
        self.results = {
            'api_provider': 'NumVerify',
            'lookup_date': datetime.now().isoformat(),
            'total_numbers': 0,
            'successful_lookups': 0,
            'failed_lookups': 0,
            'commercial_numbers': 0,
            'spam_numbers': 0,
            'personal_numbers': 0,
            'invalid_numbers': 0,
            'cost_estimate': 0.0,
            'detailed_results': []
        }
    
    def lookup_phone(self, phone_number: str) -> Optional[Dict]:
        """
        Look up a single phone number using NumVerify API.
        
        Args:
            phone_number: Phone number to look up (e.g., +12025551234)
            
        Returns:
            Dict with lookup results or None if failed
        """
        try:
            # Remove + for NumVerify API
            clean_phone = phone_number.replace('+', '')
            
            params = {
                'access_key': self.api_key,
                'number': clean_phone,
                'country_code': '',
                'format': 1
            }
            
            # Increased timeout for free tier (can be slower)
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Debug: Print API response for troubleshooting
            print(f"   📊 API Response: {data}")
            
            # Check if we have valid data (some responses don't have 'success' field but have valid data)
            if data.get('success', False) or (data.get('valid') is not None and data.get('number')):
                return {
                    'phone_number': phone_number,
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
            else:
                # Check if there's an actual error message
                error_info = data.get('error', {})
                if isinstance(error_info, dict) and error_info.get('info'):
                    error_message = error_info.get('info')
                elif isinstance(error_info, str) and error_info:
                    error_message = error_info
                else:
                    # If no clear error but no valid data, it might be a rate limit or other issue
                    error_message = f"No valid data returned: {data}"
                
                print(f"   ❌ API Error: {error_message}")
                return {
                    'phone_number': phone_number,
                    'error': error_message,
                    'raw_response': data
                }
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Network Error: {str(e)}")
            return {
                'phone_number': phone_number,
                'error': f'API request failed: {str(e)}',
                'raw_response': None
            }
        except Exception as e:
            print(f"   ❌ Unexpected Error: {str(e)}")
            return {
                'phone_number': phone_number,
                'error': f'Unexpected error: {str(e)}',
                'raw_response': None
            }
    
    def log_run_details(self, start_time: datetime, end_time: datetime, total_numbers: int, successful: int, failed: int):
        """Log detailed run information for analysis."""
        duration = (end_time - start_time).total_seconds()
        
        log_entry = {
            'run_timestamp': start_time.isoformat(),
            'duration_seconds': duration,
            'total_numbers': total_numbers,
            'successful_lookups': successful,
            'failed_lookups': failed,
            'success_rate': (successful / total_numbers * 100) if total_numbers > 0 else 0,
            'average_time_per_request': duration / total_numbers if total_numbers > 0 else 0,
            'api_cost': successful * 0.01
        }
        
        return log_entry
    
    def process_numbers(self, input_file: str, output_file: str, delay: float = 2.0):
        """
        Process all numbers from input CSV file and collect raw NumVerify data.
        
        Args:
            input_file: Path to CSV file with phone numbers
            output_file: Path to output JSON file
            delay: Delay between API calls (seconds)
        """
        start_time = datetime.now()
        print(f"🚀 Starting NumVerify API raw data collection for {input_file}")
        print(f"⏱️  Delay between calls: {delay}s")
        print(f"📊 Mode: Raw data collection (no classification)")
        
        # Load input numbers
        numbers_to_process = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row['phone_number'].strip()
                if phone:
                    numbers_to_process.append({
                        'phone_number': phone,
                        'min_date': row.get('min_date', ''),
                        'max_date': row.get('max_date', ''),
                        'date_count': row.get('date_count', ''),
                        'original_notes': row.get('notes', '')
                    })
        
        self.results['total_numbers'] = len(numbers_to_process)
        print(f"📊 Processing {len(numbers_to_process)} phone numbers...")
        print(f"💰 Estimated cost: ${len(numbers_to_process) * 0.01:.2f}")
        
        # Process each number
        for i, number_info in enumerate(numbers_to_process, 1):
            phone = number_info['phone_number']
            print(f"🔍 [{i}/{len(numbers_to_process)}] Looking up: {phone}")
            
            # API lookup
            lookup_result = self.lookup_phone(phone)
            
            if lookup_result and 'error' not in lookup_result:
                self.results['successful_lookups'] += 1
                print(f"   ✅ Success: {lookup_result.get('country_name', 'Unknown')} - {lookup_result.get('carrier', 'Unknown carrier')}")
                
                # Store raw result with metadata
                detailed_result = {
                    'phone_number': phone,
                    'lookup_successful': True,
                    'valid': lookup_result.get('valid', False),
                    'number': lookup_result.get('number', ''),
                    'local_format': lookup_result.get('local_format', ''),
                    'international_format': lookup_result.get('international_format', ''),
                    'country_prefix': lookup_result.get('country_prefix', ''),
                    'country_code': lookup_result.get('country_code', ''),
                    'country_name': lookup_result.get('country_name', ''),
                    'location': lookup_result.get('location', ''),
                    'carrier': lookup_result.get('carrier', ''),
                    'line_type': lookup_result.get('line_type', ''),
                    'conversation_metadata': {
                        'min_date': number_info['min_date'],
                        'max_date': number_info['max_date'],
                        'date_count': number_info['date_count'],
                        'original_notes': number_info['original_notes']
                    },
                    'raw_api_response': lookup_result.get('raw_response', {})
                }
                
            else:
                self.results['failed_lookups'] += 1
                error_msg = lookup_result.get('error', 'Unknown error') if lookup_result else 'No response'
                print(f"   ❌ Failed: {error_msg}")
                
                # Store failed result with metadata
                detailed_result = {
                    'phone_number': phone,
                    'lookup_successful': False,
                    'error': error_msg,
                    'conversation_metadata': {
                        'min_date': number_info['min_date'],
                        'max_date': number_info['max_date'],
                        'date_count': number_info['date_count'],
                        'original_notes': number_info['original_notes']
                    },
                    'raw_api_response': lookup_result.get('raw_response', None) if lookup_result else None
                }
            
            self.results['detailed_results'].append(detailed_result)
            
            # Delay between calls to respect rate limits
            if i < len(numbers_to_process):
                time.sleep(delay)
        
        # Calculate final statistics
        end_time = datetime.now()
        self.results['cost_estimate'] = self.results['successful_lookups'] * 0.01
        self.results['run_log'] = self.log_run_details(start_time, end_time, len(numbers_to_process), 
                                                      self.results['successful_lookups'], 
                                                      self.results['failed_lookups'])
        
        # Export results
        self.export_raw_results(output_file)
        
        # Print summary
        self.print_summary()
    
    def export_raw_results(self, output_file: str):
        """Export raw NumVerify data to JSON file for analysis."""
        # Main raw data file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # Create summary file for quick analysis
        summary_file = output_file.replace('.json', '_summary.json')
        summary_data = {
            'run_summary': self.results['run_log'],
            'statistics': {
                'total_numbers': self.results['total_numbers'],
                'successful_lookups': self.results['successful_lookups'],
                'failed_lookups': self.results['failed_lookups'],
                'cost_estimate': self.results['cost_estimate']
            },
            'data_fields_available': [
                'phone_number', 'valid', 'number', 'local_format', 'international_format',
                'country_prefix', 'country_code', 'country_name', 'location', 
                'carrier', 'line_type', 'conversation_metadata', 'raw_api_response'
            ],
            'analysis_ready': True,
            'next_steps': [
                'Review raw data patterns',
                'Analyze carrier and line_type distributions', 
                'Develop classification rules based on actual data',
                'Implement classification as separate step'
            ]
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Raw data exported to: {output_file}")
        print(f"💾 Analysis summary exported to: {summary_file}")
    
    def print_summary(self):
        """Print raw data collection summary."""
        run_log = self.results.get('run_log', {})
        print(f"\n🎯 NUMVERIFY RAW DATA COLLECTION COMPLETE!")
        print(f"=" * 60)
        print(f"📊 Total numbers processed: {self.results['total_numbers']}")
        print(f"✅ Successful lookups: {self.results['successful_lookups']}")
        print(f"❌ Failed lookups: {self.results['failed_lookups']}")
        print(f"💰 Total API cost: ${self.results['cost_estimate']:.2f}")
        print(f"⏱️  Total duration: {run_log.get('duration_seconds', 0):.1f} seconds")
        print(f"📈 Success rate: {run_log.get('success_rate', 0):.1f}%")
        print(f"🔄 Avg time per request: {run_log.get('average_time_per_request', 0):.1f}s")
        
        print(f"\n📋 NEXT STEPS:")
        print(f"1. 📊 Review raw data patterns in exported JSON")
        print(f"2. 🔍 Analyze carrier and line_type distributions")
        print(f"3. 📝 Develop classification rules based on actual data")
        print(f"4. ⚙️  Implement classification as separate step")
        print(f"5. ✅ Validate classification against known examples")

def create_test_sample(input_file: str, test_file: str, sample_size: int = 10):
    """
    Create a test sample from the main input file.
    
    Args:
        input_file: Path to main CSV file
        test_file: Path to output test CSV file
        sample_size: Number of numbers to include in test sample
    """
    import random
    
    print(f"📊 Creating test sample from {input_file}")
    print(f"🎯 Sample size: {sample_size} numbers")
    
    # Load all numbers
    all_numbers = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            phone = row['phone_number'].strip()
            if phone:
                all_numbers.append(row)
    
    print(f"📁 Total numbers available: {len(all_numbers)}")
    
    # Select random sample
    if len(all_numbers) <= sample_size:
        sample_numbers = all_numbers
        print(f"⚠️ Dataset smaller than sample size, using all {len(all_numbers)} numbers")
    else:
        sample_numbers = random.sample(all_numbers, sample_size)
        print(f"🎲 Randomly selected {sample_size} numbers")
    
    # Export sample
    with open(test_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['phone_number', 'min_date', 'max_date', 'date_count', 'notes']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in sample_numbers:
            writer.writerow({
                'phone_number': row['phone_number'],
                'min_date': row.get('min_date', ''),
                'max_date': row.get('max_date', ''),
                'date_count': row.get('date_count', ''),
                'notes': f"Test sample - {row.get('notes', '')}"
            })
    
    print(f"✅ Test sample exported to: {test_file}")
    print(f"💰 Estimated test cost: ${len(sample_numbers) * 0.01:.2f}")
    
    # Show sample numbers
    print(f"\n📋 Sample numbers:")
    for i, row in enumerate(sample_numbers, 1):
        print(f"  {i}. {row['phone_number']} ({row.get('min_date', 'Unknown date')})")
    
    return test_file

def main():
    """Main function for NumVerify API raw data collection."""
    print("🚀 NumVerify API Raw Data Collection Tool")
    print("=" * 50)
    print("📊 Mode: Raw data collection (no classification)")
    print("🎯 Purpose: Gather NumVerify data for analysis and rule development")
    
    # Check if input file exists
    input_file = "properly_filtered_within_date_range.csv"
    if not Path(input_file).exists():
        print(f"❌ Input file not found: {input_file}")
        print("Please ensure the file exists before running this tool.")
        return
    
    # Ask user for mode
    print("🔧 Choose operation mode:")
    print("1. Test mode (10 numbers) - $0.10")
    print("2. Full mode (646 numbers) - $6.46")
    print("3. Custom mode (specify number count)")
    
    while True:
        try:
            choice = input("\nEnter choice (1/2/3): ").strip()
            if choice == "1":
                mode = "test"
                sample_size = 10
                break
            elif choice == "2":
                mode = "full"
                sample_size = None
                break
            elif choice == "3":
                mode = "custom"
                sample_size = int(input("Enter number of numbers to process: "))
                if sample_size <= 0:
                    print("❌ Sample size must be positive!")
                    continue
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
        except ValueError:
            print("❌ Invalid input. Please enter a number for custom mode.")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled.")
            return
    
    # Create test sample if needed
    if mode in ["test", "custom"]:
        test_file = f"test_sample_{sample_size}_numbers.csv"
        create_test_sample(input_file, test_file, sample_size)
        input_file = test_file
        print(f"\n📁 Using test file: {input_file}")
    
    # Get API key
    api_key = input("\n🔑 Enter your NumVerify API key: ").strip()
    if not api_key:
        print("❌ API key is required!")
        return
    
    # Free tier information
    if mode in ["test", "custom"]:
        print(f"\n💡 FREE TIER NOTES:")
        print(f"   • Using HTTP endpoint (free tier doesn't support HTTPS)")
        print(f"   • Increased timeout to 30 seconds (free tier can be slower)")
        print(f"   • 1,000 requests/month limit on free tier")
    
    # Set output file (now JSON for raw data)
    if mode == "test":
        output_file = "numverify_raw_test_data.json"
    elif mode == "custom":
        output_file = f"numverify_raw_custom_{sample_size}_data.json"
    else:
        output_file = "numverify_raw_all_646_data.json"
    
    # Show cost estimate
    if mode == "test":
        cost = 10 * 0.01
    elif mode == "custom":
        cost = sample_size * 0.01
    else:
        cost = 646 * 0.01
    
    print(f"\n💰 Estimated cost: ${cost:.2f}")
    print(f"📁 Input file: {input_file}")
    print(f"📁 Output file: {output_file}")
    
    # Confirm before proceeding
    if cost > 1.00:  # Only confirm for expensive operations
        confirm = input(f"\n⚠️ This will cost ${cost:.2f}. Continue? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Operation cancelled.")
            return
    
    # Initialize API client
    api_client = NumVerifyAPI(api_key)
    
    # Process numbers
    try:
        api_client.process_numbers(input_file, output_file, delay=2.0)
        print(f"\n✅ Lookup complete! Check {output_file} for results.")
        
        if mode == "test":
            print(f"\n🧪 TEST MODE COMPLETE!")
            print(f"✅ Raw data collection working correctly")
            print(f"✅ Review test data to validate NumVerify responses")
            print(f"✅ If satisfied, run again with mode 2 (Full mode)")
            print(f"✅ Ready for full raw data collection (646 numbers)")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Process interrupted by user.")
        print(f"Partial results may be available in {output_file}")
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")

if __name__ == "__main__":
    main()
