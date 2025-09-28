#!/usr/bin/env python3
"""
Zero Conversation Investigation Tool
Samples 100 zero-conversation numbers to understand why they have no conversations.
"""

import csv
import json
import random
from pathlib import Path
from datetime import datetime
import re

class ZeroConversationInvestigator:
    def __init__(self, data_dir="../gvoice-convert"):
        self.data_dir = Path(data_dir)
        self.conversations_dir = self.data_dir / "conversations"
        self.phone_lookup_file = Path("phone_lookup.txt")
        self.results = {
            'investigation_date': datetime.now().isoformat(),
            'sample_size': 100,
            'investigation_method': 'random_sampling',
            'findings': {},
            'sample_analysis': []
        }
        
    def load_remaining_numbers(self):
        """Load remaining numbers after free filtering."""
        print("📋 Loading remaining numbers after free filtering...")
        
        remaining_file = Path("remaining_unknown_numbers.csv")
        if not remaining_file.exists():
            print("❌ Remaining numbers file not found. Run immediate_free_filtering.py first.")
            return []
        
        remaining_numbers = []
        with open(remaining_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row['phone_number'].strip()
                if phone:
                    remaining_numbers.append(phone)
        
        print(f"✅ Loaded {len(remaining_numbers)} remaining numbers")
        return remaining_numbers
    
    def load_conversation_numbers(self):
        """Load numbers that have conversations."""
        print("📋 Loading numbers with conversations...")
        
        try:
            with open("clean_phone_analysis_results.json", 'r') as f:
                clean_results = json.load(f)
            conversation_numbers = set(clean_results['frequency_analysis']['detailed_data'].keys())
        except FileNotFoundError:
            print("⚠️ Clean analysis results not found, using empty set")
            conversation_numbers = set()
        
        print(f"✅ Loaded {len(conversation_numbers)} numbers with conversations")
        return conversation_numbers
    
    def load_name_based_conversations(self):
        """Load numbers with name-based conversations."""
        print("📋 Loading name-based conversation numbers...")
        
        try:
            with open("name_based_conversation_linking_results.json", 'r') as f:
                name_results = json.load(f)
            name_based_numbers = set(name_results['conversation_mapping']['file_to_phone_mapping'].values())
        except FileNotFoundError:
            print("⚠️ Name-based linking results not found, using empty set")
            name_based_numbers = set()
        
        print(f"✅ Loaded {len(name_based_numbers)} name-based conversation numbers")
        return name_based_numbers
    
    def load_phone_lookup_data(self):
        """Load phone lookup data to check if numbers are already known."""
        print("📋 Loading phone lookup data...")
        
        phone_lookup_data = {}
        if self.phone_lookup_file.exists():
            with open(self.phone_lookup_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('|')
                        if len(parts) >= 2:
                            phone = parts[0].strip()
                            name = parts[1].strip()
                            filter_status = parts[2].strip() if len(parts) > 2 else None
                            phone_lookup_data[phone] = {
                                'name': name,
                                'filter_status': filter_status
                            }
        
        print(f"✅ Loaded {len(phone_lookup_data)} phone lookup entries")
        return phone_lookup_data
    
    def investigate_sample_number(self, phone, conversation_numbers, name_based_numbers, phone_lookup_data):
        """Investigate a single number to understand why it has no conversations."""
        investigation = {
            'phone': phone,
            'has_phone_conversation': phone in conversation_numbers,
            'has_name_conversation': phone in name_based_numbers,
            'in_phone_lookup': phone in phone_lookup_data,
            'phone_lookup_info': phone_lookup_data.get(phone, None),
            'potential_reasons': [],
            'conversation_files_found': [],
            'investigation_notes': ''
        }
        
        # Check for direct conversation file
        direct_file = self.conversations_dir / f"{phone}.html"
        if direct_file.exists():
            investigation['conversation_files_found'].append(direct_file.name)
            investigation['has_phone_conversation'] = True
        
        # Check if number is in phone_lookup.txt (already known/filtered)
        if phone in phone_lookup_data:
            investigation['potential_reasons'].append('Already in phone_lookup.txt')
            lookup_info = phone_lookup_data[phone]
            if lookup_info['filter_status'] == 'filter':
                investigation['potential_reasons'].append('Marked as filtered in phone_lookup')
        
        # Check for date range issues
        # Note: We can't easily check dates without parsing HTML content
        investigation['potential_reasons'].append('Date range filtering (2022-08-01 to 2025-06-01)')
        
        # Check for area code patterns
        if phone.startswith('+1') and len(phone) == 12:
            area_code = phone[2:5]
            investigation['area_code'] = area_code
            
            # Check if it's a known problematic area code
            if area_code in ['000', '111', '222']:
                investigation['potential_reasons'].append('Suspicious area code')
        
        # Check for international numbers
        if not phone.startswith('+1'):
            investigation['potential_reasons'].append('International number (may not be in SMS dataset)')
        
        # Check for business patterns
        if self._is_business_pattern(phone):
            investigation['potential_reasons'].append('Business pattern number')
        
        # Check for toll-free (should have been filtered already)
        if any(phone.startswith(pattern) for pattern in ['+1800', '+1833', '+1844', '+1855', '+1866', '+1877', '+1888']):
            investigation['potential_reasons'].append('Toll-free number (should have been filtered)')
        
        return investigation
    
    def _is_business_pattern(self, phone):
        """Check if phone number has business-like patterns."""
        if not phone.startswith('+1') or len(phone) != 12:
            return False
        
        digits = phone[2:]  # Remove +1
        
        # Repeating digits
        if len(set(digits)) <= 2:
            return True
        
        # Sequential patterns
        if digits in ['1234567890', '0987654321']:
            return True
        
        return False
    
    def run_investigation(self):
        """Run the zero conversation investigation."""
        print("🔍 STARTING ZERO CONVERSATION INVESTIGATION")
        print("=" * 60)
        
        # Load data
        remaining_numbers = self.load_remaining_numbers()
        conversation_numbers = self.load_conversation_numbers()
        name_based_numbers = self.load_name_based_conversations()
        phone_lookup_data = self.load_phone_lookup_data()
        
        # Find zero-conversation numbers
        all_conversation_numbers = conversation_numbers.union(name_based_numbers)
        zero_conversation_numbers = [phone for phone in remaining_numbers if phone not in all_conversation_numbers]
        
        print(f"📊 Found {len(zero_conversation_numbers)} zero-conversation numbers")
        
        # Sample 100 numbers for investigation
        sample_size = min(100, len(zero_conversation_numbers))
        sample_numbers = random.sample(zero_conversation_numbers, sample_size)
        
        print(f"🎯 Investigating random sample of {sample_size} numbers...")
        
        # Investigate each sample number
        sample_analysis = []
        for i, phone in enumerate(sample_numbers, 1):
            if i % 10 == 0:
                print(f"  📞 Investigated {i}/{sample_size} numbers...")
            
            investigation = self.investigate_sample_number(
                phone, conversation_numbers, name_based_numbers, phone_lookup_data
            )
            sample_analysis.append(investigation)
        
        # Analyze findings
        findings = self._analyze_findings(sample_analysis)
        
        # Store results
        self.results['sample_analysis'] = sample_analysis
        self.results['findings'] = findings
        
        # Save results
        output_file = Path("zero_conversation_investigation_results.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Investigation complete!")
        print(f"📊 Results saved to: {output_file}")
        
        # Print summary
        self._print_summary(findings)
        
        return self.results
    
    def _analyze_findings(self, sample_analysis):
        """Analyze the investigation findings."""
        findings = {
            'total_sample_size': len(sample_analysis),
            'reason_counts': {},
            'area_code_distribution': {},
            'phone_lookup_coverage': 0,
            'international_numbers': 0,
            'business_patterns': 0,
            'suspicious_area_codes': 0,
            'most_common_reasons': []
        }
        
        for analysis in sample_analysis:
            # Count reasons
            for reason in analysis['potential_reasons']:
                findings['reason_counts'][reason] = findings['reason_counts'].get(reason, 0) + 1
            
            # Count area codes
            if 'area_code' in analysis:
                area_code = analysis['area_code']
                findings['area_code_distribution'][area_code] = findings['area_code_distribution'].get(area_code, 0) + 1
                
                if area_code in ['000', '111', '222']:
                    findings['suspicious_area_codes'] += 1
            
            # Count other patterns
            if analysis['in_phone_lookup']:
                findings['phone_lookup_coverage'] += 1
            
            if 'International number' in analysis['potential_reasons']:
                findings['international_numbers'] += 1
            
            if 'Business pattern number' in analysis['potential_reasons']:
                findings['business_patterns'] += 1
        
        # Find most common reasons
        sorted_reasons = sorted(findings['reason_counts'].items(), key=lambda x: x[1], reverse=True)
        findings['most_common_reasons'] = sorted_reasons[:5]
        
        return findings
    
    def _print_summary(self, findings):
        """Print investigation summary."""
        print(f"\n📋 INVESTIGATION SUMMARY:")
        print(f"  📊 Sample size: {findings['total_sample_size']}")
        print(f"  📞 In phone_lookup.txt: {findings['phone_lookup_coverage']}")
        print(f"  🌍 International numbers: {findings['international_numbers']}")
        print(f"  🏢 Business patterns: {findings['business_patterns']}")
        print(f"  ⚠️ Suspicious area codes: {findings['suspicious_area_codes']}")
        
        print(f"\n🎯 TOP REASONS FOR ZERO CONVERSATIONS:")
        for reason, count in findings['most_common_reasons']:
            percentage = (count / findings['total_sample_size']) * 100
            print(f"  {reason}: {count} ({percentage:.1f}%)")
        
        print(f"\n📊 TOP AREA CODES:")
        sorted_area_codes = sorted(findings['area_code_distribution'].items(), key=lambda x: x[1], reverse=True)
        for area_code, count in sorted_area_codes[:10]:
            percentage = (count / findings['total_sample_size']) * 100
            print(f"  {area_code}: {count} ({percentage:.1f}%)")

def main():
    """Run zero conversation investigation."""
    investigator = ZeroConversationInvestigator()
    results = investigator.run_investigation()
    return results

if __name__ == "__main__":
    results = main()
