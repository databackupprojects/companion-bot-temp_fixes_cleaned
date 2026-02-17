-- Migration v3.7: Add proactive features - schedules, sessions, and greeting preferences
-- This migration adds tables and columns to support:
-- 1. User schedules (meetings, events)
-- 2. Proactive session tracking (to prevent repetition)
-- 3. Greeting preferences

-- Table: user_schedules
-- Stores meetings and events mentioned by users with proactive reminder tracking
CREATE TABLE IF NOT EXISTS user_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bot_id UUID REFERENCES bot_settings(id) ON DELETE CASCADE,
    event_name VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMP NOT NULL, -- Time information (stored in UTC)
    end_time TIMESTAMP,
    channel VARCHAR(20) DEFAULT 'web', -- 'web' or 'telegram' 
    
    preparation_reminder_sent BOOLEAN DEFAULT FALSE , 
    preparation_reminder_sent_at TIMESTAMP,
    
    event_completed_sent BOOLEAN DEFAULT FALSE,
    event_completed_sent_at TIMESTAMP,
    
    followup_sent BOOLEAN DEFAULT FALSE,
    followup_sent_at TIMESTAMP,
    
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_channel CHECK (channel IN ('web', 'telegram'))
);

CREATE INDEX idx_schedule_user_start_time ON user_schedules(user_id, start_time);
CREATE INDEX idx_schedule_status ON user_schedules(user_id, is_completed);
CREATE INDEX idx_schedule_start_time ON user_schedules(start_time);

-- Table: proactive_sessions
-- Track proactive interactions to avoid repetition and manage session state
CREATE TABLE IF NOT EXISTS proactive_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bot_id UUID REFERENCES bot_settings(id) ON DELETE CASCADE,
    -- Session tracking
    session_type VARCHAR(50) NOT NULL, -- 'morning_greeting', 'meeting_prep', 'meeting_followup', etc.
    reference_id UUID, -- Links to related entity (e.g., UserSchedule.id)
    -- Message tracking
    message_content TEXT,
    channel VARCHAR(20) DEFAULT 'web', -- 'web' or 'telegram'
    -- Status
    sent_at TIMESTAMP DEFAULT NOW(),
    acknowledged_at TIMESTAMP,
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Constraints
    CONSTRAINT valid_session_channel CHECK (channel IN ('web', 'telegram'))
);

CREATE INDEX idx_proactive_session_user_type ON proactive_sessions(user_id, session_type, sent_at DESC);
CREATE INDEX idx_proactive_session_sent_at ON proactive_sessions(sent_at DESC);

-- Table: greeting_preferences
-- Store user's greeting and communication preferences
CREATE TABLE IF NOT EXISTS greeting_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    -- Greeting preferences
    prefer_proactive BOOLEAN DEFAULT TRUE,
    preferred_greeting_time VARCHAR(20) DEFAULT 'morning', -- 'morning', 'afternoon', 'evening'
    -- Do not disturb settings (24-hour format, 0-23)
    dnd_start_hour INTEGER,
    dnd_end_hour INTEGER,
    -- Frequency preferences
    max_proactive_per_day INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    -- Constraints
    CONSTRAINT valid_greeting_time CHECK (preferred_greeting_time IN ('morning', 'afternoon', 'evening')),
    CONSTRAINT valid_dnd_start CHECK (dnd_start_hour IS NULL OR (dnd_start_hour >= 0 AND dnd_start_hour < 24)),
    CONSTRAINT valid_dnd_end CHECK (dnd_end_hour IS NULL OR (dnd_end_hour >= 0 AND dnd_end_hour < 24))
);

-- Create a trigger to automatically create greeting_preferences when a new user is created
CREATE OR REPLACE FUNCTION create_greeting_preference()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO greeting_preferences(user_id) VALUES(NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_create_greeting_preference
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION create_greeting_preference();

-- If there are existing users, create their greeting preferences
INSERT INTO greeting_preferences(user_id)
SELECT id FROM users WHERE id NOT IN (SELECT user_id FROM greeting_preferences)
ON CONFLICT (user_id) DO NOTHING;

-- Add timezone to users table if it doesn't exist (should already exist from previous migration)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'timezone'
    ) THEN
        ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC';
    END IF;
END
$$;
