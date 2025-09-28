#!/usr/bin/env python3
"""
Phone Number Analysis Tool - FREE ANALYSIS FIRST
Comprehensive analysis of unknown phone numbers using pattern recognition and frequency analysis.
"""

import csv
import re
import os
import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import glob

class PhoneAnalyzer:
    def __init__(self, data_dir="../gvoice-convert"):
        self.data_dir = Path(data_dir)
        self.conversations_dir = self.data_dir / "conversations"
        self.unknown_numbers_file = self.conversations_dir / "unknown_numbers.csv"
        
        # Analysis results
        self.unknown_numbers = []
        self.frequency_map = defaultdict(int)
        self.pattern_results = {
            'toll_free': [],
            'short_codes': [],
            'business_patterns': [],
            'geographic_clusters': defaultdict(list),
            'sequential_patterns': []
        }
        self.analysis_log = []
        
    def log(self, message):
        """Log analysis steps with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.analysis_log.append(log_entry)
        print(log_entry)
        
    def load_unknown_numbers(self):
        """Load unknown numbers from CSV file"""
        self.log("Loading unknown numbers from CSV...")
        
        with open(self.unknown_numbers_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row['phone_number'].strip()
                if phone:
                    self.unknown_numbers.append({
                        'phone': phone,
                        'display_name': row.get('display_name', '').strip(),
                        'is_spam': row.get('is_spam', 'false').lower() == 'true',
                        'notes': row.get('notes', '').strip()
                    })
        
        self.log(f"Loaded {len(self.unknown_numbers)} unknown numbers")
        return len(self.unknown_numbers)
    
    def analyze_frequency(self):
        """Analyze frequency of unknown numbers in conversation files"""
        self.log("Analyzing frequency in conversation files...")
        
        # Get all HTML conversation files
        html_files = list(self.conversations_dir.glob("*.html"))
        self.log(f"Found {len(html_files)} conversation files to analyze")
        
        # Create phone number set for faster lookup
        unknown_phones = {num['phone'] for num in self.unknown_numbers}
        
        processed_files = 0
        for html_file in html_files:
            if html_file.name == 'index.html':
                continue
                
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for phone numbers in the content
                for phone in unknown_phones:
                    # Clean phone number for searching (remove +1 prefix variations)
                    clean_phone = re.sub(r'^\+1\+?', '', phone)
                    search_patterns = [phone, clean_phone]
                    
                    # Add variations
                    if clean_phone.isdigit() and len(clean_phone) == 10:
                        # Add formatted versions
                        search_patterns.extend([
                            f"({clean_phone[:3]}) {clean_phone[3:6]}-{clean_phone[6:]}",
                            f"{clean_phone[:3]}-{clean_phone[3:6]}-{clean_phone[6:]}",
                            f"{clean_phone[:3]}.{clean_phone[3:6]}.{clean_phone[6:]}"
                        ])
                    
                    # Check if any pattern appears in content
                    for pattern in search_patterns:
                        if pattern in content:
                            self.frequency_map[phone] += 1
                            break
                            
                processed_files += 1
                if processed_files % 100 == 0:
                    self.log(f"Processed {processed_files}/{len(html_files)} files...")
                    
            except Exception as e:
                self.log(f"Error processing {html_file}: {e}")
        
        self.log(f"Frequency analysis complete. Processed {processed_files} files.")
        
        # Generate frequency statistics
        frequencies = list(self.frequency_map.values())
        if frequencies:
            total_with_conversations = len([f for f in frequencies if f > 0])
            self.log(f"Numbers found in conversations: {total_with_conversations}/{len(self.unknown_numbers)}")
            self.log(f"Max frequency: {max(frequencies)}")
            self.log(f"Numbers with 5+ conversations: {len([f for f in frequencies if f >= 5])}")
            self.log(f"Numbers with 10+ conversations: {len([f for f in frequencies if f >= 10])}")
        
        return self.frequency_map
    
    def analyze_patterns(self):
        """Analyze phone number patterns for business identification"""
        self.log("Analyzing phone number patterns...")
        
        for num_data in self.unknown_numbers:
            phone = num_data['phone']
            
            # Clean phone number
            clean_phone = re.sub(r'[^\d]', '', phone)
            
            # Toll-free analysis
            if self._is_toll_free(clean_phone):
                self.pattern_results['toll_free'].append(phone)
            
            # Short code analysis
            elif self._is_short_code(clean_phone):
                self.pattern_results['short_codes'].append(phone)
            
            # Business pattern analysis
            elif self._has_business_pattern(clean_phone):
                self.pattern_results['business_patterns'].append(phone)
            
            # Geographic clustering
            if len(clean_phone) >= 10:
                area_code = clean_phone[-10:-7]  # Get area code from 10-digit number
                self.pattern_results['geographic_clusters'][area_code].append(phone)
            
            # Sequential pattern analysis
            if self._is_sequential_pattern(clean_phone):
                self.pattern_results['sequential_patterns'].append(phone)
        
        # Log pattern results
        self.log(f"Toll-free numbers: {len(self.pattern_results['toll_free'])}")
        self.log(f"Short codes: {len(self.pattern_results['short_codes'])}")
        self.log(f"Business patterns: {len(self.pattern_results['business_patterns'])}")
        self.log(f"Sequential patterns: {len(self.pattern_results['sequential_patterns'])}")
        self.log(f"Area codes found: {len(self.pattern_results['geographic_clusters'])}")
        
        return self.pattern_results
    
    def _is_toll_free(self, phone):
        """Check if number is toll-free"""
        if len(phone) < 10:
            return False
        # Check for toll-free prefixes
        toll_free_codes = ['800', '888', '877', '866', '855', '844', '833', '822']
        area_code = phone[-10:-7]
        return area_code in toll_free_codes
    
    def _is_short_code(self, phone):
        """Check if number is a short code"""
        return 3 <= len(phone) <= 6
    
    def _has_business_pattern(self, phone):
        """Check for business-like patterns"""
        if len(phone) < 10:
            return False
            
        # Check for patterns like ending in 0000, 1111, etc.
        last_four = phone[-4:]
        if len(set(last_four)) == 1:  # All same digit
            return True
        
        # Check for sequential patterns in last 4 digits
        if last_four in ['0123', '1234', '2345', '3456', '4567', '5678', '6789']:
            return True
        
        # Check for common business endings
        business_endings = ['0000', '1000', '2000', '3000', '4000', '5000', '6000', '7000', '8000', '9000']
        if last_four in business_endings:
            return True
            
        return False
    
    def _is_sequential_pattern(self, phone):
        """Check for sequential number patterns"""
        if len(phone) < 10:
            return False
            
        # Check if digits are in sequence
        digits = [int(d) for d in phone[-10:]]
        
        # Check for ascending sequence
        ascending = all(digits[i] <= digits[i+1] for i in range(len(digits)-1))
        # Check for descending sequence  
        descending = all(digits[i] >= digits[i+1] for i in range(len(digits)-1))
        
        return ascending or descending
    
    def generate_frequency_report(self):
        """Generate detailed frequency analysis report"""
        self.log("Generating frequency analysis report...")
        
        # Sort by frequency
        sorted_by_freq = sorted(self.frequency_map.items(), key=lambda x: x[1], reverse=True)
        
        # Categorize by frequency
        high_freq = [(phone, freq) for phone, freq in sorted_by_freq if freq >= 10]
        med_freq = [(phone, freq) for phone, freq in sorted_by_freq if 5 <= freq < 10]
        low_freq = [(phone, freq) for phone, freq in sorted_by_freq if 2 <= freq < 5]
        single_freq = [(phone, freq) for phone, freq in sorted_by_freq if freq == 1]
        no_conversations = [(phone, 0) for phone in [n['phone'] for n in self.unknown_numbers] 
                           if phone not in self.frequency_map]
        
        report = {
            'summary': {
                'total_unknown': len(self.unknown_numbers),
                'found_in_conversations': len([f for f in self.frequency_map.values() if f > 0]),
                'high_frequency_10plus': len(high_freq),
                'medium_frequency_5to9': len(med_freq),
                'low_frequency_2to4': len(low_freq),
                'single_conversation': len(single_freq),
                'no_conversations_found': len(no_conversations)
            },
            'high_frequency': high_freq[:20],  # Top 20
            'medium_frequency': med_freq[:10],  # Top 10
            'categories': {
                'high_priority_for_api': len(high_freq) + len(med_freq),
                'medium_priority_for_api': len(low_freq),
                'low_priority_for_api': len(single_freq),
                'skip_api': len(no_conversations)
            }
        }
        
        return report
    
    def generate_pattern_report(self):
        """Generate detailed pattern analysis report"""
        self.log("Generating pattern analysis report...")
        
        # Calculate total filtered by patterns
        total_pattern_filtered = (
            len(self.pattern_results['toll_free']) +
            len(self.pattern_results['short_codes']) +
            len(self.pattern_results['business_patterns']) +
            len(self.pattern_results['sequential_patterns'])
        )
        
        # Analyze geographic clustering
        large_clusters = {area: phones for area, phones in self.pattern_results['geographic_clusters'].items() 
                         if len(phones) >= 5}
        
        report = {
            'summary': {
                'total_pattern_filtered': total_pattern_filtered,
                'percentage_filtered': round(total_pattern_filtered / len(self.unknown_numbers) * 100, 2),
                'toll_free_count': len(self.pattern_results['toll_free']),
                'short_code_count': len(self.pattern_results['short_codes']),
                'business_pattern_count': len(self.pattern_results['business_patterns']),
                'sequential_pattern_count': len(self.pattern_results['sequential_patterns']),
                'large_geographic_clusters': len(large_clusters)
            },
            'details': {
                'toll_free_sample': self.pattern_results['toll_free'][:10],
                'short_codes_sample': self.pattern_results['short_codes'][:10],
                'business_patterns_sample': self.pattern_results['business_patterns'][:10],
                'large_clusters': {area: len(phones) for area, phones in large_clusters.items()}
            }
        }
        
        return report
    
    def save_results(self, filename="phone_analysis_results.json"):
        """Save analysis results to JSON file"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'analysis_log': self.analysis_log,
            'frequency_analysis': self.generate_frequency_report(),
            'pattern_analysis': self.generate_pattern_report(),
            'raw_data': {
                'frequency_map': dict(self.frequency_map),
                'pattern_results': {
                    'toll_free': self.pattern_results['toll_free'],
                    'short_codes': self.pattern_results['short_codes'],
                    'business_patterns': self.pattern_results['business_patterns'],
                    'sequential_patterns': self.pattern_results['sequential_patterns'],
                    'geographic_clusters': dict(self.pattern_results['geographic_clusters'])
                }
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.log(f"Results saved to {filename}")
        return filename

def main():
    """Run comprehensive phone number analysis"""
    print("🔍 PHONE NUMBER ANALYSIS - FREE METHODS FIRST")
    print("=" * 60)
    
    analyzer = PhoneAnalyzer()
    
    # Load data
    analyzer.load_unknown_numbers()
    
    # Run analyses
    analyzer.analyze_frequency()
    analyzer.analyze_patterns()
    
    # Generate reports
    freq_report = analyzer.generate_frequency_report()
    pattern_report = analyzer.generate_pattern_report()
    
    # Save results
    results_file = analyzer.save_results()
    
    # Print summary
    print("\n📊 ANALYSIS SUMMARY")
    print("=" * 40)
    print(f"Total unknown numbers: {freq_report['summary']['total_unknown']:,}")
    print(f"Found in conversations: {freq_report['summary']['found_in_conversations']:,}")
    print(f"High frequency (10+): {freq_report['summary']['high_frequency_10plus']:,}")
    print(f"Medium frequency (5-9): {freq_report['summary']['medium_frequency_5to9']:,}")
    print(f"Pattern filtered: {pattern_report['summary']['total_pattern_filtered']:,} ({pattern_report['summary']['percentage_filtered']}%)")
    print(f"Results saved to: {results_file}")
    
    return analyzer

if __name__ == "__main__":
    analyzer = main()
