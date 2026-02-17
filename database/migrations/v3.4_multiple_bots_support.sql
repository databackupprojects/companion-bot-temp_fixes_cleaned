-- Migration v3.4: Add support for multiple bots per user
-- This migration:
-- 1. Removes unique constraint on user_id in bot_settings
-- 2. Adds is_active and is_primary columns
-- 3. Creates indexes for better query performance

-- Add new columns to bot_settings
ALTER TABLE bot_settings 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE;

-- Drop the unique constraint on user_id if it exists
-- First, find the constraint name (it varies based on PostgreSQL version)
DO $$ 
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'bot_settings'::regclass
    AND contype = 'u'
    AND array_position(conkey, (SELECT attnum FROM pg_attribute WHERE attrelid = 'bot_settings'::regclass AND attname = 'user_id')) IS NOT NULL;
    
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE bot_settings DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_bot_settings_user_active ON bot_settings(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_bot_settings_user_primary ON bot_settings(user_id, is_primary);

-- Set existing bots as primary for their users
UPDATE bot_settings 
SET is_primary = TRUE, is_active = TRUE
WHERE id IN (
    SELECT DISTINCT ON (user_id) id 
    FROM bot_settings 
    ORDER BY user_id, created_at ASC
);

-- Verify the migration
SELECT 
    COUNT(*) as total_bots,
    COUNT(DISTINCT user_id) as total_users,
    COUNT(*) FILTER (WHERE is_primary = TRUE) as primary_bots,
    COUNT(*) FILTER (WHERE is_active = TRUE) as active_bots
FROM bot_settings;
