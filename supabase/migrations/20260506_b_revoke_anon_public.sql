-- Revoke anon-role access to all public-schema objects.
--
-- Background: this codebase uses application-layer access control (Python
-- ownership checks + JWT) and the backend connects to Supabase with the
-- service-role key. The anon role has no legitimate purpose in this stack,
-- but Supabase's default Postgres grants give anon SELECT on every table
-- in `public`. Verified 2026-05-06: anon JWT against `/rest/v1/app_users`
-- on prod returned full user records including bcrypt password hashes.
-- This migration closes that exposure.
--
-- Applied: prod 2026-05-06 (manual via Studio SQL editor).
-- Status on dev: pending until dev exposes an anon role; safe to run anyway.

-- Existing objects.
REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM anon;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon;

-- Future objects created by the standard owners (supabase_admin via
-- /pg/query, postgres via psql/superuser path). Belt-and-suspenders so a
-- newly-created table can't silently re-expose data through anon.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin IN SCHEMA public
    REVOKE ALL ON TABLES    FROM anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin IN SCHEMA public
    REVOKE ALL ON FUNCTIONS FROM anon;
