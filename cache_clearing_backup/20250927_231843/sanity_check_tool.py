#!/usr/bin/env python3
"""
Sanity Check Tool - Validate Free Analysis Results
Investigate why 83.8% of numbers have zero conversations and verify filtering accuracy.
"""

import csv
import re
import json
from pathlib import Path
from collections import defaultdict
import random

class SanityChecker:
    def __init__(self, data_dir="../gvoice-convert"):
        self.data_dir = Path(data_dir)
        self.conversations_dir = self.data_dir / "conversations"
        self.unknown_numbers_file = self.conversations_dir / "unknown_numbers.csv"
        
        # Load previous analysis results
        with open('phone_analysis_results.json', 'r') as f:
            self.analysis_results = json.load(f)
        
        self.log_entries = []
        
    def log(self, message):
        """Log sanity check steps"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_entries.append(log_entry)
        print(log_entry)
    
    def validate_pattern_filtering(self):
        """Validate that pattern filtering didn't catch valid personal numbers"""
        self.log("🔍 VALIDATING PATTERN FILTERING...")
        
        # Load pattern filtered numbers
        pattern_results = self.analysis_results['raw_data']['pattern_results']
        
        # Check toll-free numbers (should be 99% accurate)
        self.log(f"Checking {len(pattern_results['toll_free'])} toll-free numbers...")
        toll_free_sample = random.sample(pattern_results['toll_free'], min(20, len(pattern_results['toll_free'])))
        
        false_positives = []
        for phone in toll_free_sample:
            clean_phone = re.sub(r'[^\d]', '', phone)
            if len(clean_phone) >= 10:
                area_code = clean_phone[-10:-7]
                if area_code not in ['800', '888', '877', '866', '855', '844', '833', '822']:
                    false_positives.append(phone)
        
        self.log(f"Toll-free false positives: {len(false_positives)}/20 sampled")
        if false_positives:
            self.log(f"  Examples: {false_positives[:5]}")
        
        # Check business patterns (should be 85% accurate)
        self.log(f"Checking {len(pattern_results['business_patterns'])} business patterns...")
        business_sample = random.sample(pattern_results['business_patterns'], 
                                       min(10, len(pattern_results['business_patterns'])))
        
        questionable_business = []
        for phone in business_sample:
            clean_phone = re.sub(r'[^\d]', '', phone)
            if len(clean_phone) >= 10:
                last_four = clean_phone[-4:]
                # Check if this might be a valid personal number
                if not (len(set(last_four)) == 1 or last_four.endswith('000')):
                    questionable_business.append(phone)
        
        self.log(f"Questionable business patterns: {len(questionable_business)}/10 sampled")
        if questionable_business:
            self.log(f"  Examples: {questionable_business}")
        
        return {
            'toll_free_false_positives': false_positives,
            'questionable_business': questionable_business
        }
    
    def investigate_zero_conversations(self):
        """Investigate why 83.8% of numbers have zero conversations"""
        self.log("🔍 INVESTIGATING ZERO CONVERSATION NUMBERS...")
        
        # Get numbers with zero conversations
        frequency_map = self.analysis_results['raw_data']['frequency_map']
        
        # Load all unknown numbers
        unknown_numbers = []
        with open(self.unknown_numbers_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row['phone_number'].strip()
                if phone:
                    unknown_numbers.append(phone)
        
        zero_conv_numbers = [phone for phone in unknown_numbers if phone not in frequency_map]
        self.log(f"Numbers with zero conversations: {len(zero_conv_numbers)}")
        
        # Sample and analyze zero conversation numbers
        sample_size = min(50, len(zero_conv_numbers))
        zero_sample = random.sample(zero_conv_numbers, sample_size)
        
        self.log(f"Analyzing sample of {sample_size} zero-conversation numbers...")
        
        # Categorize the sample
        international_numbers = []
        malformed_numbers = []
        short_numbers = []
        us_looking_numbers = []
        
        for phone in zero_sample:
            clean_phone = re.sub(r'[^\d]', '', phone)
            
            if len(clean_phone) < 10:
                short_numbers.append(phone)
            elif not phone.startswith('+1') and not phone.startswith('1'):
                international_numbers.append(phone)
            elif len(clean_phone) > 11 or (len(clean_phone) == 11 and not clean_phone.startswith('1')):
                malformed_numbers.append(phone)
            else:
                us_looking_numbers.append(phone)
        
        self.log(f"Zero conversation sample breakdown:")
        self.log(f"  International numbers: {len(international_numbers)} ({len(international_numbers)/sample_size*100:.1f}%)")
        self.log(f"  Short numbers: {len(short_numbers)} ({len(short_numbers)/sample_size*100:.1f}%)")
        self.log(f"  Malformed numbers: {len(malformed_numbers)} ({len(malformed_numbers)/sample_size*100:.1f}%)")
        self.log(f"  US-looking numbers: {len(us_looking_numbers)} ({len(us_looking_numbers)/sample_size*100:.1f}%)")
        
        # Show examples
        if international_numbers:
            self.log(f"  International examples: {international_numbers[:5]}")
        if malformed_numbers:
            self.log(f"  Malformed examples: {malformed_numbers[:5]}")
        if us_looking_numbers:
            self.log(f"  US-looking examples: {us_looking_numbers[:5]}")
        
        return {
            'total_zero_conversations': len(zero_conv_numbers),
            'sample_breakdown': {
                'international': len(international_numbers),
                'short': len(short_numbers),
                'malformed': len(malformed_numbers),
                'us_looking': len(us_looking_numbers)
            },
            'examples': {
                'international': international_numbers[:5],
                'malformed': malformed_numbers[:5],
                'us_looking': us_looking_numbers[:5]
            }
        }
    
    def test_conversation_search_accuracy(self):
        """Test if our conversation search method is working correctly"""
        self.log("🔍 TESTING CONVERSATION SEARCH ACCURACY...")
        
        # Get numbers that DO have conversations
        frequency_map = self.analysis_results['raw_data']['frequency_map']
        numbers_with_convs = [(phone, freq) for phone, freq in frequency_map.items() if freq > 0]
        
        # Test a sample to verify they actually appear in conversations
        test_sample = random.sample(numbers_with_convs, min(10, len(numbers_with_convs)))
        
        verified_count = 0
        for phone, reported_freq in test_sample:
            # Manually search for this number in conversation files
            actual_freq = self._manual_search_phone(phone)
            
            if actual_freq > 0:
                verified_count += 1
                self.log(f"✅ {phone}: reported {reported_freq}, found {actual_freq}")
            else:
                self.log(f"❌ {phone}: reported {reported_freq}, found {actual_freq}")
        
        accuracy = verified_count / len(test_sample) * 100
        self.log(f"Conversation search accuracy: {accuracy:.1f}% ({verified_count}/{len(test_sample)})")
        
        return accuracy
    
    def _manual_search_phone(self, phone):
        """Manually search for a phone number in conversation files"""
        # Clean phone number for searching
        clean_phone = re.sub(r'^\+1\+?', '', phone)
        search_patterns = [phone, clean_phone]
        
        # Add formatted versions if it's a 10-digit number
        if clean_phone.isdigit() and len(clean_phone) == 10:
            search_patterns.extend([
                f"({clean_phone[:3]}) {clean_phone[3:6]}-{clean_phone[6:]}",
                f"{clean_phone[:3]}-{clean_phone[3:6]}-{clean_phone[6:]}",
            ])
        
        found_count = 0
        html_files = list(self.conversations_dir.glob("*.html"))
        
        for html_file in html_files[:50]:  # Limit search for speed
            if html_file.name == 'index.html':
                continue
                
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in search_patterns:
                    if pattern in content:
                        found_count += 1
                        break
                        
            except Exception:
                continue
        
        return found_count
    
    def check_existing_filtering(self):
        """Check if existing filtering might explain zero conversations"""
        self.log("🔍 CHECKING EXISTING FILTERING EFFECTS...")
        
        # Check if there are any filtering settings that might affect results
        # Look for phone_lookup.txt entries
        phone_lookup_file = Path("phone_lookup.txt")
        
        if phone_lookup_file.exists():
            with open(phone_lookup_file, 'r') as f:
                lookup_content = f.read()
                lookup_lines = len(lookup_content.strip().split('\n'))
                self.log(f"Found phone_lookup.txt with {lookup_lines} entries")
                
                # Check if any of our zero-conversation numbers are in lookup
                frequency_map = self.analysis_results['raw_data']['frequency_map']
                zero_conv_numbers = []
                
                # Load unknown numbers
                with open(self.unknown_numbers_file, 'r') as uf:
                    reader = csv.DictReader(uf)
                    for row in reader:
                        phone = row['phone_number'].strip()
                        if phone and phone not in frequency_map:
                            zero_conv_numbers.append(phone)
                
                # Sample and check if they're in phone lookup
                sample = random.sample(zero_conv_numbers, min(20, len(zero_conv_numbers)))
                in_lookup = 0
                
                for phone in sample:
                    if phone in lookup_content:
                        in_lookup += 1
                
                self.log(f"Zero-conversation numbers in phone_lookup.txt: {in_lookup}/20 sampled")
        
        return True
    
    def comprehensive_sanity_check(self):
        """Run comprehensive sanity check"""
        self.log("🔍 COMPREHENSIVE SANITY CHECK STARTING...")
        
        results = {
            'pattern_validation': self.validate_pattern_filtering(),
            'zero_conversation_analysis': self.investigate_zero_conversations(),
            'search_accuracy': self.test_conversation_search_accuracy(),
            'existing_filtering_check': self.check_existing_filtering()
        }
        
        # Generate summary
        self.log("📊 SANITY CHECK SUMMARY:")
        
        # Pattern filtering validation
        pattern_val = results['pattern_validation']
        self.log(f"✅ Pattern filtering validation:")
        self.log(f"   Toll-free false positives: {len(pattern_val['toll_free_false_positives'])}/20")
        self.log(f"   Questionable business patterns: {len(pattern_val['questionable_business'])}/10")
        
        # Zero conversation analysis
        zero_analysis = results['zero_conversation_analysis']
        self.log(f"✅ Zero conversation analysis:")
        self.log(f"   Total with zero conversations: {zero_analysis['total_zero_conversations']:,}")
        
        breakdown = zero_analysis['sample_breakdown']
        total_sample = sum(breakdown.values())
        if total_sample > 0:
            self.log(f"   International: {breakdown['international']}/{total_sample} ({breakdown['international']/total_sample*100:.1f}%)")
            self.log(f"   US-looking: {breakdown['us_looking']}/{total_sample} ({breakdown['us_looking']/total_sample*100:.1f}%)")
        
        # Search accuracy
        self.log(f"✅ Search method accuracy: {results['search_accuracy']:.1f}%")
        
        return results

def main():
    """Run comprehensive sanity check"""
    print("🔍 SANITY CHECK - VALIDATING FREE ANALYSIS RESULTS")
    print("=" * 60)
    
    checker = SanityChecker()
    results = checker.comprehensive_sanity_check()
    
    # Save results
    with open('sanity_check_results.json', 'w') as f:
        json.dump({
            'timestamp': '2025-09-27T23:30:00',
            'log_entries': checker.log_entries,
            'results': results
        }, f, indent=2)
    
    print(f"\n📁 Sanity check results saved to: sanity_check_results.json")
    return results

if __name__ == "__main__":
    results = main()
