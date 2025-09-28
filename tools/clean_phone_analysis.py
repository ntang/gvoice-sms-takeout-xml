#!/usr/bin/env python3
"""
Clean Phone Number Analysis Tool
Performs comprehensive analysis on the corrected unknown_numbers.csv dataset.
"""

import csv
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import time

class CleanPhoneAnalyzer:
    def __init__(self, data_dir="../gvoice-convert"):
        self.data_dir = Path(data_dir)
        self.conversations_dir = self.data_dir / "conversations"
        self.unknown_csv = self.conversations_dir / "unknown_numbers.csv"
        self.results = {
            'analysis_date': datetime.now().isoformat(),
            'dataset_info': {},
            'frequency_analysis': {},
            'pattern_analysis': {},
            'summary': {}
        }
        
    def load_unknown_numbers(self):
        """Load unknown numbers from the clean CSV."""
        print("📋 Loading unknown numbers from clean CSV...")
        
        if not self.unknown_csv.exists():
            raise FileNotFoundError(f"Unknown numbers CSV not found: {self.unknown_csv}")
        
        unknown_numbers = []
        with open(self.unknown_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row['phone_number'].strip()
                if phone:
                    unknown_numbers.append(phone)
        
        print(f"✅ Loaded {len(unknown_numbers)} unknown numbers")
        self.results['dataset_info'] = {
            'total_unknown_numbers': len(unknown_numbers),
            'csv_file': str(self.unknown_csv),
            'data_quality': 'clean (post-bug-fix)'
        }
        
        return unknown_numbers
    
    def find_conversation_files(self):
        """Find all conversation HTML files."""
        print("🔍 Scanning for conversation files...")
        
        conversation_files = []
        for html_file in self.conversations_dir.glob("*.html"):
            # Skip non-conversation files
            if html_file.name in ['index.html', 'search.html']:
                continue
            conversation_files.append(html_file)
        
        print(f"✅ Found {len(conversation_files)} conversation files")
        return conversation_files
    
    def analyze_conversation_frequency(self, unknown_numbers, conversation_files):
        """Analyze how frequently each unknown number appears in conversations."""
        print("📊 Analyzing conversation frequency for unknown numbers...")
        
        # Create a set for fast lookup
        unknown_set = set(unknown_numbers)
        
        # Track frequency and file counts
        frequency_data = defaultdict(lambda: {'conversation_count': 0, 'files': []})
        
        # Process each conversation file
        total_files = len(conversation_files)
        processed = 0
        
        for html_file in conversation_files:
            processed += 1
            if processed % 1000 == 0:
                print(f"  📄 Processed {processed}/{total_files} files...")
            
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract phone numbers from filename (format: +1234567890.html)
                filename_stem = html_file.stem
                if filename_stem in unknown_set:
                    frequency_data[filename_stem]['conversation_count'] += 1
                    frequency_data[filename_stem]['files'].append(html_file.name)
                
                # Also search within file content for additional references
                for phone in unknown_set:
                    if phone in content:
                        if phone not in frequency_data:
                            frequency_data[phone]['conversation_count'] = 0
                            frequency_data[phone]['files'] = []
                        if html_file.name not in frequency_data[phone]['files']:
                            frequency_data[phone]['conversation_count'] += 1
                            frequency_data[phone]['files'].append(html_file.name)
                            
            except Exception as e:
                print(f"  ⚠️ Error processing {html_file}: {e}")
                continue
        
        # Convert to regular dict and calculate statistics
        frequency_stats = {
            'numbers_with_conversations': 0,
            'numbers_without_conversations': 0,
            'total_conversation_count': 0,
            'frequency_distribution': Counter(),
            'detailed_data': {}
        }
        
        for phone, data in frequency_data.items():
            conv_count = data['conversation_count']
            frequency_stats['detailed_data'][phone] = {
                'conversation_count': conv_count,
                'file_count': len(data['files']),
                'sample_files': data['files'][:5]  # First 5 files as examples
            }
            
            if conv_count > 0:
                frequency_stats['numbers_with_conversations'] += 1
                frequency_stats['frequency_distribution'][conv_count] += 1
            else:
                frequency_stats['numbers_without_conversations'] += 1
            
            frequency_stats['total_conversation_count'] += conv_count
        
        print(f"✅ Frequency analysis complete:")
        print(f"  📞 Numbers with conversations: {frequency_stats['numbers_with_conversations']}")
        print(f"  📞 Numbers without conversations: {frequency_stats['numbers_without_conversations']}")
        print(f"  📊 Total conversation instances: {frequency_stats['total_conversation_count']}")
        
        self.results['frequency_analysis'] = frequency_stats
        return frequency_stats
    
    def analyze_patterns(self, unknown_numbers):
        """Analyze patterns in unknown phone numbers."""
        print("🔍 Analyzing phone number patterns...")
        
        pattern_stats = {
            'toll_free': [],
            'short_codes': [],
            'business_patterns': [],
            'area_code_analysis': Counter(),
            'format_analysis': Counter(),
            'suspicious_patterns': []
        }
        
        for phone in unknown_numbers:
            # Toll-free numbers (800, 833, 844, 855, 866, 877, 888)
            if phone.startswith('+1800') or phone.startswith('+1833') or \
               phone.startswith('+1844') or phone.startswith('+1855') or \
               phone.startswith('+1866') or phone.startswith('+1877') or \
               phone.startswith('+1888'):
                pattern_stats['toll_free'].append(phone)
            
            # Short codes (5-6 digits)
            elif re.match(r'^\+\d{1,2}\d{5,6}$', phone):
                pattern_stats['short_codes'].append(phone)
            
            # Business patterns (repeating digits, sequential, etc.)
            elif self._is_business_pattern(phone):
                pattern_stats['business_patterns'].append(phone)
            
            # Area code analysis
            if phone.startswith('+1') and len(phone) == 12:
                area_code = phone[2:5]
                pattern_stats['area_code_analysis'][area_code] += 1
            
            # Format analysis
            pattern_stats['format_analysis'][phone[:3]] += 1
            
            # Suspicious patterns
            if self._is_suspicious_pattern(phone):
                pattern_stats['suspicious_patterns'].append(phone)
        
        # Calculate summary statistics
        pattern_summary = {
            'toll_free_count': len(pattern_stats['toll_free']),
            'short_codes_count': len(pattern_stats['short_codes']),
            'business_patterns_count': len(pattern_stats['business_patterns']),
            'suspicious_patterns_count': len(pattern_stats['suspicious_patterns']),
            'top_area_codes': dict(pattern_stats['area_code_analysis'].most_common(10)),
            'format_breakdown': dict(pattern_stats['format_analysis'])
        }
        
        print(f"✅ Pattern analysis complete:")
        print(f"  🆓 Toll-free numbers: {pattern_summary['toll_free_count']}")
        print(f"  📱 Short codes: {pattern_summary['short_codes_count']}")
        print(f"  🏢 Business patterns: {pattern_summary['business_patterns_count']}")
        print(f"  ⚠️ Suspicious patterns: {pattern_summary['suspicious_patterns_count']}")
        
        self.results['pattern_analysis'] = {
            'detailed_patterns': pattern_stats,
            'summary': pattern_summary
        }
        
        return pattern_stats, pattern_summary
    
    def _is_business_pattern(self, phone):
        """Check if phone number has business-like patterns."""
        if not phone.startswith('+1') or len(phone) != 12:
            return False
        
        digits = phone[2:]  # Remove +1
        
        # Repeating digits (e.g., 1111111111, 2222222222)
        if len(set(digits)) <= 2:
            return True
        
        # Sequential patterns (e.g., 1234567890)
        if digits in ['1234567890', '0987654321']:
            return True
        
        # All same digit
        if len(set(digits)) == 1:
            return True
        
        return False
    
    def _is_suspicious_pattern(self, phone):
        """Check for suspicious number patterns."""
        if not phone.startswith('+1') or len(phone) != 12:
            return False
        
        digits = phone[2:]  # Remove +1
        
        # Very low numbers (likely test numbers)
        if digits.startswith('000') or digits.startswith('111'):
            return True
        
        # High repetition
        digit_counts = Counter(digits)
        if max(digit_counts.values()) >= 6:  # Same digit appears 6+ times
            return True
        
        return False
    
    def generate_summary(self, frequency_stats, pattern_summary):
        """Generate comprehensive summary and recommendations."""
        print("📋 Generating analysis summary...")
        
        total_numbers = self.results['dataset_info']['total_unknown_numbers']
        numbers_with_conversations = frequency_stats['numbers_with_conversations']
        numbers_without_conversations = frequency_stats['numbers_without_conversations']
        
        # Calculate percentages
        conv_percentage = (numbers_with_conversations / total_numbers) * 100 if total_numbers > 0 else 0
        no_conv_percentage = (numbers_without_conversations / total_numbers) * 100 if total_numbers > 0 else 0
        
        # Free filtering potential
        toll_free = pattern_summary['toll_free_count']
        short_codes = pattern_summary['short_codes_count']
        business_patterns = pattern_summary['business_patterns_count']
        suspicious = pattern_summary['suspicious_patterns_count']
        
        free_filterable = toll_free + short_codes + business_patterns + suspicious
        free_filter_percentage = (free_filterable / total_numbers) * 100 if total_numbers > 0 else 0
        
        summary = {
            'total_unknown_numbers': total_numbers,
            'conversation_analysis': {
                'numbers_with_conversations': numbers_with_conversations,
                'numbers_without_conversations': numbers_without_conversations,
                'conversation_percentage': round(conv_percentage, 2),
                'no_conversation_percentage': round(no_conv_percentage, 2)
            },
            'free_filtering_potential': {
                'toll_free_numbers': toll_free,
                'short_codes': short_codes,
                'business_patterns': business_patterns,
                'suspicious_patterns': suspicious,
                'total_free_filterable': free_filterable,
                'free_filter_percentage': round(free_filter_percentage, 2),
                'remaining_for_api': total_numbers - free_filterable,
                'api_cost_estimate': f"${((total_numbers - free_filterable) * 0.01):.2f} (NumVerify)"
            },
            'recommendations': {
                'immediate_actions': [
                    f"Filter {toll_free} toll-free numbers (definitely commercial)",
                    f"Filter {short_codes} short codes (likely promotional)",
                    f"Review {business_patterns} business pattern numbers",
                    f"Exclude {suspicious} suspicious test numbers"
                ],
                'api_strategy': f"Use NumVerify API for remaining {total_numbers - free_filterable} numbers",
                'cost_benefit': f"Free filtering reduces API costs by {free_filter_percentage:.1f}%"
            }
        }
        
        self.results['summary'] = summary
        
        print(f"✅ Summary generated:")
        print(f"  📞 {conv_percentage:.1f}% of numbers have conversations")
        print(f"  🆓 {free_filter_percentage:.1f}% can be filtered for free")
        print(f"  💰 API cost reduced to ${((total_numbers - free_filterable) * 0.01):.2f}")
        
        return summary
    
    def save_results(self):
        """Save analysis results to JSON file."""
        output_file = Path("clean_phone_analysis_results.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {output_file}")
        return output_file
    
    def run_complete_analysis(self):
        """Run the complete clean phone analysis."""
        print("🚀 STARTING CLEAN PHONE NUMBER ANALYSIS")
        print("=" * 60)
        start_time = time.time()
        
        try:
            # Load data
            unknown_numbers = self.load_unknown_numbers()
            conversation_files = self.find_conversation_files()
            
            # Run analysis phases
            frequency_stats = self.analyze_conversation_frequency(unknown_numbers, conversation_files)
            pattern_stats, pattern_summary = self.analyze_patterns(unknown_numbers)
            
            # Generate summary
            summary = self.generate_summary(frequency_stats, pattern_summary)
            
            # Save results
            output_file = self.save_results()
            
            # Final report
            elapsed_time = time.time() - start_time
            print(f"\n🎉 ANALYSIS COMPLETE!")
            print(f"⏱️ Total time: {elapsed_time:.1f} seconds")
            print(f"📊 Results: {output_file}")
            
            return self.results
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            raise

def main():
    """Run the clean phone analysis."""
    analyzer = CleanPhoneAnalyzer()
    results = analyzer.run_complete_analysis()
    return results

if __name__ == "__main__":
    results = main()
