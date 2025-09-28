#!/usr/bin/env python3
"""
Create Test Sample
Extracts a small sample of numbers from the main dataset for API testing.
"""

import csv
import random
from pathlib import Path

def create_test_sample(input_file: str, output_file: str, sample_size: int = 5):
    """
    Create a small sample of numbers for testing.
    
    Args:
        input_file: Path to main CSV file
        output_file: Path to output test CSV file
        sample_size: Number of numbers to include in sample
    """
    print(f"📊 Creating test sample from {input_file}")
    print(f"🎯 Sample size: {sample_size} numbers")
    
    # Load all numbers
    all_numbers = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            phone = row['phone_number'].strip()
            if phone:
                all_numbers.append(row)
    
    print(f"📁 Total numbers available: {len(all_numbers)}")
    
    # Select random sample
    if len(all_numbers) <= sample_size:
        sample_numbers = all_numbers
        print(f"⚠️ Dataset smaller than sample size, using all {len(all_numbers)} numbers")
    else:
        sample_numbers = random.sample(all_numbers, sample_size)
        print(f"🎲 Randomly selected {sample_size} numbers")
    
    # Export sample
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['phone_number', 'min_date', 'max_date', 'date_count', 'notes']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in sample_numbers:
            writer.writerow({
                'phone_number': row['phone_number'],
                'min_date': row.get('min_date', ''),
                'max_date': row.get('max_date', ''),
                'date_count': row.get('date_count', ''),
                'notes': f"Test sample - {row.get('notes', '')}"
            })
    
    print(f"✅ Test sample exported to: {output_file}")
    print(f"💰 Estimated test cost: ${len(sample_numbers) * 0.01:.2f}")
    
    # Show sample numbers
    print(f"\n📋 Sample numbers:")
    for i, row in enumerate(sample_numbers, 1):
        print(f"  {i}. {row['phone_number']} ({row.get('min_date', 'Unknown date')})")

def main():
    """Main function."""
    input_file = "properly_filtered_within_date_range.csv"
    output_file = "test_sample_numbers.csv"
    sample_size = 5
    
    if not Path(input_file).exists():
        print(f"❌ Input file not found: {input_file}")
        return
    
    create_test_sample(input_file, output_file, sample_size)
    
    print(f"\n🎯 Next steps:")
    print(f"1. Review the sample in {output_file}")
    print(f"2. Run: python tools/test_numverify_api.py")
    print(f"3. Use the test sample file for validation")

if __name__ == "__main__":
    main()
