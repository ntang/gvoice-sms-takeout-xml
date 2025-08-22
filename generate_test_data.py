#!/usr/bin/env python3
"""Generate comprehensive test data for Google Voice SMS converter testing."""

import os
from pathlib import Path
from datetime import datetime, timedelta
import random

def generate_test_files():
    """Generate a large number of test files with various patterns."""
    
    # Create test directories
    test_dir = Path("test_data")
    calls_dir = test_dir / "Calls"
    calls_dir.mkdir(parents=True, exist_ok=True)
    
    # Base data for generating files
    names = [
        "John Doe", "Jane Smith", "Bob Wilson", "Alice Johnson", "Charlie Brown",
        "Diana Prince", "Edward Norton", "Fiona Apple", "George Washington", "Helen Keller",
        "Isaac Newton", "Julia Roberts", "Kevin Bacon", "Lisa Simpson", "Michael Jordan",
        "Nancy Drew", "Oliver Twist", "Patricia Highsmith", "Quentin Tarantino", "Rachel Green"
    ]
    
    phone_numbers = [
        "+15551234567", "+15559876543", "+15551112222", "+15554443333", "+15550000000",
        "+15559998888", "+15557776666", "+15556665555", "+15554443333", "+15552221111"
    ]
    
    # Generate 1000+ test files
    base_date = datetime(2024, 1, 1)
    file_count = 0
    
    print("Generating test files...")
    
    # Generate SMS files
    for i in range(300):
        name = random.choice(names)
        phone = random.choice(phone_numbers)
        date = base_date + timedelta(days=i, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        date_str = date.strftime("%Y-%m-%dT%H_%M_%SZ")
        
        filename = f"{name} - Text - {date_str}.html"
        filepath = calls_dir / filename
        
        # Generate random messages
        messages = [
            "Hello there!", "How are you?", "Nice to meet you!", "What's up?",
            "Thanks for the message!", "See you later!", "Have a great day!",
            "Looking forward to it!", "That sounds good!", "Let me know!"
        ]
        
        content = f"""<!DOCTYPE html>
<html>
<head>
    <title>SMS Conversation {i+1}</title>
</head>
<body>
    <div class="conversation">
        <div class="message">
            <abbr class="dt" title="{date.isoformat()}Z">{date.strftime('%b %d')}</abbr>
            <cite><a href="tel:{phone}">{name}</a></cite>
            <q>{random.choice(messages)}</q>
        </div>
        <div class="message">
            <abbr class="dt" title="{(date + timedelta(minutes=1)).isoformat()}Z">{(date + timedelta(minutes=1)).strftime('%b %d')}</abbr>
            <cite>Me</cite>
            <q>Response message {i+1}</q>
        </div>
    </div>
</body>
</html>"""
        
        filepath.write_text(content)
        file_count += 1
        
        if file_count % 100 == 0:
            print(f"Generated {file_count} files...")
    
    # Generate call files
    for i in range(200):
        name = random.choice(names)
        phone = random.choice(phone_numbers)
        call_type = random.choice(["Placed", "Received", "Missed"])
        date = base_date + timedelta(days=i, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        date_str = date.strftime("%Y-%m-%dT%H_%M_%SZ")
        
        filename = f"{name} - {call_type} - {date_str}.html"
        filepath = calls_dir / filename
        
        duration = random.randint(10, 300)  # 10 seconds to 5 minutes
        
        content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{call_type} Call</title>
</head>
<body>
    <div class="call">
        <abbr class="dt" title="{date.isoformat()}Z">{date.strftime('%b %d')}</abbr>
        <a class="tel" href="tel:{phone}">{name}</a>
        <abbr class="duration" title="PT{duration}S">({duration//60}:{duration%60:02d})</abbr>
    </div>
</body>
</html>"""
        
        filepath.write_text(content)
        file_count += 1
    
    # Generate voicemail files
    for i in range(150):
        name = random.choice(names)
        phone = random.choice(phone_numbers)
        date = base_date + timedelta(days=i, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        date_str = date.strftime("%Y-%m-%dT%H_%M_%SZ")
        
        filename = f"{name} - Voicemail - {date_str}.html"
        filepath = calls_dir / filename
        
        duration = random.randint(15, 120)  # 15 seconds to 2 minutes
        
        content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Voicemail</title>
</head>
<body>
    <div class="voicemail">
        <abbr class="dt" title="{date.isoformat()}Z">{date.strftime('%b %d')}</abbr>
        <a class="tel" href="tel:{phone}">{name}</a>
        <div class="message">Voicemail message {i+1} - please call back when convenient.</div>
        <abbr class="duration" title="PT{duration}S">({duration//60}:{duration%60:02d})</abbr>
    </div>
</body>
</html>"""
        
        filepath.write_text(content)
        file_count += 1
    
    # Generate some legitimate Google Voice export files with file parts
    for i in range(50):
        name = random.choice(names)
        phone = random.choice(phone_numbers)
        date = base_date + timedelta(days=i, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        date_str = date.strftime("%Y-%m-%dT%H_%M_%SZ")
        part1 = random.randint(1, 9)
        part2 = random.randint(1, 9)
        
        filename = f"{name} - Text - {date_str}-{part1}-{part2}.html"
        filepath = calls_dir / filename
        
        content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Legitimate Export with File Parts</title>
</head>
<body>
    <div class="conversation">
        <div class="message">
            <abbr class="dt" title="{date.isoformat()}Z">{date.strftime('%b %d')}</abbr>
            <cite><a href="tel:{phone}">{name}</a></cite>
            <q>This is a legitimate Google Voice export with file parts -{part1}-{part2}.</q>
        </div>
    </div>
</body>
</html>"""
        
        filepath.write_text(content)
        file_count += 1
    
    # Generate some corrupted files to test error handling
    corrupted_patterns = [
        (" - Voicemail - 2024-01-25T12_00_00Z.html", "Empty name part"),
        ("Invalid Name - Text - 2024-01-26T13_00_00Z-extra-stuff.html", "Extra parts"),
        ("Missing Extension - Text - 2024-01-27T14_00_00Z", "Missing .html"),
        ("Special@Chars - Text - 2024-01-28T15_00_00Z.html", "Special characters"),
        ("Very Long Name With Many Words And Spaces That Exceeds Normal Limits - Text - 2024-01-29T16_00_00Z.html", "Very long name")
    ]
    
    for filename, description in corrupted_patterns:
        filepath = calls_dir / filename
        
        content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Corrupted File - {description}</title>
</head>
<body>
    <div class="corrupted">
        <abbr class="dt" title="2024-01-25T12:00:00Z">Jan 25</abbr>
        <div class="message">This file has corruption: {description}</div>
    </div>
</body>
</html>"""
        
        filepath.write_text(content)
        file_count += 1
    
    print(f"Generated {file_count} test files in {calls_dir}")
    return file_count

if __name__ == "__main__":
    generate_test_files()
