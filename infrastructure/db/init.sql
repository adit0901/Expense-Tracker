-- Runs once on first container start. Owner role `fintrack` is created by the image.
-- Extensions (citext, pg_trgm) are created by the Alembic baseline migration.
CREATE ROLE fintrack_app LOGIN PASSWORD 'fintrack_app';
CREATE DATABASE fintrack_test OWNER fintrack;
