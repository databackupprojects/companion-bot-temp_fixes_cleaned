-- Migration: Add quiz_token field to bot_settings table
-- Description: Links bot configurations back to their original quiz tokens for proper persona retrieval

-- Check if column exists before adding (for idempotency)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'bot_settings' 
        AND column_name = 'quiz_token'
    ) THEN
        ALTER TABLE bot_settings ADD COLUMN quiz_token VARCHAR(32);
        CREATE UNIQUE INDEX idx_bot_settings_quiz_token ON bot_settings(quiz_token) WHERE quiz_token IS NOT NULL;
        RAISE NOTICE 'Added quiz_token column and index to bot_settings';
    ELSE
        RAISE NOTICE 'quiz_token column already exists in bot_settings';
    END IF;
END $$;
