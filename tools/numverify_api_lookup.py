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
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success', False):
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
                return {
                    'phone_number': phone_number,
                    'error': data.get('error', {}).get('info', 'Unknown error'),
                    'raw_response': data
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'phone_number': phone_number,
                'error': f'API request failed: {str(e)}',
                'raw_response': None
            }
        except Exception as e:
            return {
                'phone_number': phone_number,
                'error': f'Unexpected error: {str(e)}',
                'raw_response': None
            }
    
    def classify_number(self, lookup_result: Dict) -> str:
        """
        Classify a number as commercial, spam, personal, or invalid based on NumVerify data.
        
        Args:
            lookup_result: Result from NumVerify API
            
        Returns:
            Classification: 'commercial', 'spam', 'personal', or 'invalid'
        """
        if 'error' in lookup_result:
            return 'invalid'
        
        if not lookup_result.get('valid', False):
            return 'invalid'
        
        line_type = lookup_result.get('line_type', '').lower()
        carrier = lookup_result.get('carrier', '').lower()
        
        # Commercial indicators
        commercial_indicators = ['landline', 'voip', 'mobile']
        spam_indicators = ['voip', 'toll_free', 'premium_rate']
        
        # Check for commercial carriers
        commercial_carriers = [
            'twilio', 'bandwidth', 'toll-free', 'voip', 'business',
            'commercial', 'marketing', 'call center'
        ]
        
        if any(indicator in carrier for indicator in commercial_carriers):
            return 'commercial'
        
        if line_type in spam_indicators:
            return 'spam'
        elif line_type in commercial_indicators:
            return 'commercial'
        else:
            return 'personal'
    
    def process_numbers(self, input_file: str, output_file: str, delay: float = 0.1):
        """
        Process all numbers from input CSV file.
        
        Args:
            input_file: Path to CSV file with phone numbers
            output_file: Path to output CSV file
            delay: Delay between API calls (seconds)
        """
        print(f"🚀 Starting NumVerify API lookup for {input_file}")
        print(f"⏱️  Delay between calls: {delay}s")
        
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
        
        # Process each number
        for i, number_info in enumerate(numbers_to_process, 1):
            phone = number_info['phone_number']
            print(f"🔍 [{i}/{len(numbers_to_process)}] Looking up: {phone}")
            
            # API lookup
            lookup_result = self.lookup_phone(phone)
            
            if lookup_result and 'error' not in lookup_result:
                self.results['successful_lookups'] += 1
                classification = self.classify_number(lookup_result)
                
                # Update counters
                if classification == 'commercial':
                    self.results['commercial_numbers'] += 1
                elif classification == 'spam':
                    self.results['spam_numbers'] += 1
                elif classification == 'personal':
                    self.results['personal_numbers'] += 1
                else:
                    self.results['invalid_numbers'] += 1
                
                # Store detailed result
                detailed_result = {
                    'phone_number': phone,
                    'classification': classification,
                    'valid': lookup_result.get('valid', False),
                    'carrier': lookup_result.get('carrier', ''),
                    'line_type': lookup_result.get('line_type', ''),
                    'country_name': lookup_result.get('country_name', ''),
                    'location': lookup_result.get('location', ''),
                    'min_date': number_info['min_date'],
                    'max_date': number_info['max_date'],
                    'date_count': number_info['date_count'],
                    'api_response': lookup_result
                }
                
            else:
                self.results['failed_lookups'] += 1
                classification = 'failed'
                
                detailed_result = {
                    'phone_number': phone,
                    'classification': classification,
                    'error': lookup_result.get('error', 'Unknown error') if lookup_result else 'No response',
                    'min_date': number_info['min_date'],
                    'max_date': number_info['max_date'],
                    'date_count': number_info['date_count'],
                    'api_response': lookup_result
                }
            
            self.results['detailed_results'].append(detailed_result)
            
            # Delay between calls to respect rate limits
            if i < len(numbers_to_process):
                time.sleep(delay)
        
        # Calculate cost
        self.results['cost_estimate'] = self.results['successful_lookups'] * 0.01
        
        # Export results
        self.export_results(output_file)
        
        # Print summary
        self.print_summary()
    
    def export_results(self, output_file: str):
        """Export results to CSV file."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'phone_number', 'classification', 'valid', 'carrier', 'line_type',
                'country_name', 'location', 'min_date', 'max_date', 'date_count',
                'error', 'notes'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.results['detailed_results']:
                writer.writerow({
                    'phone_number': result['phone_number'],
                    'classification': result['classification'],
                    'valid': result.get('valid', ''),
                    'carrier': result.get('carrier', ''),
                    'line_type': result.get('line_type', ''),
                    'country_name': result.get('country_name', ''),
                    'location': result.get('location', ''),
                    'min_date': result.get('min_date', ''),
                    'max_date': result.get('max_date', ''),
                    'date_count': result.get('date_count', ''),
                    'error': result.get('error', ''),
                    'notes': f"NumVerify lookup - {result['classification']}"
                })
        
        # Save detailed results
        json_file = output_file.replace('.csv', '_detailed.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results exported to: {output_file}")
        print(f"💾 Detailed results exported to: {json_file}")
    
    def print_summary(self):
        """Print processing summary."""
        print(f"\n🎯 NUMVERIFY API LOOKUP COMPLETE!")
        print(f"=" * 50)
        print(f"📊 Total numbers processed: {self.results['total_numbers']}")
        print(f"✅ Successful lookups: {self.results['successful_lookups']}")
        print(f"❌ Failed lookups: {self.results['failed_lookups']}")
        print(f"🏢 Commercial numbers: {self.results['commercial_numbers']}")
        print(f"🚫 Spam numbers: {self.results['spam_numbers']}")
        print(f"👤 Personal numbers: {self.results['personal_numbers']}")
        print(f"❓ Invalid numbers: {self.results['invalid_numbers']}")
        print(f"💰 Estimated cost: ${self.results['cost_estimate']:.2f}")

def main():
    """Main function for NumVerify API lookup."""
    print("🚀 NumVerify API Phone Number Lookup Tool")
    print("=" * 50)
    
    # Check if input file exists
    input_file = "properly_filtered_within_date_range.csv"
    if not Path(input_file).exists():
        print(f"❌ Input file not found: {input_file}")
        print("Please ensure the file exists before running this tool.")
        return
    
    # Get API key
    api_key = input("🔑 Enter your NumVerify API key: ").strip()
    if not api_key:
        print("❌ API key is required!")
        return
    
    # Set output file
    output_file = "numverify_lookup_results.csv"
    
    # Initialize API client
    api_client = NumVerifyAPI(api_key)
    
    # Process numbers
    try:
        api_client.process_numbers(input_file, output_file, delay=0.1)
        print(f"\n✅ Lookup complete! Check {output_file} for results.")
    except KeyboardInterrupt:
        print(f"\n⚠️ Process interrupted by user.")
        print(f"Partial results may be available in {output_file}")
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")

if __name__ == "__main__":
    main()
