#!/usr/bin/env python3
"""
Date Range Filtering Analysis
Analyzes the impact of date range filtering on API cost optimization.
"""

import csv
import json
from pathlib import Path
from datetime import datetime

class DateRangeFilteringAnalyzer:
    def __init__(self):
        self.results = {
            'analysis_date': datetime.now().isoformat(),
            'date_range_logic': {},
            'cost_analysis': {},
            'recommendations': []
        }
        
    def analyze_date_range_impact(self):
        """Analyze the impact of date range filtering on API costs."""
        print("📅 ANALYZING DATE RANGE FILTERING IMPACT")
        print("=" * 50)
        
        # Load remaining numbers after free filtering
        remaining_file = Path("remaining_unknown_numbers.csv")
        if not remaining_file.exists():
            print("❌ Remaining numbers file not found. Run immediate_free_filtering.py first.")
            return None
        
        remaining_numbers = []
        with open(remaining_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row['phone_number'].strip()
                if phone:
                    remaining_numbers.append(phone)
        
        print(f"📊 Total remaining numbers: {len(remaining_numbers)}")
        
        # Load numbers with conversations (within date range)
        try:
            with open("clean_phone_analysis_results.json", 'r') as f:
                clean_results = json.load(f)
            conversation_numbers = set(clean_results['frequency_analysis']['detailed_data'].keys())
        except FileNotFoundError:
            print("⚠️ Clean analysis results not found")
            conversation_numbers = set()
        
        # Load name-based conversation numbers
        try:
            with open("name_based_conversation_linking_results.json", 'r') as f:
                name_results = json.load(f)
            name_based_numbers = set(name_results['conversation_mapping']['file_to_phone_mapping'].values())
        except FileNotFoundError:
            name_based_numbers = set()
        
        # Combine all conversation numbers
        all_conversation_numbers = conversation_numbers.union(name_based_numbers)
        
        # Categorize remaining numbers
        numbers_within_date_range = []
        numbers_outside_date_range = []
        
        for phone in remaining_numbers:
            if phone in all_conversation_numbers:
                numbers_within_date_range.append(phone)
            else:
                numbers_outside_date_range.append(phone)
        
        # Analysis results
        date_range_logic = {
            'total_remaining_numbers': len(remaining_numbers),
            'numbers_within_date_range': len(numbers_within_date_range),
            'numbers_outside_date_range': len(numbers_outside_date_range),
            'date_range_coverage': (len(numbers_within_date_range) / len(remaining_numbers)) * 100 if remaining_numbers else 0
        }
        
        # Cost analysis
        cost_analysis = {
            'original_api_cost': len(remaining_numbers) * 0.01,
            'date_range_optimized_cost': len(numbers_within_date_range) * 0.01,
            'cost_savings': (len(remaining_numbers) - len(numbers_within_date_range)) * 0.01,
            'cost_reduction_percentage': ((len(remaining_numbers) - len(numbers_within_date_range)) / len(remaining_numbers)) * 100 if remaining_numbers else 0
        }
        
        # Store results
        self.results['date_range_logic'] = date_range_logic
        self.results['cost_analysis'] = cost_analysis
        
        # Generate recommendations
        recommendations = [
            {
                'category': 'Cost Optimization',
                'insight': f"Only {len(numbers_within_date_range)} numbers need API lookup (within date range)",
                'action': 'Skip API lookup for numbers outside date range',
                'savings': f"${cost_analysis['cost_savings']:.2f} ({cost_analysis['cost_reduction_percentage']:.1f}% reduction)"
            },
            {
                'category': 'Strategy',
                'insight': f"{len(numbers_outside_date_range)} numbers are outside date range",
                'action': 'Mark as filtered (outside processing date range)',
                'impact': 'No processing needed - numbers won\'t be included in final output'
            }
        ]
        
        self.results['recommendations'] = recommendations
        
        # Print results
        print(f"✅ Analysis complete:")
        print(f"  📊 Total remaining numbers: {len(remaining_numbers)}")
        print(f"  📅 Within date range: {len(numbers_within_date_range)} ({date_range_logic['date_range_coverage']:.1f}%)")
        print(f"  📅 Outside date range: {len(numbers_outside_date_range)} ({100-date_range_logic['date_range_coverage']:.1f}%)")
        print(f"  💰 Original API cost: ${cost_analysis['original_api_cost']:.2f}")
        print(f"  💰 Optimized API cost: ${cost_analysis['date_range_optimized_cost']:.2f}")
        print(f"  💰 Cost savings: ${cost_analysis['cost_savings']:.2f} ({cost_analysis['cost_reduction_percentage']:.1f}% reduction)")
        
        return self.results
    
    def save_results(self):
        """Save analysis results."""
        output_file = Path("date_range_filtering_analysis_results.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {output_file}")
        return output_file

def main():
    """Run date range filtering analysis."""
    analyzer = DateRangeFilteringAnalyzer()
    results = analyzer.analyze_date_range_impact()
    
    if results:
        analyzer.save_results()
        
        print(f"\n🎉 DATE RANGE OPTIMIZATION ANALYSIS COMPLETE!")
        print(f"📊 Potential cost reduction: {results['cost_analysis']['cost_reduction_percentage']:.1f}%")
        print(f"💰 Savings: ${results['cost_analysis']['cost_savings']:.2f}")
    
    return results

if __name__ == "__main__":
    results = main()
