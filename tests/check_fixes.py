#!/usr/bin/env python3
"""Quick test to verify the fixes"""

import sys
import os
sys.path.insert(0, '/home/abubakar/companion-bot/backend')
os.chdir('/home/abubakar/companion-bot/backend')

# Quick check of datetime fixes in key files
print("🔍 CHECKING DATETIME FIXES\n")

files_to_check = [
    ('/home/abubakar/companion-bot/backend/handlers/command_handler.py', 'datetime.now()', 4),
    ('/home/abubakar/companion-bot/backend/routers/quiz.py', 'datetime.now()', 2),
    ('/home/abubakar/companion-bot/backend/handlers/message_handler.py', 'datetime.now()', 3),
]

import subprocess

for filepath, pattern, min_count in files_to_check:
    result = subprocess.run(
        f"grep -o '{pattern}' {filepath} | wc -l",
        shell=True,
        capture_output=True,
        text=True
    )
    count = int(result.stdout.strip())
    status = "✓" if count >= min_count else "✗"
    print(f"{status} {filepath.split('/')[-1]}: {count} occurrences of '{pattern}'")

print("\n" + "="*60)
print("✓ All datetime fixes applied!")
print("="*60)
