-- Migration v3.5: Add tier settings table for dynamic bot limits
-- This migration:
-- 1. Creates tier_settings table
-- 2. Initializes default tier configurations
-- 3. Adds unique constraint on archetype per user

-- Create tier_settings table
CREATE TABLE IF NOT EXISTS tier_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier_name VARCHAR(20) UNIQUE NOT NULL,
    max_bots INTEGER NOT NULL DEFAULT 1,
    max_messages_per_day INTEGER NOT NULL DEFAULT 20,
    max_proactive_per_day INTEGER NOT NULL DEFAULT 1,
    features JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tier_settings_name ON tier_settings(tier_name);

-- Insert default tier configurations
INSERT INTO tier_settings (tier_name, max_bots, max_messages_per_day, max_proactive_per_day, features)
VALUES 
    ('free', 1, 20, 1, '{"advanced_settings": false, "analytics": false}'::jsonb),
    ('plus', 3, 100, 3, '{"advanced_settings": true, "analytics": true}'::jsonb),
    ('premium', 5, 1000, 5, '{"advanced_settings": true, "analytics": true, "priority_support": true}'::jsonb)
ON CONFLICT (tier_name) DO NOTHING;

-- Add unique constraint to enforce one bot per archetype per user
-- This ensures users cannot create multiple bots with the same archetype
CREATE UNIQUE INDEX IF NOT EXISTS idx_bot_settings_user_archetype 
ON bot_settings(user_id, archetype) 
WHERE is_active = TRUE;

-- Verify the migration
SELECT 
    tier_name,
    max_bots,
    max_messages_per_day,
    max_proactive_per_day
FROM tier_settings
ORDER BY max_bots ASC;

-- Check for any users with duplicate archetypes (should be none after constraint)
SELECT 
    user_id,
    archetype,
    COUNT(*) as count
FROM bot_settings
WHERE is_active = TRUE
GROUP BY user_id, archetype
HAVING COUNT(*) > 1;
