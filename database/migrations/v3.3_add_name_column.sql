-- Migration v3.3: Add name column to users table
-- Description: Add the missing 'name' column that's referenced in the User model

ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(100);

-- Add comment
COMMENT ON COLUMN users.name IS 'User full name from quiz or registration';
