#!/usr/bin/env python3
"""
Pipeline Bug Investigation Tool
Investigate why malformed phone numbers are being written to unknown_numbers.csv
"""

import csv
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

class PipelineBugInvestigator:
    def __init__(self, data_dir="../gvoice-convert"):
        self.data_dir = Path(data_dir)
        self.conversations_dir = self.data_dir / "conversations"
        self.unknown_numbers_file = self.conversations_dir / "unknown_numbers.csv"
        self.log_entries = []
        
    def log(self, message):
        """Log investigation steps"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_entries.append(log_entry)
        print(log_entry)
    
    def analyze_malformed_patterns(self):
        """Analyze the patterns of malformed phone numbers"""
        self.log("🔍 ANALYZING MALFORMED PHONE NUMBER PATTERNS...")
        
        malformed_patterns = defaultdict(list)
        total_numbers = 0
        
        with open(self.unknown_numbers_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row['phone_number'].strip()
                if phone:
                    total_numbers += 1
                    
                    # Categorize malformed patterns
                    if phone.startswith('+1+'):
                        malformed_patterns['double_plus'].append(phone)
                    elif phone.startswith('+1') and len(phone) > 12:
                        malformed_patterns['too_long_with_plus1'].append(phone)
                    elif phone.startswith('+') and not phone.startswith('+1'):
                        malformed_patterns['international'].append(phone)
                    elif re.match(r'^\+1\d{10}$', phone):
                        malformed_patterns['correct_format'].append(phone)
                    elif re.match(r'^\+\d{11}$', phone) and phone.startswith('+1'):
                        malformed_patterns['correct_format'].append(phone)
                    else:
                        malformed_patterns['other_malformed'].append(phone)
        
        self.log(f"Total numbers analyzed: {total_numbers:,}")
        
        for pattern_type, numbers in malformed_patterns.items():
            percentage = len(numbers) / total_numbers * 100
            self.log(f"{pattern_type}: {len(numbers):,} ({percentage:.1f}%)")
            
            # Show examples
            examples = numbers[:5]
            self.log(f"  Examples: {examples}")
        
        return malformed_patterns, total_numbers
    
    def investigate_phone_extraction_source(self):
        """Investigate where these malformed numbers come from in the processing pipeline"""
        self.log("🔍 INVESTIGATING PHONE EXTRACTION SOURCE...")
        
        # Look for phone extraction logic in the codebase
        phone_extraction_files = [
            "sms.py",
            "core/phone_lookup.py", 
            "processors/file_processor.py",
            "processors/html_processor.py"
        ]
        
        extraction_patterns = []
        
        for file_path in phone_extraction_files:
            if Path(file_path).exists():
                self.log(f"Checking {file_path}...")
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                    # Look for phone number extraction patterns
                    phone_regex_patterns = re.findall(r'["\'].*?\+.*?["\']', content)
                    if phone_regex_patterns:
                        self.log(f"  Found phone patterns: {phone_regex_patterns[:3]}")
                        extraction_patterns.extend(phone_regex_patterns)
                        
                    # Look for phone number processing functions
                    if 'extract' in content.lower() and 'phone' in content.lower():
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'extract' in line.lower() and 'phone' in line.lower():
                                context = lines[max(0, i-2):i+3]
                                self.log(f"  Phone extraction context in {file_path}:")
                                for ctx_line in context:
                                    self.log(f"    {ctx_line.strip()}")
                                break
                                
                except Exception as e:
                    self.log(f"  Error reading {file_path}: {e}")
            else:
                self.log(f"  {file_path} not found")
        
        return extraction_patterns
    
    def check_html_source_formats(self):
        """Check what phone number formats appear in the original HTML files"""
        self.log("🔍 CHECKING ORIGINAL HTML SOURCE FORMATS...")
        
        # Look at a few HTML files to see original phone number formats
        html_files = list(Path("../gvoice-convert").glob("*.html"))[:10]
        
        phone_formats_found = set()
        
        for html_file in html_files:
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for phone number patterns in HTML
                phone_patterns = [
                    r'\+1\d{10}',  # +1 followed by 10 digits
                    r'\+\d{10,15}',  # + followed by 10-15 digits
                    r'tel:[^"\']*',  # tel: links
                    r'\(\d{3}\)\s*\d{3}-\d{4}',  # (123) 456-7890
                    r'\d{3}-\d{3}-\d{4}',  # 123-456-7890
                ]
                
                for pattern in phone_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        phone_formats_found.update(matches[:5])  # Add first 5 matches
                        
            except Exception as e:
                self.log(f"Error reading {html_file}: {e}")
        
        self.log(f"Phone formats found in HTML source:")
        for fmt in sorted(list(phone_formats_found)[:10]):
            self.log(f"  {fmt}")
        
        return phone_formats_found
    
    def trace_unknown_numbers_generation(self):
        """Try to trace how unknown_numbers.csv is generated"""
        self.log("🔍 TRACING UNKNOWN_NUMBERS.CSV GENERATION...")
        
        # Look for code that writes to unknown_numbers.csv
        search_files = [
            "sms.py",
            "core/phone_lookup.py",
            "core/conversation_manager.py",
            "processors/file_processor.py",
            "processors/html_processor.py"
        ]
        
        csv_writers = []
        
        for file_path in search_files:
            if Path(file_path).exists():
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    # Look for CSV writing or unknown_numbers references
                    if 'unknown_numbers' in content.lower():
                        self.log(f"Found 'unknown_numbers' reference in {file_path}")
                        
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'unknown_numbers' in line.lower():
                                context = lines[max(0, i-3):i+4]
                                self.log(f"  Context around line {i+1}:")
                                for j, ctx_line in enumerate(context):
                                    marker = " -> " if j == 3 else "    "
                                    self.log(f"{marker}{ctx_line.strip()}")
                                break
                    
                    # Look for CSV writing
                    if 'csv' in content.lower() and 'write' in content.lower():
                        csv_writers.append(file_path)
                        
                except Exception as e:
                    self.log(f"Error reading {file_path}: {e}")
        
        self.log(f"Files with CSV writing capability: {csv_writers}")
        return csv_writers
    
    def comprehensive_bug_investigation(self):
        """Run comprehensive investigation into the pipeline bug"""
        self.log("🚨 COMPREHENSIVE PIPELINE BUG INVESTIGATION")
        self.log("=" * 60)
        
        # Analyze malformed patterns
        patterns, total = self.analyze_malformed_patterns()
        
        # Investigate extraction source
        extraction_patterns = self.investigate_phone_extraction_source()
        
        # Check HTML source formats
        html_formats = self.check_html_source_formats()
        
        # Trace CSV generation
        csv_writers = self.trace_unknown_numbers_generation()
        
        # Generate summary
        self.log("\n📊 INVESTIGATION SUMMARY:")
        self.log("=" * 40)
        
        # Calculate malformed percentage
        malformed_count = sum(len(nums) for pattern_type, nums in patterns.items() 
                             if pattern_type != 'correct_format')
        malformed_percentage = malformed_count / total * 100
        
        self.log(f"Total numbers: {total:,}")
        self.log(f"Malformed numbers: {malformed_count:,} ({malformed_percentage:.1f}%)")
        self.log(f"Correct format: {len(patterns.get('correct_format', [])):,}")
        
        # Most common malformed pattern
        largest_malformed = max(
            [(k, v) for k, v in patterns.items() if k != 'correct_format'],
            key=lambda x: len(x[1]),
            default=('none', [])
        )
        
        if largest_malformed[1]:
            self.log(f"Most common malformed pattern: {largest_malformed[0]} ({len(largest_malformed[1]):,} numbers)")
        
        self.log(f"Files that write CSV: {len(csv_writers)}")
        self.log(f"Phone extraction patterns found: {len(extraction_patterns)}")
        
        return {
            'total_numbers': total,
            'malformed_patterns': {k: len(v) for k, v in patterns.items()},
            'malformed_percentage': malformed_percentage,
            'csv_writers': csv_writers,
            'extraction_patterns': extraction_patterns[:10],  # First 10
            'html_formats_sample': list(html_formats)[:10]
        }

def main():
    """Run pipeline bug investigation"""
    investigator = PipelineBugInvestigator()
    results = investigator.comprehensive_bug_investigation()
    
    # Save results
    with open('pipeline_bug_investigation.json', 'w') as f:
        import json
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'log_entries': investigator.log_entries,
            'results': results
        }, f, indent=2)
    
    print(f"\n📁 Investigation results saved to: pipeline_bug_investigation.json")
    return results

if __name__ == "__main__":
    results = main()
