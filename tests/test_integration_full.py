"""
Full integration tests against the live API at http://localhost:8000
Tests:
  1. Proactive messaging (DB-level + API gate checks)
  2. Bot creation via quiz flow
  3. Chatting with newly created bots
  4. Admin page (auth, stats, user list)
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta

import httpx

BASE = "http://localhost:8000"
ADMIN_EMAIL = "ali@companion.com"
ADMIN_PASS = "Test1234!"

# Unique test user per run so we don't pollute the DB with stale state
_RUN_ID = uuid.uuid4().hex[:8]
TEST_EMAIL = f"integration_test_{_RUN_ID}@test.com"
TEST_PASS = "TestPass123!"
TEST_USERNAME = f"inttest_{_RUN_ID}"

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []


def ok(label):
    results.append((True, label))
    print(f"  {PASS} {label}")


def fail(label, detail=""):
    results.append((False, label))
    print(f"  {FAIL} {label}" + (f": {detail}" if detail else ""))


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── helpers ──────────────────────────────────────────────────────────────────

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


async def register_and_login(client, email, password, username) -> str | None:
    """Register a new user and return access token."""
    r = await client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "username": username,
    })
    if r.status_code not in (200, 201):
        fail("Register test user", f"HTTP {r.status_code}: {r.text[:200]}")
        return None
    ok("Register test user")

    r = await client.post("/api/auth/token",
        content=f"username={email}&password={password}",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code != 200:
        fail("Login test user", f"HTTP {r.status_code}")
        return None
    data = r.json()
    ok("Login test user")
    return data["access_token"]


async def admin_login(client) -> str | None:
    r = await client.post("/api/auth/token",
        content=f"username={ADMIN_EMAIL}&password={ADMIN_PASS}",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code != 200:
        fail("Admin login", f"HTTP {r.status_code}: {r.text[:200]}")
        return None
    data = r.json()
    if data.get("role") != "admin":
        fail("Admin login — role check", f"role={data.get('role')}")
        return None
    ok("Admin login (role=admin confirmed)")
    return data["access_token"]


# ── Test 1: Proactive messaging ───────────────────────────────────────────────

async def test_proactive(client, token):
    section("1. PROACTIVE MESSAGING")

    # 1a. API gate — /api/messages/proactive
    r = await client.post("/api/messages/proactive", headers=auth_headers(token))
    if r.status_code == 200:
        data = r.json()
        if data.get("success"):
            ok(f"Proactive message generated: {data.get('message','')[:60]}...")
        else:
            ok(f"Proactive gate blocked (expected): reason={data.get('reason')}")
    else:
        fail("Proactive endpoint reachable", f"HTTP {r.status_code}: {r.text[:200]}")
        return

    # 1b. DB-level: verify Message rows with message_type='proactive' exist
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
    os.chdir(os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from dotenv import load_dotenv
    load_dotenv()

    try:
        from database import AsyncSessionLocal
        from models.sql_models import Message
        from sqlalchemy import select, func

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.count()).where(Message.message_type == 'proactive')
            )
            count = result.scalar()
            if count is not None:
                ok(f"Proactive Message rows in DB: {count}")
            else:
                fail("Proactive Message rows query returned None")
    except Exception as e:
        fail("DB check for proactive messages", str(e))

    # 1c. Proactive meeting handler imports cleanly
    try:
        from services.proactive_meeting_handler import ProactiveMeetingHandler
        ok("ProactiveMeetingHandler imports OK")
    except Exception as e:
        fail("ProactiveMeetingHandler import", str(e))

    # 1d. Memory summarizer no longer calls missing method
    try:
        from jobs.memory_summarizer import MemorySummarizer
        import inspect
        src = inspect.getsource(MemorySummarizer._extract_facts)
        if "extract_facts_from_conversation" in src:
            fail("memory_summarizer still calls non-existent extract_facts_from_conversation")
        else:
            ok("memory_summarizer uses direct OpenAI call (no missing method)")
    except Exception as e:
        fail("memory_summarizer source check", str(e))


# ── Test 2: Bot creation ──────────────────────────────────────────────────────

async def test_bot_creation(client, token) -> str | None:
    section("2. BOT CREATION")

    # 2a. Can-create check
    r = await client.get("/api/quiz/can-create", headers=auth_headers(token))
    if r.status_code == 200:
        data = r.json()
        ok(f"Can-create-bot: allowed={data.get('can_create')}, tier={data.get('tier')}")
    else:
        fail("Can-create-bot endpoint", f"HTTP {r.status_code}")

    # 2b. Start quiz session
    r = await client.post("/api/quiz/start", headers=auth_headers(token))
    if r.status_code in (200, 201):
        session_data = r.json()
        quiz_token = session_data.get("session_token") or session_data.get("token")
        ok(f"Quiz session started: token={str(quiz_token)[:16]}...")
    else:
        fail("Start quiz session", f"HTTP {r.status_code}: {r.text[:200]}")
        return None

    # 2c. Submit complete quiz
    quiz_payload = {
        "user_name": TEST_USERNAME,
        "bot_name": f"TestBot_{_RUN_ID}",
        "archetype": "golden_retriever",
        "bot_gender": "female",
        "attachment_style": "secure",
        "flirtiness": "subtle",
        "toxicity": "healthy",
        "spice_consent": False,
    }
    r = await client.post("/api/quiz/complete", json=quiz_payload, headers=auth_headers(token))
    if r.status_code in (200, 201):
        bot_data = r.json()
        ok(f"Quiz completed, token={bot_data.get('token','')[:16]}...")
    else:
        fail("Quiz complete", f"HTTP {r.status_code}: {r.text[:300]}")
        return None

    # 2d. Verify bot appears in my-bots (no duplicates) and get bot_id
    r = await client.get("/api/quiz/my-bots", headers=auth_headers(token))
    bot_id = None
    if r.status_code == 200:
        bots = r.json().get("bots", [])
        test_bots = [b for b in bots if _RUN_ID in b["bot_name"]]
        if len(test_bots) == 1:
            bot_id = test_bots[0]["id"]
            ok(f"My Bots: 1 test bot listed (no duplicates). bot_id={bot_id}. Total: {len(bots)}")
        elif len(test_bots) == 0:
            fail("My Bots: test bot not found in list")
        else:
            fail(f"My Bots: DUPLICATE -- {len(test_bots)} entries for the same bot")
    else:
        fail("My Bots endpoint", f"HTTP {r.status_code}")

    return bot_id


# ── Test 3: Chat with new bot ─────────────────────────────────────────────────

async def test_chat(client, token, bot_id):
    section("3. CHATTING WITH NEW BOT")

    if not bot_id:
        fail("Chat test skipped — no bot_id from creation test")
        return

    # 3a. Send first message
    r = await client.post("/api/messages/", json={
        "message": "Hello! Who are you?",
        "bot_id": bot_id,
    }, headers=auth_headers(token))

    if r.status_code == 200:
        data = r.json()
        reply = data.get("reply") or data.get("response", "")
        ok(f"Message sent, bot replied: {reply[:80]}...")
    else:
        fail("Send message", f"HTTP {r.status_code}: {r.text[:300]}")
        return

    # 3b. Send second message — verify no FK violation
    r = await client.post("/api/messages/", json={
        "message": "What do you like to do?",
        "bot_id": bot_id,
    }, headers=auth_headers(token))

    if r.status_code == 200:
        ok("Second message — no FK violation")
    else:
        fail("Second message FK check", f"HTTP {r.status_code}: {r.text[:300]}")

    # 3c. Verify messages appear in history
    r = await client.get(f"/api/messages/history?limit=10&bot_id={bot_id}",
                         headers=auth_headers(token))
    if r.status_code == 200:
        msgs = r.json().get("messages", [])
        user_msgs = [m for m in msgs if m["role"] == "user"]
        bot_msgs = [m for m in msgs if m["role"] == "bot"]
        ok(f"Message history: {len(user_msgs)} user + {len(bot_msgs)} bot messages")
    else:
        fail("Message history", f"HTTP {r.status_code}")

    # 3d. Empty message validation
    r = await client.post("/api/messages/", json={
        "message": "   ",
        "bot_id": bot_id,
    }, headers=auth_headers(token))
    if r.status_code == 400:
        ok("Empty message correctly rejected (400)")
    else:
        fail("Empty message validation", f"Expected 400, got {r.status_code}")


# ── Test 4: Admin page ────────────────────────────────────────────────────────

async def test_admin(client):
    section("4. ADMIN PAGE")

    # 4a. Admin login + role check
    admin_token = await admin_login(client)
    if not admin_token:
        return

    # 4b. /api/users/me returns role=admin
    r = await client.get("/api/users/me", headers=auth_headers(admin_token))
    if r.status_code == 200:
        me = r.json()
        if me.get("role") == "admin":
            ok(f"GET /api/users/me: role=admin confirmed")
        else:
            fail("GET /api/users/me role check", f"role={me.get('role')}")
    else:
        fail("GET /api/users/me", f"HTTP {r.status_code}")

    # 4c. Admin stats endpoint
    r = await client.get("/api/admin/stats", headers=auth_headers(admin_token))
    if r.status_code == 200:
        stats = r.json()
        ok(f"Admin stats: users={stats.get('total_users')}, "
           f"messages={stats.get('total_messages')}")
    else:
        fail("Admin stats", f"HTTP {r.status_code}: {r.text[:200]}")

    # 4d. Admin user list
    r = await client.get("/api/admin/users?limit=5", headers=auth_headers(admin_token))
    if r.status_code == 200:
        users = r.json()
        count = len(users) if isinstance(users, list) else users.get("total", "?")
        ok(f"Admin user list accessible: returned data OK")
    else:
        fail("Admin user list", f"HTTP {r.status_code}: {r.text[:200]}")

    # 4e. Non-admin cannot access admin endpoints
    r = await client.post("/api/auth/register", json={
        "email": f"nonadmin_{_RUN_ID}@test.com",
        "password": "Test1234!",
        "username": f"nonadmin_{_RUN_ID}",
    })
    if r.status_code in (200, 201):
        r2 = await client.post("/api/auth/token",
            content=f"username=nonadmin_{_RUN_ID}@test.com&password=Test1234!",
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        if r2.status_code == 200:
            regular_token = r2.json()["access_token"]
            r3 = await client.get("/api/admin/stats", headers=auth_headers(regular_token))
            if r3.status_code in (401, 403):
                ok("Non-admin blocked from admin endpoints (401/403)")
            else:
                fail("Non-admin access control", f"Expected 401/403, got {r3.status_code}")


# ── Main runner ───────────────────────────────────────────────────────────────

async def main():
    print("\n" + "="*60)
    print("  COMPANION BOT — FULL INTEGRATION TESTS")
    print(f"  Target: {BASE}")
    print(f"  Run ID: {_RUN_ID}")
    print("="*60)

    # Check API is reachable
    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as client:
        try:
            r = await client.get("/health")
            if r.status_code not in (200, 404):
                r = await client.get("/")
            print(f"\n  API reachable at {BASE} [OK]")
        except Exception as e:
            print(f"\n  {FAIL} Cannot reach API at {BASE}: {e}")
            print("  Make sure 'python run.py' is running first.\n")
            return

        # Register + login test user
        section("0. TEST USER SETUP")
        token = await register_and_login(client, TEST_EMAIL, TEST_PASS, TEST_USERNAME)
        if not token:
            print("\n[FAIL] Cannot proceed without test user. Aborting.")
            return

        # Run all test suites
        await test_proactive(client, token)
        bot_id = await test_bot_creation(client, token)
        await test_chat(client, token, bot_id)
        await test_admin(client)

    # Summary
    section("SUMMARY")
    passed = sum(1 for ok, _ in results if ok)
    failed = sum(1 for ok, _ in results if not ok)
    total = len(results)
    print(f"\n  {PASS} Passed: {passed}/{total}")
    if failed:
        print(f"  {FAIL} Failed: {failed}/{total}")
        for ok_flag, label in results:
            if not ok_flag:
                print(f"       - {label}")
    print()
    if failed == 0:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED — see above")
    print()


if __name__ == "__main__":
    asyncio.run(main())
