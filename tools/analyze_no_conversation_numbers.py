#!/usr/bin/env python3
"""
Analyze Numbers Without Conversations
Deep dive into the 7,940 numbers that have no conversations to understand why.
Also validates number format integrity in unknown_numbers.csv.
"""

import csv
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import time

class NoConversationAnalyzer:
    def __init__(self, data_dir="../gvoice-convert"):
        self.data_dir = Path(data_dir)
        self.conversations_dir = self.data_dir / "conversations"
        self.unknown_csv = self.conversations_dir / "unknown_numbers.csv"
        self.results = {
            'analysis_date': datetime.now().isoformat(),
            'format_validation': {},
            'no_conversation_analysis': {},
            'potential_issues': [],
            'recommendations': []
        }
        
    def validate_number_formats(self):
        """Validate that all numbers in unknown_numbers.csv have proper formats."""
        print("🔍 Validating number formats in unknown_numbers.csv...")
        
        if not self.unknown_csv.exists():
            raise FileNotFoundError(f"Unknown numbers CSV not found: {self.unknown_csv}")
        
        validation_results = {
            'total_numbers': 0,
            'valid_formats': 0,
            'invalid_formats': [],
            'format_categories': Counter(),
            'suspicious_patterns': [],
            'potential_bugs': []
        }
        
        with open(self.unknown_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                phone = row['phone_number'].strip()
                validation_results['total_numbers'] += 1
                
                # Check for various format issues
                format_valid, issues = self._validate_single_number(phone, row_num)
                
                if format_valid:
                    validation_results['valid_formats'] += 1
                    validation_results['format_categories'][self._categorize_format(phone)] += 1
                else:
                    validation_results['invalid_formats'].extend(issues)
                    validation_results['potential_bugs'].append({
                        'row': row_num,
                        'phone': phone,
                        'issues': issues
                    })
                
                # Check for suspicious patterns
                if self._is_suspicious_format(phone):
                    validation_results['suspicious_patterns'].append({
                        'row': row_num,
                        'phone': phone,
                        'reason': self._get_suspicion_reason(phone)
                    })
        
        print(f"✅ Format validation complete:")
        print(f"  📞 Total numbers: {validation_results['total_numbers']}")
        print(f"  ✅ Valid formats: {validation_results['valid_formats']}")
        print(f"  ❌ Invalid formats: {len(validation_results['invalid_formats'])}")
        print(f"  ⚠️ Suspicious patterns: {len(validation_results['suspicious_patterns'])}")
        
        if validation_results['potential_bugs']:
            print(f"  🐛 Potential bugs found: {len(validation_results['potential_bugs'])}")
        
        self.results['format_validation'] = validation_results
        return validation_results
    
    def _validate_single_number(self, phone, row_num):
        """Validate a single phone number format."""
        issues = []
        
        if not phone:
            issues.append("Empty phone number")
            return False, issues
        
        # Check for malformed patterns from the original bug
        if phone.count('+') > 1:
            issues.append("Multiple plus signs")
        
        if phone.startswith('+1+'):
            issues.append("Double plus format (+1+xxx)")
        
        # Check length and format
        if phone.startswith('+1'):
            if len(phone) != 12:
                issues.append(f"US number wrong length: {len(phone)} chars (should be 12)")
        elif phone.startswith('+'):
            if len(phone) < 10 or len(phone) > 16:
                issues.append(f"International number wrong length: {len(phone)} chars")
        else:
            issues.append("Missing country code (+ prefix)")
        
        # Check for non-digit characters after cleaning
        cleaned = re.sub(r'[^\d+]', '', phone)
        if cleaned != phone:
            issues.append("Contains non-digit characters")
        
        # Check for all zeros or other test patterns
        digits_only = re.sub(r'[^\d]', '', phone)
        if digits_only == '0' * len(digits_only):
            issues.append("All zeros (test number)")
        
        return len(issues) == 0, issues
    
    def _categorize_format(self, phone):
        """Categorize the phone number format."""
        if phone.startswith('+1800') or phone.startswith('+1833') or \
           phone.startswith('+1844') or phone.startswith('+1855') or \
           phone.startswith('+1866') or phone.startswith('+1877') or \
           phone.startswith('+1888'):
            return 'US_Toll_Free'
        elif phone.startswith('+1'):
            return 'US_Standard'
        elif phone.startswith('+'):
            return 'International'
        else:
            return 'Other'
    
    def _is_suspicious_format(self, phone):
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
    
    def _get_suspicion_reason(self, phone):
        """Get the reason why a number is suspicious."""
        if not phone.startswith('+1') or len(phone) != 12:
            return "Non-US format"
        
        digits = phone[2:]
        
        if len(set(digits)) == 1:
            return f"All same digit: {digits[0]}"
        
        if digits in ['1234567890', '0987654321']:
            return "Sequential pattern"
        
        if digits.startswith('000') or digits.startswith('111'):
            return "Very low number (test pattern)"
        
        digit_counts = Counter(digits)
        max_count = max(digit_counts.values())
        if max_count >= 6:
            return f"High repetition: digit appears {max_count} times"
        
        return "Unknown suspicious pattern"
    
    def analyze_no_conversation_numbers(self):
        """Analyze why numbers have no conversations."""
        print("🔍 Analyzing numbers without conversations...")
        
        # Load the clean analysis results
        try:
            with open("clean_phone_analysis_results.json", 'r') as f:
                clean_results = json.load(f)
        except FileNotFoundError:
            print("❌ Clean analysis results not found. Run clean_phone_analysis.py first.")
            return None
        
        # Get numbers without conversations
        detailed_data = clean_results['frequency_analysis']['detailed_data']
        numbers_with_conversations = set(detailed_data.keys())
        
        # Load all unknown numbers
        all_unknown_numbers = []
        with open(self.unknown_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row['phone_number'].strip()
                if phone:
                    all_unknown_numbers.append(phone)
        
        # Find numbers without conversations
        numbers_without_conversations = []
        for phone in all_unknown_numbers:
            if phone not in numbers_with_conversations:
                numbers_without_conversations.append(phone)
        
        print(f"📊 Found {len(numbers_without_conversations)} numbers without conversations")
        
        # Analyze patterns in numbers without conversations
        no_conv_analysis = {
            'total_count': len(numbers_without_conversations),
            'format_breakdown': Counter(),
            'toll_free_count': 0,
            'test_number_count': 0,
            'suspicious_count': 0,
            'international_count': 0,
            'area_code_analysis': Counter(),
            'sample_numbers': numbers_without_conversations[:20],  # First 20 as samples
            'potential_reasons': []
        }
        
        for phone in numbers_without_conversations:
            # Format categorization
            format_type = self._categorize_format(phone)
            no_conv_analysis['format_breakdown'][format_type] += 1
            
            # Specific pattern counts
            if format_type == 'US_Toll_Free':
                no_conv_analysis['toll_free_count'] += 1
            
            if self._is_suspicious_format(phone):
                no_conv_analysis['suspicious_count'] += 1
            
            if not phone.startswith('+1'):
                no_conv_analysis['international_count'] += 1
            
            # Area code analysis for US numbers
            if phone.startswith('+1') and len(phone) == 12:
                area_code = phone[2:5]
                no_conv_analysis['area_code_analysis'][area_code] += 1
        
        # Analyze potential reasons for no conversations
        potential_reasons = []
        
        if no_conv_analysis['toll_free_count'] > 0:
            potential_reasons.append(f"{no_conv_analysis['toll_free_count']} toll-free numbers - likely commercial/spam")
        
        if no_conv_analysis['suspicious_count'] > 0:
            potential_reasons.append(f"{no_conv_analysis['suspicious_count']} suspicious/test numbers")
        
        if no_conv_analysis['international_count'] > 0:
            potential_reasons.append(f"{no_conv_analysis['international_count']} international numbers - may not be in SMS dataset")
        
        # Check for area code patterns
        top_area_codes = no_conv_analysis['area_code_analysis'].most_common(10)
        if top_area_codes:
            potential_reasons.append(f"Top area codes: {', '.join([f'{code}({count})' for code, count in top_area_codes[:5]])}")
        
        no_conv_analysis['potential_reasons'] = potential_reasons
        
        print(f"✅ No-conversation analysis complete:")
        print(f"  🆓 Toll-free numbers: {no_conv_analysis['toll_free_count']}")
        print(f"  ⚠️ Suspicious/test numbers: {no_conv_analysis['suspicious_count']}")
        print(f"  🌍 International numbers: {no_conv_analysis['international_count']}")
        print(f"  📊 Format breakdown: {dict(no_conv_analysis['format_breakdown'])}")
        
        self.results['no_conversation_analysis'] = no_conv_analysis
        return no_conv_analysis
    
    def check_conversation_file_naming(self):
        """Check if conversation file naming matches number formats."""
        print("🔍 Checking conversation file naming patterns...")
        
        conversation_files = list(self.conversations_dir.glob("*.html"))
        naming_analysis = {
            'total_files': len(conversation_files),
            'valid_naming': 0,
            'invalid_naming': 0,
            'naming_issues': [],
            'sample_files': []
        }
        
        for html_file in conversation_files:
            if html_file.name in ['index.html', 'search.html']:
                continue
            
            filename_stem = html_file.stem
            
            # Check if filename looks like a phone number
            if re.match(r'^\+\d{10,15}$', filename_stem):
                naming_analysis['valid_naming'] += 1
            else:
                naming_analysis['invalid_naming'] += 1
                naming_analysis['naming_issues'].append(filename_stem)
            
            # Collect sample files
            if len(naming_analysis['sample_files']) < 10:
                naming_analysis['sample_files'].append(filename_stem)
        
        print(f"✅ File naming analysis:")
        print(f"  ✅ Valid phone number names: {naming_analysis['valid_naming']}")
        print(f"  ❌ Invalid names: {naming_analysis['invalid_naming']}")
        
        if naming_analysis['invalid_naming'] > 0:
            print(f"  ⚠️ Sample naming issues: {naming_analysis['naming_issues'][:5]}")
        
        return naming_analysis
    
    def generate_recommendations(self, format_validation, no_conv_analysis):
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Format validation recommendations
        if format_validation['potential_bugs']:
            recommendations.append({
                'category': 'Data Quality',
                'issue': f"{len(format_validation['potential_bugs'])} numbers with format issues",
                'recommendation': 'Review and fix malformed numbers in unknown_numbers.csv',
                'priority': 'High'
            })
        
        if format_validation['suspicious_patterns']:
            recommendations.append({
                'category': 'Data Quality',
                'issue': f"{len(format_validation['suspicious_patterns'])} suspicious number patterns",
                'recommendation': 'Consider filtering out test/suspicious numbers',
                'priority': 'Medium'
            })
        
        # No conversation analysis recommendations
        if no_conv_analysis['toll_free_count'] > 0:
            recommendations.append({
                'category': 'Filtering Strategy',
                'issue': f"{no_conv_analysis['toll_free_count']} toll-free numbers without conversations",
                'recommendation': 'Filter toll-free numbers as likely commercial/spam',
                'priority': 'High'
            })
        
        if no_conv_analysis['suspicious_count'] > 0:
            recommendations.append({
                'category': 'Filtering Strategy',
                'issue': f"{no_conv_analysis['suspicious_count']} suspicious numbers without conversations",
                'recommendation': 'Filter suspicious/test numbers',
                'priority': 'Medium'
            })
        
        if no_conv_analysis['international_count'] > 0:
            recommendations.append({
                'category': 'Analysis Strategy',
                'issue': f"{no_conv_analysis['international_count']} international numbers without conversations",
                'recommendation': 'Consider international numbers may not be in SMS dataset',
                'priority': 'Low'
            })
        
        self.results['recommendations'] = recommendations
        return recommendations
    
    def save_results(self):
        """Save analysis results."""
        output_file = Path("no_conversation_analysis_results.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {output_file}")
        return output_file
    
    def run_analysis(self):
        """Run the complete analysis."""
        print("🚀 STARTING NO-CONVERSATION ANALYSIS")
        print("=" * 60)
        start_time = time.time()
        
        try:
            # Validate number formats
            format_validation = self.validate_number_formats()
            
            # Analyze numbers without conversations
            no_conv_analysis = self.analyze_no_conversation_numbers()
            
            # Check file naming
            naming_analysis = self.check_conversation_file_naming()
            
            # Generate recommendations
            recommendations = self.generate_recommendations(format_validation, no_conv_analysis)
            
            # Save results
            output_file = self.save_results()
            
            # Final report
            elapsed_time = time.time() - start_time
            print(f"\n🎉 ANALYSIS COMPLETE!")
            print(f"⏱️ Total time: {elapsed_time:.1f} seconds")
            print(f"📊 Results: {output_file}")
            
            # Print key findings
            print(f"\n📋 KEY FINDINGS:")
            if format_validation['potential_bugs']:
                print(f"  🐛 {len(format_validation['potential_bugs'])} numbers with format issues")
            if no_conv_analysis:
                print(f"  🆓 {no_conv_analysis['toll_free_count']} toll-free numbers without conversations")
                print(f"  ⚠️ {no_conv_analysis['suspicious_count']} suspicious numbers without conversations")
            
            return self.results
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            raise

def main():
    """Run the no-conversation analysis."""
    analyzer = NoConversationAnalyzer()
    results = analyzer.run_analysis()
    return results

if __name__ == "__main__":
    results = main()
