-- migrations.sql
-- Version: 3.1 MVP
-- Database migrations for AI Companion Bot
-- Run these in order on a fresh database

-- =============================================
-- CORE TABLES
-- =============================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    name VARCHAR(100),
    
    -- Subscription
    tier VARCHAR(20) DEFAULT 'free',
    tier_expires_at TIMESTAMP,
    
    -- Limits
    messages_today INTEGER DEFAULT 0,
    proactive_count_today INTEGER DEFAULT 0,
    
    -- Activity
    last_active_at TIMESTAMP,
    is_active_today BOOLEAN DEFAULT FALSE,
    
    -- Timezone
    timezone VARCHAR(50) DEFAULT 'UTC',
    
    -- Safety consent
    spice_consent BOOLEAN DEFAULT FALSE,
    spice_consent_at TIMESTAMP,
    
    -- Reset tracking
    last_daily_reset DATE,
    
    -- Soft delete
    deleted_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Bot settings table
CREATE TABLE IF NOT EXISTS bot_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    
    -- Core variables (always queried)
    bot_name VARCHAR(50) DEFAULT 'Dot',
    bot_gender VARCHAR(20) DEFAULT 'female',
    archetype VARCHAR(50) DEFAULT 'golden_retriever',
    attachment_style VARCHAR(20) DEFAULT 'secure',
    flirtiness VARCHAR(20) DEFAULT 'subtle',
    toxicity VARCHAR(20) DEFAULT 'healthy' 
        CHECK (toxicity IN ('healthy', 'mild', 'toxic_light')),
    tone_summary TEXT,
    
    -- Advanced variables (JSONB)
    advanced_settings JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'reactive',
    
    -- Question tracking
    is_question BOOLEAN DEFAULT FALSE,
    question_topic VARCHAR(200),
    question_answered BOOLEAN DEFAULT FALSE,
    
    -- Mood
    detected_mood VARCHAR(20),
    
    -- Memory
    summarized BOOLEAN DEFAULT FALSE,
    
    -- Soft delete
    deleted_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- User boundaries table
CREATE TABLE IF NOT EXISTS user_boundaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    boundary_type VARCHAR(20) NOT NULL,
    boundary_value VARCHAR(200) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    
    -- 24-hour hard stop tracking
    user_initiated_after TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Mood history table
CREATE TABLE IF NOT EXISTS mood_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    mood VARCHAR(20) NOT NULL,
    detected_at TIMESTAMP DEFAULT NOW()
);

-- User memory table
CREATE TABLE IF NOT EXISTS user_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(50),
    fact TEXT NOT NULL,
    importance INTEGER DEFAULT 1 CHECK (importance BETWEEN 1 AND 5),
    source_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id, fact)
);

-- Proactive log table
CREATE TABLE IF NOT EXISTS proactive_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    message_content TEXT,
    message_category VARCHAR(50),
    sent_at TIMESTAMP DEFAULT NOW()
);

-- Quiz configs table
CREATE TABLE IF NOT EXISTS quiz_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token VARCHAR(32) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,  -- Track which user created
    config_data JSONB NOT NULL,
    tone_summary TEXT,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Support requests table
CREATE TABLE IF NOT EXISTS support_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    context TEXT,
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Analytics events table
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    event_name VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- INDEXES (Critical for performance)
-- =============================================

-- Users
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);
CREATE INDEX IF NOT EXISTS idx_users_timezone ON users(timezone);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active_at DESC) WHERE deleted_at IS NULL;

-- Messages
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_created ON messages(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_unsummarized ON messages(user_id, summarized) WHERE summarized = FALSE AND deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_messages_questions ON messages(user_id, is_question, question_answered) WHERE is_question = TRUE;

-- Boundaries
CREATE INDEX IF NOT EXISTS idx_boundaries_user_active ON user_boundaries(user_id, active) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_boundaries_type ON user_boundaries(boundary_type) WHERE active = TRUE;

-- Mood history
CREATE INDEX IF NOT EXISTS idx_mood_user_time ON mood_history(user_id, detected_at DESC);

-- User memory
CREATE INDEX IF NOT EXISTS idx_memory_user_importance ON user_memory(user_id, importance DESC);
CREATE INDEX IF NOT EXISTS idx_memory_category ON user_memory(category);

-- Proactive log
CREATE INDEX IF NOT EXISTS idx_proactive_user_time ON proactive_log(user_id, sent_at DESC);

-- Quiz configs
CREATE INDEX IF NOT EXISTS idx_quiz_token ON quiz_configs(token) WHERE used_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_quiz_expires ON quiz_configs(expires_at) WHERE used_at IS NULL;

-- Analytics
CREATE INDEX IF NOT EXISTS idx_analytics_event_time ON analytics_events(event_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_user ON analytics_events(user_id, created_at DESC);

-- JSONB indexes for common queries
CREATE INDEX IF NOT EXISTS idx_bot_settings_archetype ON bot_settings(archetype);
CREATE INDEX IF NOT EXISTS idx_bot_settings_attachment ON bot_settings(attachment_style);

-- =============================================
-- FUNCTIONS
-- =============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_bot_settings_updated_at ON bot_settings;
CREATE TRIGGER update_bot_settings_updated_at
    BEFORE UPDATE ON bot_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- CLEANUP JOBS (run via cron)
-- =============================================

-- Delete old analytics (90 days)
-- DELETE FROM analytics_events WHERE created_at < NOW() - INTERVAL '90 days';

-- Delete old mood history (30 days)
-- DELETE FROM mood_history WHERE detected_at < NOW() - INTERVAL '30 days';

-- Delete expired quiz configs (7 days past expiry)
-- DELETE FROM quiz_configs WHERE expires_at < NOW() - INTERVAL '7 days';

-- Delete old proactive logs (30 days)
-- DELETE FROM proactive_log WHERE sent_at < NOW() - INTERVAL '30 days';

-- =============================================
-- SAMPLE DATA FOR TESTING
-- =============================================

-- Uncomment to add test user
/*
INSERT INTO users (telegram_id, name, timezone) 
VALUES (123456789, 'TestUser', 'America/New_York');

INSERT INTO bot_settings (user_id, bot_name, archetype, tone_summary)
SELECT id, 'Sunny', 'golden_retriever', 'your biggest fan who gets excited about literally everything you do'
FROM users WHERE telegram_id = 123456789;
*/
