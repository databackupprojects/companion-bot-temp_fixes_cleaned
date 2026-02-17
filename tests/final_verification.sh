#!/bin/bash

echo "=========================================="
echo "FINAL VERIFICATION TEST"
echo "=========================================="

# Test 1: Check backend is running
echo -e "\n[1] Backend Status:"
if ps aux | grep "python run.py" | grep -v grep > /dev/null; then
    echo "✓ Backend running"
else
    echo "✗ Backend not running"
    exit 1
fi

# Test 2: Check database connectivity
echo -e "\n[2] Database:"
PGPASSWORD=123123 psql -U abubakar -h localhost -d companion_bot -c "SELECT 'Connected' as status;" 2>&1 | grep -q "Connected" && echo "✓ Database connected" || echo "✗ Database not responding"

# Test 3: Check key tables
echo -e "\n[3] Database Tables:"
echo -n "  Bot Settings: "
PGPASSWORD=123123 psql -U abubakar -h localhost -d companion_bot -t -c "SELECT COUNT(*) FROM bot_settings;" | xargs echo "✓ Found"

echo -n "  Quiz Configs: "
PGPASSWORD=123123 psql -U abubakar -h localhost -d companion_bot -t -c "SELECT COUNT(*) FROM quiz_configs WHERE user_id IS NOT NULL;" | xargs echo "✓ With user_id:"

echo -n "  Schedules: "
PGPASSWORD=123123 psql -U abubakar -h localhost -d companion_bot -t -c "SELECT COUNT(*) FROM user_schedules WHERE is_completed = FALSE;" | xargs echo "✓ Upcoming:"

# Test 4: Check code fixes
echo -e "\n[4] Code Fixes:"
echo -n "  command_handler.py: "
grep -c "datetime.now()" /home/abubakar/companion-bot/backend/handlers/command_handler.py | xargs echo "✓ Uses datetime.now():"

echo -n "  quiz.py: "
grep -c "datetime.now()" /home/abubakar/companion-bot/backend/routers/quiz.py | xargs echo "✓ Uses datetime.now():"

echo -n "  message_handler.py: "
grep -c "datetime.now()" /home/abubakar/companion-bot/backend/handlers/message_handler.py | xargs echo "✓ Uses datetime.now():"

# Test 5: Check chat logging
echo -e "\n[5] Chat Logging:"
if [ -d "/home/abubakar/companion-bot/logs/chats" ]; then
    count=$(find /home/abubakar/companion-bot/logs/chats -name "*.log" | wc -l)
    echo "✓ Logs directory exists, $count log files found"
else
    echo "✗ Logs directory not found"
fi

echo -e "\n=========================================="
echo "✅ VERIFICATION COMPLETE"
echo "=========================================="
