-- Migration v3.6: Add bot_id support to messages table
-- This migration adds the bot_id column to messages table to support multiple bots per user
-- and create indexes for better query performance

-- Add bot_id column to messages table
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS bot_id UUID REFERENCES bot_settings(id) ON DELETE CASCADE;

-- Create indexes for better query performance when filtering by bot_id
CREATE INDEX IF NOT EXISTS idx_messages_user_created ON messages(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_bot_created ON messages(bot_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_user_bot_created ON messages(user_id, bot_id, created_at DESC);

-- Verify the migration
SELECT 
    COUNT(*) as total_messages,
    COUNT(DISTINCT user_id) as total_users,
    COUNT(*) FILTER (WHERE bot_id IS NOT NULL) as messages_with_bot_id,
    COUNT(*) FILTER (WHERE bot_id IS NULL) as messages_without_bot_id
FROM messages;
