-- Create application roles with least-privilege defaults
DO $$ BEGIN
   CREATE ROLE mcp_app LOGIN PASSWORD 'change-me';
EXCEPTION WHEN duplicate_object THEN RAISE NOTICE 'role exists'; END $$;

DO $$ BEGIN
   CREATE ROLE langfuse LOGIN PASSWORD 'change-me';
EXCEPTION WHEN duplicate_object THEN RAISE NOTICE 'role exists'; END $$;

