#!/usr/bin/env python3
"""
Proper Date Range Filtering
Actually checks the dates in conversation files to determine which numbers are within/outside the date range.
"""

import csv
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class ProperDateRangeFiltering:
    def __init__(self):
        self.date_range_start = datetime(2022, 8, 1)
        self.date_range_end = datetime(2025, 6, 1)
        self.results = {
            'date_range': f"{self.date_range_start.strftime('%Y-%m-%d')} to {self.date_range_end.strftime('%Y-%m-%d')}",
            'analysis_results': {},
            'filtering_results': {}
        }
        
    def extract_dates_from_html(self, html_file):
        """Extract all dates from an HTML conversation file."""
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all date patterns
            date_pattern = r'(\d{4}-\d{2}-\d{2})'
            dates = re.findall(date_pattern, content)
            
            # Convert to datetime objects
            parsed_dates = []
            for date_str in dates:
                try:
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                    parsed_dates.append(parsed_date)
                except ValueError:
                    continue
            
            return parsed_dates
        except Exception as e:
            print(f"Error reading {html_file}: {e}")
            return []
    
    def analyze_conversation_dates(self):
        """Analyze dates in all conversation files."""
        print("📅 Analyzing dates in conversation files...")
        
        conversation_dir = Path("../gvoice-convert/conversations/")
        if not conversation_dir.exists():
            raise FileNotFoundError(f"Conversation directory not found: {conversation_dir}")
        
        phone_date_ranges = {}
        all_dates = []
        
        html_files = list(conversation_dir.glob("*.html"))
        print(f"Found {len(html_files)} HTML files")
        
        for i, html_file in enumerate(html_files):
            if i % 100 == 0:
                print(f"  Processing file {i+1}/{len(html_files)}: {html_file.name}")
            
            dates = self.extract_dates_from_html(html_file)
            if dates:
                min_date = min(dates)
                max_date = max(dates)
                
                # Extract phone number from filename
                phone = html_file.stem
                if phone.startswith('+'):
                    phone_date_ranges[phone] = {
                        'min_date': min_date,
                        'max_date': max_date,
                        'date_count': len(dates)
                    }
                
                all_dates.extend(dates)
        
        # Analyze overall date distribution
        if all_dates:
            overall_min = min(all_dates)
            overall_max = max(all_dates)
            dates_within_range = [d for d in all_dates if self.date_range_start <= d <= self.date_range_end]
            
            self.results['analysis_results'] = {
                'total_html_files': len(html_files),
                'files_with_dates': len(phone_date_ranges),
                'overall_date_range': {
                    'min_date': overall_min.isoformat(),
                    'max_date': overall_max.isoformat()
                },
                'date_range_filter': {
                    'start': self.date_range_start.isoformat(),
                    'end': self.date_range_end.isoformat()
                },
                'dates_within_range': len(dates_within_range),
                'dates_outside_range': len(all_dates) - len(dates_within_range),
                'percentage_within_range': (len(dates_within_range) / len(all_dates)) * 100 if all_dates else 0
            }
        
        return phone_date_ranges
    
    def categorize_numbers_by_date_range(self, phone_date_ranges):
        """Categorize numbers based on their actual date ranges."""
        print("📊 Categorizing numbers by date range...")
        
        within_range = []
        outside_range = []
        no_conversation = []
        
        # Load remaining numbers
        remaining_file = Path("remaining_unknown_numbers.csv")
        if not remaining_file.exists():
            raise FileNotFoundError("Remaining numbers file not found")
        
        with open(remaining_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            remaining_numbers = [row['phone_number'].strip() for row in reader if row['phone_number'].strip()]
        
        print(f"Analyzing {len(remaining_numbers)} remaining numbers...")
        
        for phone in remaining_numbers:
            if phone in phone_date_ranges:
                date_info = phone_date_ranges[phone]
                min_date = date_info['min_date']
                max_date = date_info['max_date']
                
                # Check if ANY part of the conversation falls within the date range
                if (min_date <= self.date_range_end and max_date >= self.date_range_start):
                    within_range.append({
                        'phone': phone,
                        'min_date': min_date.isoformat(),
                        'max_date': max_date.isoformat(),
                        'date_count': date_info['date_count']
                    })
                else:
                    outside_range.append({
                        'phone': phone,
                        'min_date': min_date.isoformat(),
                        'max_date': max_date.isoformat(),
                        'date_count': date_info['date_count']
                    })
            else:
                no_conversation.append(phone)
        
        self.results['filtering_results'] = {
            'total_remaining_numbers': len(remaining_numbers),
            'numbers_with_conversations': len(within_range) + len(outside_range),
            'numbers_within_date_range': len(within_range),
            'numbers_outside_date_range': len(outside_range),
            'numbers_no_conversation': len(no_conversation),
            'percentage_within_range': (len(within_range) / len(remaining_numbers)) * 100 if remaining_numbers else 0
        }
        
        return within_range, outside_range, no_conversation
    
    def export_results(self, within_range, outside_range, no_conversation):
        """Export the properly categorized results."""
        print("💾 Exporting properly categorized results...")
        
        # Export numbers within date range (candidates for API lookup)
        within_file = Path("properly_filtered_within_date_range.csv")
        with open(within_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['phone_number', 'min_date', 'max_date', 'date_count', 'notes'])
            for item in sorted(within_range, key=lambda x: x['phone']):
                writer.writerow([item['phone'], item['min_date'], item['max_date'], item['date_count'], 'Within date range - candidate for API lookup'])
        
        # Export numbers outside date range
        outside_file = Path("properly_filtered_outside_date_range.csv")
        with open(outside_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['phone_number', 'min_date', 'max_date', 'date_count', 'notes'])
            for item in sorted(outside_range, key=lambda x: x['phone']):
                writer.writerow([item['phone'], item['min_date'], item['max_date'], item['date_count'], 'Outside date range - no API lookup needed'])
        
        # Export numbers with no conversations
        no_conv_file = Path("properly_filtered_no_conversations.csv")
        with open(no_conv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['phone_number', 'notes'])
            for phone in sorted(no_conversation):
                writer.writerow([phone, 'No conversation file found - may be outside date range or invalid'])
        
        # Update results with file info
        self.results['export_files'] = {
            'within_date_range_file': str(within_file),
            'outside_date_range_file': str(outside_file),
            'no_conversation_file': str(no_conv_file),
            'within_count': len(within_range),
            'outside_count': len(outside_range),
            'no_conversation_count': len(no_conversation)
        }
        
        print(f"✅ Exported {len(within_range)} numbers within date range")
        print(f"✅ Exported {len(outside_range)} numbers outside date range")
        print(f"✅ Exported {len(no_conversation)} numbers with no conversations")
        
        return within_file, outside_file, no_conv_file
    
    def save_results(self):
        """Save the analysis results."""
        output_file = Path("proper_date_range_analysis_results.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Analysis results saved to: {output_file}")
        return output_file

def main():
    """Run proper date range filtering analysis."""
    print("🚀 PROPER DATE RANGE FILTERING ANALYSIS")
    print("=" * 50)
    
    filterer = ProperDateRangeFiltering()
    
    # Analyze conversation dates
    phone_date_ranges = filterer.analyze_conversation_dates()
    
    # Categorize numbers by actual date ranges
    within_range, outside_range, no_conversation = filterer.categorize_numbers_by_date_range(phone_date_ranges)
    
    # Export results
    within_file, outside_file, no_conv_file = filterer.export_results(within_range, outside_range, no_conversation)
    
    # Save analysis results
    output_file = filterer.save_results()
    
    print(f"\n🎯 PROPER DATE RANGE ANALYSIS COMPLETE!")
    print(f"📊 Numbers within date range: {len(within_range)} (candidates for API lookup)")
    print(f"📊 Numbers outside date range: {len(outside_range)} (no API needed)")
    print(f"📊 Numbers with no conversations: {len(no_conversation)}")
    print(f"💰 Potential API cost: ${len(within_range) * 0.01:.2f}")
    
    return filterer.results

if __name__ == "__main__":
    results = main()
