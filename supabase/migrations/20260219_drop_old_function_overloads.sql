-- Drop old overloaded function signatures that conflict with the new
-- scope-isolated versions added in 20260221_rag_scoped_search.sql.
--
-- PostgreSQL allows function overloading, but PostgREST (PGRST203) cannot
-- resolve the ambiguity when both signatures match the supplied parameters.
-- Dropping the old 5-parameter variants removes the ambiguity.

-- Old match_document_chunks: (vector, uuid, uuid, float, int) — no pool_id
DROP FUNCTION IF EXISTS match_document_chunks(
    vector(1536), UUID, UUID, FLOAT, INT
);

-- Old match_document_assets: (vector, uuid, uuid, float, int) — no pool_id
DROP FUNCTION IF EXISTS match_document_assets(
    vector(1536), UUID, UUID, FLOAT, INT
);
