#!/usr/bin/env python3
"""
CORRECTED Phone Number Analysis Tool
Fixes the phone number format matching bug discovered in sanity check.
"""

import csv
import re
import os
import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import glob

class CorrectedPhoneAnalyzer:
    def __init__(self, data_dir="../gvoice-convert"):
        self.data_dir = Path(data_dir)
        self.conversations_dir = self.data_dir / "conversations"
        self.unknown_numbers_file = self.conversations_dir / "unknown_numbers.csv"
        
        # Analysis results
        self.unknown_numbers = []
        self.frequency_map = defaultdict(int)
        self.analysis_log = []
        
    def log(self, message):
        """Log analysis steps with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.analysis_log.append(log_entry)
        print(log_entry)
        
    def normalize_phone_number(self, phone):
        """Normalize phone number to standard format for comparison"""
        # Remove all non-digits
        digits_only = re.sub(r'[^\d]', '', phone)
        
        # Handle malformed formats from CSV
        if phone.startswith('+1+'):
            # Format: +1+232132379 -> extract the digits after +1+
            digits_only = phone[3:]  # Remove '+1+'
        elif phone.startswith('+1') and len(phone) > 12:
            # Format: +10000000000 -> this is actually +1 + 0000000000
            digits_only = phone[2:]  # Remove '+1'
        elif phone.startswith('+'):
            digits_only = phone[1:]  # Remove '+'
        
        # Ensure we have clean digits
        digits_only = re.sub(r'[^\d]', '', digits_only)
        
        # Standardize to 10-digit US format if it's 11 digits starting with 1
        if len(digits_only) == 11 and digits_only.startswith('1'):
            digits_only = digits_only[1:]
        
        return digits_only
    
    def load_unknown_numbers(self):
        """Load and normalize unknown numbers from CSV file"""
        self.log("Loading and normalizing unknown numbers from CSV...")
        
        with open(self.unknown_numbers_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row['phone_number'].strip()
                if phone:
                    normalized = self.normalize_phone_number(phone)
                    self.unknown_numbers.append({
                        'original': phone,
                        'normalized': normalized,
                        'display_name': row.get('display_name', '').strip(),
                        'is_spam': row.get('is_spam', 'false').lower() == 'true',
                        'notes': row.get('notes', '').strip()
                    })
        
        self.log(f"Loaded {len(self.unknown_numbers)} unknown numbers")
        
        # Show some examples of normalization
        examples = self.unknown_numbers[:5]
        self.log("Normalization examples:")
        for ex in examples:
            self.log(f"  {ex['original']} -> {ex['normalized']}")
        
        return len(self.unknown_numbers)
    
    def analyze_frequency_corrected(self):
        """Corrected frequency analysis using proper phone number matching"""
        self.log("Running CORRECTED frequency analysis...")
        
        # Get all HTML conversation files
        html_files = list(self.conversations_dir.glob("*.html"))
        self.log(f"Found {len(html_files)} conversation files to analyze")
        
        # Create normalized phone number mapping
        normalized_to_original = {}
        for num_data in self.unknown_numbers:
            normalized_to_original[num_data['normalized']] = num_data['original']
        
        processed_files = 0
        for html_file in html_files:
            if html_file.name == 'index.html':
                continue
                
            # Extract phone number from filename
            filename = html_file.stem  # Remove .html extension
            
            # Normalize the filename phone number
            file_phone_normalized = self.normalize_phone_number(filename)
            
            # Check if this normalized number is in our unknown numbers
            if file_phone_normalized in normalized_to_original:
                original_phone = normalized_to_original[file_phone_normalized]
                self.frequency_map[original_phone] += 1
                
            processed_files += 1
            if processed_files % 100 == 0:
                self.log(f"Processed {processed_files}/{len(html_files)} files...")
        
        self.log(f"Corrected frequency analysis complete. Processed {processed_files} files.")
        
        # Generate frequency statistics
        frequencies = list(self.frequency_map.values())
        if frequencies:
            total_with_conversations = len([f for f in frequencies if f > 0])
            self.log(f"Numbers found in conversations: {total_with_conversations}/{len(self.unknown_numbers)}")
            self.log(f"Max frequency: {max(frequencies)}")
            self.log(f"Numbers with 5+ conversations: {len([f for f in frequencies if f >= 5])}")
            self.log(f"Numbers with 10+ conversations: {len([f for f in frequencies if f >= 10])}")
        else:
            self.log("No frequencies found - this indicates a matching problem")
        
        return self.frequency_map
    
    def validate_matching(self):
        """Validate that our phone number matching is working correctly"""
        self.log("Validating phone number matching...")
        
        # Get a few conversation files and check matching
        html_files = list(self.conversations_dir.glob("*.html"))[:10]
        
        for html_file in html_files:
            if html_file.name == 'index.html':
                continue
                
            filename = html_file.stem
            normalized_filename = self.normalize_phone_number(filename)
            
            # Check if any of our unknown numbers match
            matches = []
            for num_data in self.unknown_numbers:
                if num_data['normalized'] == normalized_filename:
                    matches.append(num_data['original'])
            
            if matches:
                self.log(f"File {filename} -> normalized {normalized_filename} -> matches {matches}")
            else:
                # Check if this is actually an unknown number
                found_in_unknowns = any(filename in num_data['original'] for num_data in self.unknown_numbers)
                if not found_in_unknowns:
                    self.log(f"File {filename} -> not in unknown numbers (expected)")
    
    def comprehensive_corrected_analysis(self):
        """Run comprehensive corrected analysis"""
        self.log("🔍 COMPREHENSIVE CORRECTED ANALYSIS STARTING...")
        
        # Load and normalize data
        self.load_unknown_numbers()
        
        # Validate our matching approach
        self.validate_matching()
        
        # Run corrected frequency analysis
        self.analyze_frequency_corrected()
        
        # Generate summary
        self.log("📊 CORRECTED ANALYSIS SUMMARY:")
        
        frequencies = list(self.frequency_map.values())
        total_with_conversations = len([f for f in frequencies if f > 0])
        total_zero_conversations = len(self.unknown_numbers) - total_with_conversations
        
        self.log(f"Total unknown numbers: {len(self.unknown_numbers):,}")
        self.log(f"Found in conversations: {total_with_conversations:,} ({total_with_conversations/len(self.unknown_numbers)*100:.1f}%)")
        self.log(f"Zero conversations: {total_zero_conversations:,} ({total_zero_conversations/len(self.unknown_numbers)*100:.1f}%)")
        
        if frequencies:
            high_freq = len([f for f in frequencies if f >= 10])
            med_freq = len([f for f in frequencies if f >= 5 and f < 10])
            low_freq = len([f for f in frequencies if f >= 2 and f < 5])
            single_freq = len([f for f in frequencies if f == 1])
            
            self.log(f"High frequency (10+): {high_freq:,}")
            self.log(f"Medium frequency (5-9): {med_freq:,}")
            self.log(f"Low frequency (2-4): {low_freq:,}")
            self.log(f"Single conversation: {single_freq:,}")
        
        return {
            'total_unknown': len(self.unknown_numbers),
            'found_in_conversations': total_with_conversations,
            'zero_conversations': total_zero_conversations,
            'frequency_map': dict(self.frequency_map)
        }

def main():
    """Run corrected comprehensive phone number analysis"""
    print("🔧 CORRECTED PHONE NUMBER ANALYSIS")
    print("=" * 60)
    
    analyzer = CorrectedPhoneAnalyzer()
    results = analyzer.comprehensive_corrected_analysis()
    
    # Save corrected results
    with open('corrected_phone_analysis.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'analysis_log': analyzer.analysis_log,
            'results': results
        }, f, indent=2)
    
    print(f"\n📁 Corrected results saved to: corrected_phone_analysis.json")
    return results

if __name__ == "__main__":
    results = main()
