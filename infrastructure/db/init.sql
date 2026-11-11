-- Runs once on first container start. Owner role `fintrack` is created by the image.
CREATE ROLE fintrack_app LOGIN PASSWORD 'fintrack_app';
CREATE DATABASE fintrack_test OWNER fintrack;
\connect fintrack
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
GRANT CONNECT ON DATABASE fintrack TO fintrack_app;
\connect fintrack_test
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
GRANT CONNECT ON DATABASE fintrack_test TO fintrack_app;
