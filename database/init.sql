-- database/init.sql - Database Initialization
CREATE DATABASE companion_bot;
CREATE USER companion_user WITH PASSWORD 'companion_password';
GRANT ALL PRIVILEGES ON DATABASE companion_bot TO companion_user;
ALTER DATABASE companion_bot SET timezone TO 'UTC';

-- Connect to the database
\c companion_bot;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";