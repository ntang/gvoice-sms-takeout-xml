#!/usr/bin/env python3
"""
Name-Based Conversation Linking Analysis
Uses phone_lookup.txt to map phone numbers to names, then finds corresponding conversation files.
"""

import csv
import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import time

class NameBasedConversationLinker:
    def __init__(self, data_dir="../gvoice-convert"):
        self.data_dir = Path(data_dir)
        self.conversations_dir = self.data_dir / "conversations"
        self.phone_lookup_file = Path("phone_lookup.txt")
        self.unknown_csv = self.conversations_dir / "unknown_numbers.csv"
        self.results = {
            'analysis_date': datetime.now().isoformat(),
            'phone_lookup_analysis': {},
            'conversation_mapping': {},
            'enhanced_frequency': {},
            'recommendations': []
        }
        
    def load_phone_lookup_mappings(self):
        """Load phone number to name mappings from phone_lookup.txt."""
        print("📋 Loading phone number to name mappings...")
        
        if not self.phone_lookup_file.exists():
            raise FileNotFoundError(f"Phone lookup file not found: {self.phone_lookup_file}")
        
        mappings = {
            'phone_to_name': {},
            'name_to_phone': {},
            'total_mappings': 0,
            'name_patterns': Counter(),
            'sample_mappings': []
        }
        
        with open(self.phone_lookup_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse format: phone_number|alias[|filter]
                parts = line.split('|')
                if len(parts) >= 2:
                    phone = parts[0].strip()
                    name = parts[1].strip()
                    
                    # Store mappings
                    mappings['phone_to_name'][phone] = name
                    mappings['name_to_phone'][name] = phone
                    mappings['total_mappings'] += 1
                    
                    # Analyze name patterns
                    if '_' in name:
                        mappings['name_patterns']['underscore_separated'] += 1
                    elif ' ' in name:
                        mappings['name_patterns']['space_separated'] += 1
                    else:
                        mappings['name_patterns']['single_word'] += 1
                    
                    # Collect samples
                    if len(mappings['sample_mappings']) < 10:
                        mappings['sample_mappings'].append({
                            'phone': phone,
                            'name': name,
                            'filter': parts[2].strip() if len(parts) > 2 else None
                        })
        
        print(f"✅ Loaded {mappings['total_mappings']} phone-to-name mappings")
        print(f"  📊 Name patterns: {dict(mappings['name_patterns'])}")
        
        self.results['phone_lookup_analysis'] = mappings
        return mappings
    
    def find_conversation_files_by_name(self, name_mappings):
        """Find conversation files that match names from phone_lookup.txt."""
        print("🔍 Finding conversation files by name patterns...")
        
        conversation_files = list(self.conversations_dir.glob("*.html"))
        name_based_files = [f for f in conversation_files if not f.name.startswith('+')]
        
        print(f"📁 Found {len(conversation_files)} total conversation files")
        print(f"📁 Found {len(name_based_files)} name-based conversation files")
        
        # Create mapping from conversation files to phone numbers
        file_to_phone_mapping = {}
        matched_files = 0
        unmatched_files = []
        
        for file in name_based_files:
            filename_stem = file.stem  # Remove .html extension
            
            # Try exact match first
            if filename_stem in name_mappings['name_to_phone']:
                phone = name_mappings['name_to_phone'][filename_stem]
                file_to_phone_mapping[file.name] = phone
                matched_files += 1
                continue
            
            # Try partial matches (handle cases like "Aniella_SusanT" where one name might be in lookup)
            matched_phone = self._find_partial_match(filename_stem, name_mappings)
            if matched_phone:
                file_to_phone_mapping[file.name] = matched_phone
                matched_files += 1
            else:
                unmatched_files.append(filename_stem)
        
        mapping_results = {
            'total_name_based_files': len(name_based_files),
            'matched_files': matched_files,
            'unmatched_files': len(unmatched_files),
            'match_rate': (matched_files / len(name_based_files)) * 100 if name_based_files else 0,
            'file_to_phone_mapping': file_to_phone_mapping,
            'unmatched_file_samples': unmatched_files[:10],
            'matched_file_samples': list(file_to_phone_mapping.items())[:10]
        }
        
        print(f"✅ Name-based file mapping complete:")
        print(f"  📞 Matched files: {matched_files}/{len(name_based_files)} ({mapping_results['match_rate']:.1f}%)")
        print(f"  ❓ Unmatched files: {len(unmatched_files)}")
        
        self.results['conversation_mapping'] = mapping_results
        return mapping_results
    
    def _find_partial_match(self, filename_stem, name_mappings):
        """Try to find partial matches between filename and known names."""
        # Split filename by common separators
        name_parts = filename_stem.replace('_', ' ').replace('-', ' ').split()
        
        # Try to match against known names
        for known_name, phone in name_mappings['name_to_phone'].items():
            known_parts = known_name.replace('_', ' ').replace('-', ' ').split()
            
            # Check if any name parts match
            for part in name_parts:
                if part in known_parts and len(part) > 2:  # Avoid very short matches
                    return phone
        
        return None
    
    def load_unknown_numbers(self):
        """Load unknown numbers from CSV."""
        print("📋 Loading unknown numbers...")
        
        unknown_numbers = []
        with open(self.unknown_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row['phone_number'].strip()
                if phone:
                    unknown_numbers.append(phone)
        
        print(f"✅ Loaded {len(unknown_numbers)} unknown numbers")
        return unknown_numbers
    
    def enhanced_frequency_analysis(self, unknown_numbers, phone_mappings, file_mappings):
        """Perform enhanced frequency analysis including name-based conversations."""
        print("📊 Performing enhanced frequency analysis...")
        
        # Load clean analysis results for baseline
        try:
            with open("clean_phone_analysis_results.json", 'r') as f:
                clean_results = json.load(f)
            baseline_frequency = clean_results['frequency_analysis']['detailed_data']
        except FileNotFoundError:
            print("⚠️ Clean analysis results not found, starting from scratch")
            baseline_frequency = {}
        
        enhanced_frequency = {
            'baseline_conversations': len(baseline_frequency),
            'name_based_conversations': 0,
            'total_enhanced_conversations': 0,
            'new_numbers_with_conversations': [],
            'enhanced_details': {},
            'impact_analysis': {}
        }
        
        # Count name-based conversations
        name_based_phones = set(file_mappings['file_to_phone_mapping'].values())
        enhanced_frequency['name_based_conversations'] = len(name_based_phones)
        
        # Combine baseline and name-based conversations
        all_conversation_phones = set(baseline_frequency.keys()).union(name_based_phones)
        enhanced_frequency['total_enhanced_conversations'] = len(all_conversation_phones)
        
        # Find new numbers that have conversations through name-based mapping
        new_conversation_numbers = []
        for phone in unknown_numbers:
            if phone in name_based_phones and phone not in baseline_frequency:
                new_conversation_numbers.append(phone)
        
        enhanced_frequency['new_numbers_with_conversations'] = new_conversation_numbers
        
        # Calculate impact
        original_no_conversation = len(unknown_numbers) - len(baseline_frequency)
        enhanced_no_conversation = len(unknown_numbers) - len(all_conversation_phones)
        conversation_increase = len(all_conversation_phones) - len(baseline_frequency)
        
        enhanced_frequency['impact_analysis'] = {
            'original_no_conversation_count': original_no_conversation,
            'enhanced_no_conversation_count': enhanced_no_conversation,
            'conversation_increase': conversation_increase,
            'improvement_percentage': (conversation_increase / len(unknown_numbers)) * 100 if unknown_numbers else 0
        }
        
        print(f"✅ Enhanced frequency analysis complete:")
        print(f"  📞 Baseline conversations: {enhanced_frequency['baseline_conversations']}")
        print(f"  📞 Name-based conversations: {enhanced_frequency['name_based_conversations']}")
        print(f"  📞 Total enhanced conversations: {enhanced_frequency['total_enhanced_conversations']}")
        print(f"  📈 New conversations found: {conversation_increase}")
        print(f"  📊 Improvement: {enhanced_frequency['impact_analysis']['improvement_percentage']:.1f}%")
        
        self.results['enhanced_frequency'] = enhanced_frequency
        return enhanced_frequency
    
    def generate_recommendations(self, phone_mappings, file_mappings, enhanced_frequency):
        """Generate recommendations based on enhanced analysis."""
        recommendations = []
        
        # Match rate recommendations
        match_rate = file_mappings['match_rate']
        if match_rate < 50:
            recommendations.append({
                'category': 'Data Quality',
                'issue': f"Low name-based file match rate: {match_rate:.1f}%",
                'recommendation': 'Consider improving name matching algorithms or phone_lookup.txt completeness',
                'priority': 'Medium'
            })
        elif match_rate > 80:
            recommendations.append({
                'category': 'Data Quality',
                'issue': f"High name-based file match rate: {match_rate:.1f}%",
                'recommendation': 'Excellent phone-to-name mapping coverage',
                'priority': 'Low'
            })
        
        # Conversation improvement recommendations
        improvement = enhanced_frequency['impact_analysis']['improvement_percentage']
        if improvement > 5:
            recommendations.append({
                'category': 'Analysis Enhancement',
                'issue': f"Significant conversation discovery improvement: {improvement:.1f}%",
                'recommendation': 'Name-based linking provides substantial value for filtering decisions',
                'priority': 'High'
            })
        
        # API cost optimization recommendations
        new_conversations = len(enhanced_frequency['new_numbers_with_conversations'])
        if new_conversations > 0:
            cost_savings = new_conversations * 0.01  # NumVerify cost per number
            recommendations.append({
                'category': 'Cost Optimization',
                'issue': f"Found {new_conversations} additional numbers with conversations",
                'recommendation': f"Potential API cost savings: ${cost_savings:.2f} (can skip these numbers)",
                'priority': 'High'
            })
        
        self.results['recommendations'] = recommendations
        return recommendations
    
    def save_results(self):
        """Save analysis results."""
        output_file = Path("name_based_conversation_linking_results.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {output_file}")
        return output_file
    
    def run_analysis(self):
        """Run the complete name-based conversation linking analysis."""
        print("🚀 STARTING NAME-BASED CONVERSATION LINKING ANALYSIS")
        print("=" * 60)
        start_time = time.time()
        
        try:
            # Load phone-to-name mappings
            phone_mappings = self.load_phone_lookup_mappings()
            
            # Find conversation files by name
            file_mappings = self.find_conversation_files_by_name(phone_mappings)
            
            # Load unknown numbers
            unknown_numbers = self.load_unknown_numbers()
            
            # Enhanced frequency analysis
            enhanced_frequency = self.enhanced_frequency_analysis(unknown_numbers, phone_mappings, file_mappings)
            
            # Generate recommendations
            recommendations = self.generate_recommendations(phone_mappings, file_mappings, enhanced_frequency)
            
            # Save results
            output_file = self.save_results()
            
            # Final report
            elapsed_time = time.time() - start_time
            print(f"\n🎉 ANALYSIS COMPLETE!")
            print(f"⏱️ Total time: {elapsed_time:.1f} seconds")
            print(f"📊 Results: {output_file}")
            
            # Print key findings
            print(f"\n📋 KEY FINDINGS:")
            print(f"  🔗 {file_mappings['match_rate']:.1f}% of name-based files matched to phone numbers")
            print(f"  📈 {enhanced_frequency['impact_analysis']['conversation_increase']} additional conversations found")
            print(f"  💰 Potential cost savings: ${len(enhanced_frequency['new_numbers_with_conversations']) * 0.01:.2f}")
            
            return self.results
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            raise

def main():
    """Run the name-based conversation linking analysis."""
    linker = NameBasedConversationLinker()
    results = linker.run_analysis()
    return results

if __name__ == "__main__":
    results = main()
