#!/usr/bin/env python3
"""
Immediate Free Filtering Tool
Filters 1,110 numbers (toll-free + suspicious patterns) from unknown_numbers.csv
"""

import csv
import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

class ImmediateFreeFilter:
    def __init__(self, data_dir="../gvoice-convert"):
        self.data_dir = Path(data_dir)
        self.conversations_dir = self.data_dir / "conversations"
        self.unknown_csv = self.conversations_dir / "unknown_numbers.csv"
        self.results = {
            'filtering_date': datetime.now().isoformat(),
            'toll_free_numbers': [],
            'suspicious_numbers': [],
            'filtered_summary': {},
            'remaining_numbers': []
        }
        
    def load_unknown_numbers(self):
        """Load unknown numbers from CSV."""
        print("📋 Loading unknown numbers from CSV...")
        
        unknown_numbers = []
        with open(self.unknown_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row['phone_number'].strip()
                if phone:
                    unknown_numbers.append(phone)
        
        print(f"✅ Loaded {len(unknown_numbers)} unknown numbers")
        return unknown_numbers
    
    def identify_toll_free_numbers(self, numbers):
        """Identify toll-free numbers."""
        print("🆓 Identifying toll-free numbers...")
        
        toll_free_patterns = [
            '+1800', '+1833', '+1844', '+1855', '+1866', '+1877', '+1888'
        ]
        
        toll_free_numbers = []
        for phone in numbers:
            if any(phone.startswith(pattern) for pattern in toll_free_patterns):
                toll_free_numbers.append(phone)
        
        print(f"✅ Found {len(toll_free_numbers)} toll-free numbers")
        return toll_free_numbers
    
    def identify_suspicious_numbers(self, numbers):
        """Identify suspicious/test number patterns."""
        print("⚠️ Identifying suspicious number patterns...")
        
        suspicious_numbers = []
        for phone in numbers:
            if self._is_suspicious_pattern(phone):
                suspicious_numbers.append(phone)
        
        print(f"✅ Found {len(suspicious_numbers)} suspicious numbers")
        return suspicious_numbers
    
    def _is_suspicious_pattern(self, phone):
        """Check for suspicious number patterns."""
        if not phone.startswith('+1') or len(phone) != 12:
            return False
        
        digits = phone[2:]  # Remove +1
        
        # All same digit
        if len(set(digits)) == 1:
            return True
        
        # Sequential patterns
        if digits in ['1234567890', '0987654321']:
            return True
        
        # Very low numbers (likely test)
        if digits.startswith('000') or digits.startswith('111'):
            return True
        
        # High repetition of same digit
        digit_counts = Counter(digits)
        if max(digit_counts.values()) >= 6:
            return True
        
        return False
    
    def filter_numbers(self):
        """Perform immediate free filtering."""
        print("🚀 STARTING IMMEDIATE FREE FILTERING")
        print("=" * 50)
        
        # Load unknown numbers
        unknown_numbers = self.load_unknown_numbers()
        
        # Identify filterable numbers
        toll_free_numbers = self.identify_toll_free_numbers(unknown_numbers)
        suspicious_numbers = self.identify_suspicious_numbers(unknown_numbers)
        
        # Remove duplicates (in case a number is both toll-free and suspicious)
        all_filtered_numbers = set(toll_free_numbers + suspicious_numbers)
        
        # Find remaining numbers
        remaining_numbers = [phone for phone in unknown_numbers if phone not in all_filtered_numbers]
        
        # Store results
        self.results['toll_free_numbers'] = sorted(toll_free_numbers)
        self.results['suspicious_numbers'] = sorted(suspicious_numbers)
        self.results['remaining_numbers'] = sorted(remaining_numbers)
        
        # Summary
        self.results['filtered_summary'] = {
            'total_unknown_numbers': len(unknown_numbers),
            'toll_free_count': len(toll_free_numbers),
            'suspicious_count': len(suspicious_numbers),
            'total_filtered': len(all_filtered_numbers),
            'remaining_count': len(remaining_numbers),
            'filtering_percentage': (len(all_filtered_numbers) / len(unknown_numbers)) * 100,
            'cost_savings': len(all_filtered_numbers) * 0.01  # NumVerify cost per number
        }
        
        print(f"✅ Filtering complete:")
        print(f"  📞 Total unknown numbers: {len(unknown_numbers)}")
        print(f"  🆓 Toll-free numbers: {len(toll_free_numbers)}")
        print(f"  ⚠️ Suspicious numbers: {len(suspicious_numbers)}")
        print(f"  🗑️ Total filtered: {len(all_filtered_numbers)}")
        print(f"  📊 Remaining: {len(remaining_numbers)}")
        print(f"  💰 Cost savings: ${len(all_filtered_numbers) * 0.01:.2f}")
        
        return self.results
    
    def export_filtered_results(self):
        """Export filtered results to CSV files."""
        print("💾 Exporting filtered results...")
        
        # Export toll-free numbers
        toll_free_file = Path("filtered_toll_free_numbers.csv")
        with open(toll_free_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['phone_number', 'filter_reason', 'confidence'])
            for phone in self.results['toll_free_numbers']:
                writer.writerow([phone, 'toll_free', '99%'])
        
        # Export suspicious numbers
        suspicious_file = Path("filtered_suspicious_numbers.csv")
        with open(suspicious_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['phone_number', 'filter_reason', 'confidence'])
            for phone in self.results['suspicious_numbers']:
                writer.writerow([phone, 'suspicious_pattern', '95%'])
        
        # Export remaining numbers
        remaining_file = Path("remaining_unknown_numbers.csv")
        with open(remaining_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['phone_number', 'display_name', 'is_spam', 'notes'])
            for phone in self.results['remaining_numbers']:
                writer.writerow([phone, '', 'false', ''])
        
        # Export summary
        summary_file = Path("filtering_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported results:")
        print(f"  🆓 Toll-free: {toll_free_file}")
        print(f"  ⚠️ Suspicious: {suspicious_file}")
        print(f"  📊 Remaining: {remaining_file}")
        print(f"  📋 Summary: {summary_file}")
        
        return {
            'toll_free_file': toll_free_file,
            'suspicious_file': suspicious_file,
            'remaining_file': remaining_file,
            'summary_file': summary_file
        }

def main():
    """Run immediate free filtering."""
    filter_tool = ImmediateFreeFilter()
    
    # Perform filtering
    results = filter_tool.filter_numbers()
    
    # Export results
    exported_files = filter_tool.export_filtered_results()
    
    print(f"\n🎉 IMMEDIATE FREE FILTERING COMPLETE!")
    print(f"📊 Filtered {results['filtered_summary']['total_filtered']} numbers")
    print(f"💰 Saved ${results['filtered_summary']['cost_savings']:.2f} in API costs")
    
    return results

if __name__ == "__main__":
    results = main()
