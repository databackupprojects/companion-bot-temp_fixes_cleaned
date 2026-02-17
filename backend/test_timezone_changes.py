# backend/test_timezone_changes.py
"""
Quick test to verify timezone changes are working correctly
"""
from datetime import datetime
from utils.timezone import (
    get_utc_now, 
    to_user_timezone, 
    to_utc, 
    format_for_user,
    get_user_current_time
)
import pytz

def test_timezone_conversions():
    """Test all timezone conversion functions."""
    
    print("=" * 60)
    print("Testing Timezone Conversion Functions")
    print("=" * 60)
    
    # Test 1: Get UTC now
    utc_now = get_utc_now()
    print(f"\n1. UTC Now (naive): {utc_now}")
    print(f"   Type: {type(utc_now)}, Timezone: {utc_now.tzinfo}")
    
    # Test 2: Convert UTC to different timezones
    test_timezones = ['America/New_York', 'Europe/London', 'Asia/Tokyo', 'Australia/Sydney']
    
    for tz in test_timezones:
        user_time = to_user_timezone(utc_now, tz)
        print(f"\n2. UTC to {tz}:")
        print(f"   {user_time}")
        print(f"   Timezone: {user_time.tzinfo}")
    
    # Test 3: Format for display
    ny_time = format_for_user(utc_now, 'America/New_York')
    london_time = format_for_user(utc_now, 'Europe/London')
    tokyo_time = format_for_user(utc_now, 'Asia/Tokyo')
    
    print(f"\n3. Formatted for Display:")
    print(f"   New York: {ny_time}")
    print(f"   London:   {london_time}")
    print(f"   Tokyo:    {tokyo_time}")
    
    # Test 4: Round-trip conversion
    print(f"\n4. Round-trip conversion test:")
    
    # Start with UTC
    original_utc = get_utc_now()
    print(f"   Original UTC: {original_utc}")
    
    # Convert to user timezone and back
    user_tz = 'America/New_York'
    user_local = to_user_timezone(original_utc, user_tz)
    print(f"   Convert to {user_tz}: {user_local}")
    
    back_to_utc = to_utc(user_local, user_tz)
    print(f"   Convert back to UTC: {back_to_utc}")
    
    # Check if they match (allowing for microsecond precision)
    difference = abs((original_utc - back_to_utc).total_seconds())
    print(f"   Difference: {difference:.2f} seconds")
    print(f"   ✓ Round-trip successful!" if difference < 1 else "   ✗ Round-trip failed!")
    
    # Test 5: User current time
    print(f"\n5. User Current Time:")
    for tz in test_timezones:
        current = get_user_current_time(tz)
        print(f"   {tz}: {current}")
    
    print("\n" + "=" * 60)
    print("All timezone conversion tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_timezone_conversions()
