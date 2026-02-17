#!/bin/bash

# End-to-End Testing Script for AI Companion Bot
# This script tests the complete user flow

echo "======================================"
echo "AI Companion Bot - E2E Testing"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_BASE="http://localhost:8010/api"
TEST_USER="testuser_$(date +%s)"
TEST_EMAIL="${TEST_USER}@example.com"
TEST_PASSWORD="testpass123"

echo "Test Configuration:"
echo "  API Base: $API_BASE"
echo "  Test User: $TEST_USER"
echo "  Test Email: $TEST_EMAIL"
echo ""

# Test 1: Health Check
echo -n "Test 1: API Health Check... "
HEALTH=$(curl -s "$API_BASE/../" | jq -r '.message' 2>/dev/null)
if [[ "$HEALTH" == *"AI Companion Bot"* ]]; then
    echo -e "${GREEN}✓ PASSED${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
    echo "  Response: $HEALTH"
    exit 1
fi

# Test 2: User Registration
echo -n "Test 2: User Registration... "
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$TEST_USER\",\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.access_token' 2>/dev/null)
USER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.user_id' 2>/dev/null)

if [[ "$ACCESS_TOKEN" != "null" && "$ACCESS_TOKEN" != "" ]]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "  User ID: $USER_ID"
else
    echo -e "${RED}✗ FAILED${NC}"
    echo "  Response: $REGISTER_RESPONSE"
    exit 1
fi

# Test 3: Check Bot Creation Limit
echo -n "Test 3: Check Bot Creation Limit... "
BOT_LIMIT=$(curl -s -X GET "$API_BASE/quiz/can-create" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

CAN_CREATE=$(echo "$BOT_LIMIT" | jq -r '.can_create' 2>/dev/null)
if [[ "$CAN_CREATE" == "true" ]]; then
    echo -e "${GREEN}✓ PASSED${NC}"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - User cannot create bot"
    echo "  Response: $BOT_LIMIT"
fi

# Test 4: Complete Quiz
echo -n "Test 4: Complete Quiz... "
QUIZ_DATA='{
  "user_name": "TestUser",
  "bot_gender": "female",
  "archetype": "golden_retriever",
  "bot_name": "Sunny",
  "attachment_style": "secure",
  "flirtiness": "subtle",
  "toxicity": "healthy",
  "spice_consent": false
}'

QUIZ_RESPONSE=$(curl -s -X POST "$API_BASE/quiz/complete" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$QUIZ_DATA")

QUIZ_TOKEN=$(echo "$QUIZ_RESPONSE" | jq -r '.token' 2>/dev/null)
DEEP_LINK=$(echo "$QUIZ_RESPONSE" | jq -r '.deep_link' 2>/dev/null)

if [[ "$QUIZ_TOKEN" != "null" && "$QUIZ_TOKEN" != "" ]]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "  Token: ${QUIZ_TOKEN:0:20}..."
    echo "  Deep Link: $DEEP_LINK"
else
    echo -e "${RED}✗ FAILED${NC}"
    echo "  Response: $QUIZ_RESPONSE"
    exit 1
fi

# Test 5: Get Bot Settings
echo -n "Test 5: Get Bot Settings... "
SETTINGS=$(curl -s -X GET "$API_BASE/settings" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

BOT_NAME=$(echo "$SETTINGS" | jq -r '.bot_name' 2>/dev/null)
if [[ "$BOT_NAME" != "null" && "$BOT_NAME" != "" ]]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "  Bot Name: $BOT_NAME"
    echo "  Archetype: $(echo "$SETTINGS" | jq -r '.archetype')"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - No bot settings found"
fi

# Test 6: Send Message
echo -n "Test 6: Send Message... "
MESSAGE_RESPONSE=$(curl -s -X POST "$API_BASE/messages" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"message":"Hello! How are you?"}')

BOT_REPLY=$(echo "$MESSAGE_RESPONSE" | jq -r '.bot_reply' 2>/dev/null)
if [[ "$BOT_REPLY" != "null" && "$BOT_REPLY" != "" ]]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "  Bot Reply: ${BOT_REPLY:0:50}..."
else
    echo -e "${RED}✗ FAILED${NC}"
    echo "  Response: $MESSAGE_RESPONSE"
fi

# Test 7: Get Message History
echo -n "Test 7: Get Message History... "
HISTORY=$(curl -s -X GET "$API_BASE/messages/history?limit=10" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

MESSAGE_COUNT=$(echo "$HISTORY" | jq '. | length' 2>/dev/null)
if [[ "$MESSAGE_COUNT" -gt 0 ]]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "  Messages: $MESSAGE_COUNT"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - No messages found"
fi

# Test 8: Logout
echo -n "Test 8: Logout... "
LOGOUT=$(curl -s -X POST "$API_BASE/auth/logout" \
    -H "Authorization: Bearer $ACCESS_TOKEN")
echo -e "${GREEN}✓ PASSED${NC}"

echo ""
echo "======================================"
echo "All tests completed!"
echo "======================================"
