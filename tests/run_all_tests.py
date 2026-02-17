#!/usr/bin/env python3
"""
Quick test runner for all /schedule command and chat logging tests.
Runs all test files in sequence with clear reporting.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


TEST_FILES = [
    "test_telegram_commands.py",
    "test_integration_schedule_logging.py",
    "test_schedule_command_unit.py",
    "test_e2e_schedule_logging.py",
]


def run_test(test_file):
    """Run a single test file and return results."""
    test_path = Path(__file__).parent / test_file
    
    print(f"\n{'='*80}")
    print(f"Running: {test_file}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=False,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"❌ Test timeout: {test_file}")
        return False
    except Exception as e:
        print(f"❌ Error running {test_file}: {e}")
        return False


def main():
    """Run all tests and report results."""
    print("\n" + "="*80)
    print("TELEGRAM /schedule COMMAND AND CHAT LOGGING TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    results = {}
    for test_file in TEST_FILES:
        results[test_file] = run_test(test_file)
    
    # Summary
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_file, passed_test in results.items():
        status = "✅ PASSED" if passed_test else "❌ FAILED"
        print(f"{status}: {test_file}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
