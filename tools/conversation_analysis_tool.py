#!/usr/bin/env python3
"""
Conversation Analysis Tool
Creates HTML table with NumVerify data and conversation samples for classification analysis.
"""

import json
import csv
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

class ConversationAnalyzer:
    def __init__(self):
        self.results = []
        
    def load_numverify_data(self, numverify_file: str) -> List[Dict]:
        """Load NumVerify results."""
        with open(numverify_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['detailed_results']
    
    def extract_conversation_sample(self, phone_number: str) -> Dict:
        """
        Extract conversation sample from HTML file.
        
        Args:
            phone_number: Phone number to look up
            
        Returns:
            Dict with conversation metadata and sample
        """
        # Convert phone number to filename format
        clean_phone = phone_number.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        html_file = Path(f"../gvoice-convert/conversations/{phone_number}.html")
        
        if not html_file.exists():
            return {
                'conversation_found': False,
                'error': 'HTML file not found',
                'sample_text': '',
                'message_count': 0,
                'first_message': '',
                'date_range': ''
            }
        
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Get the original text content for date extraction
            text_content = soup.get_text()
            
            # Extract actual message content by looking for message cells/rows
            messages = []
            
            # Look for message content in table cells with class="message"
            message_elements = soup.find_all('td', class_='message')
            
            for element in message_elements:
                # Get text and decode HTML entities
                text = element.get_text().strip()
                if text and len(text) > 5:  # Only meaningful messages
                    messages.append(text)
            
            # If we didn't find messages in structured elements, fall back to text extraction
            if not messages:
                # Remove HTML tags and get clean text
                clean_text = re.sub(r'<[^>]+>', ' ', text_content)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                
                # Split into lines and find message-like content
                lines = clean_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if len(line) > 15 and not any(metadata in line.lower() for metadata in [
                        'sms conversation', 'total messages', 'date range', 'converted from',
                        'timestamp', 'sender', 'message', 'attachments', phone_number.replace('+', ''),
                        'google voice', 'takeout'
                    ]):
                        # Skip timestamp and phone number patterns
                        if not re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line) and not re.match(r'^\+?\d{10,15}$', line):
                            messages.append(line)
            
            # Combine messages into sample text
            if messages:
                sample_text = ' '.join(messages)
                # Limit to reasonable length but prioritize showing more actual content
                if len(sample_text) > 800:
                    sample_text = sample_text[:800] + "..."
                first_message = messages[0][:300] + "..." if len(messages[0]) > 300 else messages[0]
            else:
                sample_text = "No message content found"
                first_message = ""
            
            # Count messages
            message_count = len(messages)
            
            # Try to extract date range from the original text
            date_range = self.extract_date_range(text_content)
            
            return {
                'conversation_found': True,
                'sample_text': sample_text,
                'message_count': message_count,
                'first_message': first_message,
                'date_range': date_range,
                'full_text_length': len(text_content)
            }
            
        except Exception as e:
            import traceback
            error_details = f'Error reading file: {str(e)}\n{traceback.format_exc()}'
            return {
                'conversation_found': False,
                'error': error_details,
                'sample_text': '',
                'message_count': 0,
                'first_message': '',
                'date_range': ''
            }
    
    def extract_date_range(self, text: str) -> str:
        """Extract date range from conversation text."""
        # Look for date patterns
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        dates = re.findall(date_pattern, text)
        
        if len(dates) >= 2:
            return f"{dates[0]} to {dates[-1]}"
        elif len(dates) == 1:
            return dates[0]
        else:
            return "No dates found"
    
    def classify_number(self, numverify_data: Dict, conversation_data: Dict) -> Dict:
        """
        Apply classification rules based on NumVerify and conversation data.
        
        Args:
            numverify_data: NumVerify API response
            conversation_data: Conversation sample data
            
        Returns:
            Classification result with confidence
        """
        if not numverify_data.get('lookup_successful', False):
            return {
                'classification': 'unknown',
                'confidence': 0,
                'reasoning': 'NumVerify lookup failed'
            }
        
        carrier = numverify_data.get('carrier', '').lower()
        line_type = numverify_data.get('line_type', '').lower()
        location = numverify_data.get('location', '').lower()
        sample_text = conversation_data.get('sample_text', '').lower()
        
        # SPAM/COMMERCIAL INDICATORS (HIGHEST PRIORITY - OVERRIDE CARRIER INFO)
        spam_indicators = [
            # Political spam
            'donation', 'donate', 'campaign', 'election', 'vote', 'candidate', 'politician',
            'fundraising', 'fundraiser', 'contribute', 'contribution', 'political action',
            'pac', 'super pac', 'triple-match', 'match your donation', 'rush a donation',
            'no surrender', 'take back the house', 'special election', 'gop majority',
            'democrats can regain', 'turn out the vote', 'win tonight',
            
            # Marketing/spam
            'text stop to quit', 'text stop to opt out', 'text stop to end', 'text stop to stop', 'text stop 2 end',
            'stop to end', 'stop to stop', 'stop 2 end', 'stop to quit', 'stop to opt out',
            'reply stop', 'reply stop to end', 'reply stop to quit', 'reply stop to opt out',
            'unsubscribe', 'opt out', 'opt-out',
            'limited time offer', 'act now', 'call now', 'click here', 'visit our website',
            'free trial', 'special offer', 'discount', 'sale', 'deal', 'promo',
            'congratulations', 'you have won', 'claim your prize', 'winner',
            'urgent', 'immediate action', 'expires soon', 'today only',
            
            # Business/automated
            'your account', 'payment due', 'invoice', 'billing', 'subscription',
            'auto-renewal', 'renewal notice', 'service interruption', 'account suspended',
            'verify your account', 'confirm your identity', 'security alert',
            
            # Food delivery services
            'doordash', 'door dash', 'caviar', 'uber', 'uber eats', 'ubereats', 'uber eats',
            'grubhub', 'grub hub', 'postmates', 'post mates', 'seamless',
            'delivery order', 'food delivery', 'restaurant delivery', 'order ready',
            'your order is ready', 'order pickup', 'delivery driver', 'courier',
            
            # Generic spam patterns
            'click the link', 'follow this link', 'visit us at', 'check out',
            'share this', 'forward this', 'pass it on', 'tell your friends'
        ]
        
        spam_score = sum(1 for indicator in spam_indicators if indicator in sample_text)
        
        if spam_score >= 1:  # Even one spam indicator is very strong evidence
            confidence = min(95, 70 + (spam_score * 10))  # 70-95% confidence based on spam indicators
            return {
                'classification': 'commercial',
                'confidence': confidence,
                'reasoning': f'Spam/commercial content detected ({spam_score} indicators): {sample_text[:100]}...'
            }
        
        # Commercial carriers (high confidence)
        commercial_carriers = [
            'emergency networks llc',
            'commio llc',
            'twilio', 'bandwidth', 'vonage', 'ringcentral', '8x8'
        ]
        
        if any(commercial_carrier in carrier for commercial_carrier in commercial_carriers):
            return {
                'classification': 'commercial',
                'confidence': 90,
                'reasoning': f'Known business carrier: {carrier}'
            }
        
        # Personal carriers (high confidence)
        personal_carriers = [
            't-mobile usa inc.',
            'at&t mobility llc',
            'cellco partnership (verizon wireless)',
            'united states cellular corp.'
        ]
        
        if any(personal_carrier in carrier for personal_carrier in personal_carriers):
            return {
                'classification': 'personal',
                'confidence': 85,
                'reasoning': f'Known personal carrier: {carrier}'
            }
        
        # Business conversation indicators (moderate confidence)
        business_indicators = [
            'business', 'company', 'corp', 'llc', 'inc', 'service', 'customer',
            'appointment', 'invoice', 'payment', 'account', 'support', 'sales',
            'marketing', 'advertisement', 'promotion', 'offer'
        ]
        
        business_score = sum(1 for indicator in business_indicators if indicator in sample_text)
        
        if business_score >= 2:
            return {
                'classification': 'commercial',
                'confidence': 75,
                'reasoning': f'Business language detected ({business_score} indicators)'
            }
        
        # Personal conversation indicators
        personal_indicators = [
            'hey', 'hi', 'hello', 'thanks', 'thank you', 'love', 'miss you',
            'family', 'friend', 'dinner', 'lunch', 'weekend', 'vacation',
            'home', 'house', 'kids', 'children', 'mom', 'dad'
        ]
        
        personal_score = sum(1 for indicator in personal_indicators if indicator in sample_text)
        
        if personal_score >= 2:
            return {
                'classification': 'personal',
                'confidence': 80,
                'reasoning': f'Personal language detected ({personal_score} indicators)'
            }
        
        # Default based on line type
        if line_type == 'mobile':
            return {
                'classification': 'personal',
                'confidence': 60,
                'reasoning': 'Mobile number, likely personal'
            }
        elif line_type == 'landline':
            return {
                'classification': 'unknown',
                'confidence': 50,
                'reasoning': 'Landline, unclear if business or personal'
            }
        
        return {
            'classification': 'unknown',
            'confidence': 30,
            'reasoning': 'Insufficient data for classification'
        }
    
    def analyze_all_numbers_by_commercial_confidence(self, numverify_data: List[Dict]) -> List[Dict]:
        """
        Analyze all numbers and sort by commercial/spam confidence.
        
        Args:
            numverify_data: All NumVerify results
            
        Returns:
            List of analysis results sorted by commercial confidence (highest first)
        """
        # Filter to only successful lookups
        valid_numbers = [item for item in numverify_data if item.get('lookup_successful', False)]
        
        print(f"📊 Analyzing {len(valid_numbers)} numbers with successful NumVerify lookups...")
        
        # Analyze each number
        results = []
        for i, numverify_item in enumerate(valid_numbers, 1):
            phone = numverify_item['phone_number']
            if i % 50 == 0 or i == 1:  # Progress update every 50 numbers
                print(f"Analyzing {i}/{len(valid_numbers)}: {phone}")
            
            # Extract conversation sample
            conversation_data = self.extract_conversation_sample(phone)
            
            # Apply classification
            classification = self.classify_number(numverify_item, conversation_data)
            
            # Combine all data
            result = {
                'phone_number': phone,
                'carrier': numverify_item.get('carrier', ''),
                'line_type': numverify_item.get('line_type', ''),
                'location': numverify_item.get('location', ''),
                'country_name': numverify_item.get('country_name', ''),
                'conversation_found': conversation_data.get('conversation_found', False),
                'message_count': conversation_data.get('message_count', 0),
                'date_range': conversation_data.get('date_range', ''),
                'first_message': conversation_data.get('first_message', ''),
                'sample_text': conversation_data.get('sample_text', ''),
                'classification': classification['classification'],
                'confidence': classification['confidence'],
                'reasoning': classification['reasoning'],
                'error': conversation_data.get('error', '')
            }
            
            results.append(result)
        
        # Sort by commercial/spam confidence (highest first)
        # Commercial/spam gets positive confidence, personal/unknown gets negative for sorting
        def sort_key(result):
            if result['classification'] == 'commercial':
                return result['confidence']  # Higher is better for commercial
            else:
                return -result['confidence']  # Lower confidence = higher in list for non-commercial
        
        results.sort(key=sort_key, reverse=True)
        
        # Add rank after sorting
        for i, result in enumerate(results, 1):
            result['rank'] = i
        
        return results
    
    def generate_html_table(self, analysis_results: List[Dict], output_file: str):
        """Generate HTML table with analysis results."""
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Phone Number Classification Analysis</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; position: sticky; top: 0; }}
        .commercial {{ background-color: #ffebee; }}
        .personal {{ background-color: #e8f5e8; }}
        .unknown {{ background-color: #fff3e0; }}
        .high-confidence {{ font-weight: bold; }}
        .medium-confidence {{ font-style: italic; }}
        .conversation-text {{ max-width: 800px; white-space: pre-wrap; font-size: 12px; line-height: 1.3; }}
        .phone-number {{ font-weight: bold; min-width: 120px; }}
        .carrier {{ font-size: 11px; color: #666; }}
        .classification {{ font-weight: bold; text-align: center; min-width: 80px; }}
        .confidence {{ text-align: center; min-width: 60px; }}
        .filter-controls {{ margin-bottom: 20px; }}
        .filter-controls select {{ margin-right: 10px; }}
        .stats {{ margin-bottom: 20px; padding: 10px; background-color: #f0f0f0; }}
    </style>
    <script>
        function filterTable() {{
            var classification = document.getElementById('classificationFilter').value;
            var confidence = document.getElementById('confidenceFilter').value;
            var table = document.getElementById('analysisTable');
            var rows = table.getElementsByTagName('tr');
            
            for (var i = 1; i < rows.length; i++) {{
                var row = rows[i];
                var classificationCell = row.cells[3];
                var confidenceCell = row.cells[4];
                
                var showRow = true;
                
                if (classification !== 'all' && classificationCell.textContent !== classification) {{
                    showRow = false;
                }}
                
                if (confidence !== 'all') {{
                    var conf = parseInt(confidenceCell.textContent);
                    if (confidence === 'high' && conf < 80) showRow = false;
                    if (confidence === 'medium' && (conf < 60 || conf >= 80)) showRow = false;
                    if (confidence === 'low' && conf >= 60) showRow = false;
                }}
                
                row.style.display = showRow ? '' : 'none';
            }}
        }}
    </script>
</head>
<body>
    <h1>Phone Number Classification Analysis</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="stats">
        <strong>Analysis Summary:</strong><br>
        Total Numbers Analyzed: {len(analysis_results)}<br>
        Commercial: {len([r for r in analysis_results if r['classification'] == 'commercial'])}<br>
        Personal: {len([r for r in analysis_results if r['classification'] == 'personal'])}<br>
        Unknown: {len([r for r in analysis_results if r['classification'] == 'unknown'])}<br>
        High Confidence (80%+): {len([r for r in analysis_results if r['confidence'] >= 80])}
    </div>
    
    <div class="filter-controls">
        <label>Filter by Classification:</label>
        <select id="classificationFilter" onchange="filterTable()">
            <option value="all">All</option>
            <option value="commercial">Commercial</option>
            <option value="personal">Personal</option>
            <option value="unknown">Unknown</option>
        </select>
        
        <label>Filter by Confidence:</label>
        <select id="confidenceFilter" onchange="filterTable()">
            <option value="all">All</option>
            <option value="high">High (80%+)</option>
            <option value="medium">Medium (60-79%)</option>
            <option value="low">Low (<60%)</option>
        </select>
    </div>
    
    <table id="analysisTable">
        <thead>
            <tr>
                <th>Phone Number</th>
                <th>Carrier</th>
                <th>Conversation Sample</th>
                <th>Classification</th>
                <th>Confidence</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for result in analysis_results:
            classification_class = result['classification']
            confidence_class = 'high-confidence' if result['confidence'] >= 80 else 'medium-confidence' if result['confidence'] >= 60 else ''
            
            # Get conversation text - prioritize sample_text, fallback to first_message
            conversation_text = result['sample_text'] if result['sample_text'] else result['first_message']
            if not conversation_text:
                conversation_text = f"No conversation found: {result.get('error', 'Unknown error')}"
            
            html_content += f"""
            <tr class="{classification_class} {confidence_class}">
                <td class="phone-number">{result['phone_number']}</td>
                <td class="carrier">{result['carrier'] or 'Unknown'}<br/>{result['line_type']} • {result['location']}</td>
                <td class="conversation-text">{conversation_text}</td>
                <td class="classification">{result['classification']}</td>
                <td class="confidence">{result['confidence']}%</td>
            </tr>
"""
        
        html_content += """
        </tbody>
    </table>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML analysis table generated: {output_file}")

def main():
    """Main function for conversation analysis."""
    print("🔍 Phone Number Conversation Analysis Tool")
    print("=" * 50)
    
    # Load NumVerify data
    numverify_file = "numverify_raw_all_646_data.json"
    if not Path(numverify_file).exists():
        print(f"❌ NumVerify data file not found: {numverify_file}")
        return
    
    analyzer = ConversationAnalyzer()
    print("📊 Loading NumVerify data...")
    numverify_data = analyzer.load_numverify_data(numverify_file)
    
    print(f"✅ Loaded {len(numverify_data)} NumVerify results")
    
    # Analyze all numbers sorted by commercial confidence
    print("🔍 Analyzing all numbers sorted by commercial/spam confidence...")
    analysis_results = analyzer.analyze_all_numbers_by_commercial_confidence(numverify_data)
    
    # Generate HTML table
    output_file = "phone_number_classification_analysis.html"
    analyzer.generate_html_table(analysis_results, output_file)
    
    print(f"\n🎯 ANALYSIS COMPLETE!")
    print(f"📊 Analyzed {len(analysis_results)} numbers")
    print(f"📁 HTML table: {output_file}")
    print(f"🔍 Open in browser to review classifications")

if __name__ == "__main__":
    main()
