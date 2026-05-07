-- Revoke `authenticated`-role access to all public-schema objects.
--
-- Mirror of 20260506_b_revoke_anon_public.sql but for the `authenticated`
-- DB role. PostgREST routes any JWT carrying `role: authenticated` to this
-- DB role; the Supabase template grants `authenticated` SELECT/INSERT/
-- UPDATE/DELETE on every public table by default.
--
-- This codebase never legitimately issues `authenticated` JWTs — the
-- backend uses `service_role` exclusively, and end-users hold `app_users`
-- JWTs signed with `JWT_SECRET` (not the Supabase JWT secret). So
-- `authenticated` is dormant. But anyone who obtains the Supabase JWT
-- secret (`SERVICE_PASSWORD_JWT`) could mint such a token and bypass our
-- application-layer enforcement.
--
-- Without this migration, the 2026-05-06 anon revoke is half a job:
-- the same exposure exists via `authenticated`.
--
-- `service_role` is intentionally NOT touched — the backend depends on it.
--
-- Applied: prod TBD (manual via Studio SQL editor).
-- Status on dev: pending.

-- Existing objects.
REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM authenticated;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM authenticated;

-- Future objects created by the standard owners.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin IN SCHEMA public
    REVOKE ALL ON TABLES    FROM authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin IN SCHEMA public
    REVOKE ALL ON FUNCTIONS FROM authenticated;
