-- migrations/v3.2_add_missing_columns.sql
-- Version: 3.2
-- Add missing columns to users table
-- This migration adds columns that are defined in the SQLAlchemy model but missing from the database

-- Add missing columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS username VARCHAR(100);

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS name VARCHAR(100);

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE;

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user';

-- Update last_daily_reset to use TIMESTAMP instead of DATE for consistency
-- Note: This is safe as PostgreSQL can handle the conversion
ALTER TABLE users 
ALTER COLUMN last_daily_reset TYPE TIMESTAMP USING last_daily_reset::timestamp;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
