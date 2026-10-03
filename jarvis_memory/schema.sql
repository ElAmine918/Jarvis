
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    conversation_id VARCHAR(100) NOT NULL,
    source_message_id VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    message_ts TIMESTAMPTZ NOT NULL,
    seq INT NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    fts tsvector GENERATED ALWAYS AS (to_tsvector('simple', left(content, 500000))) STORED,
    CONSTRAINT uq_message_source UNIQUE (source, conversation_id, source_message_id)
);
CREATE INDEX messages_conv_seq_idx ON messages (conversation_id, seq);
CREATE INDEX messages_ts_idx ON messages (message_ts);
CREATE INDEX messages_source_idx ON messages (source);
CREATE INDEX messages_fts_idx ON messages USING GIN (fts);

CREATE TABLE message_embeddings (
    message_id BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    embedded_text TEXT NOT NULL,
    embedding_model VARCHAR(50) NOT NULL,
    embedding halfvec(768) NOT NULL,
    CONSTRAINT uq_embedding_chunk UNIQUE (message_id, chunk_index, embedding_model)
);

CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding halfvec(768),
    embedding_model_name VARCHAR(50),
    match_count INT DEFAULT 5,
    filter_date_min TIMESTAMPTZ DEFAULT NULL,
    filter_date_max TIMESTAMPTZ DEFAULT NULL,
    filter_source VARCHAR(50) DEFAULT NULL,
    filter_role VARCHAR(50) DEFAULT NULL
) RETURNS TABLE (
    message_id BIGINT,
    content TEXT,
    message_ts TIMESTAMPTZ,
    conversation_id VARCHAR(100),
    score FLOAT8
) AS $$
BEGIN
    SET LOCAL hnsw.iterative_scan = 'relaxed_order';
    
    RETURN QUERY
    WITH vector_matches_raw AS (
        SELECT 
            me.message_id,
            (1.0 - (me.embedding <=> query_embedding))::FLOAT8 AS vector_score
        FROM message_embeddings me
        JOIN messages m ON m.id = me.message_id
        WHERE me.embedding_model = embedding_model_name
          AND (filter_date_min IS NULL OR m.message_ts >= filter_date_min)
          AND (filter_date_max IS NULL OR m.message_ts <= filter_date_max)
          AND (filter_source IS NULL OR m.source = filter_source)
          AND (filter_role IS NULL OR m.role = filter_role)
        ORDER BY me.embedding <=> query_embedding
        LIMIT match_count * 4
    ),
    vector_matches_distinct AS (
        SELECT DISTINCT ON (vm.message_id) vm.message_id, vm.vector_score
        FROM vector_matches_raw vm
        ORDER BY vm.message_id, vm.vector_score DESC
    ),
    vector_matches AS (
        SELECT 
            vmd.message_id, 
            ROW_NUMBER() OVER (ORDER BY vmd.vector_score DESC) AS vector_rank
        FROM vector_matches_distinct vmd
        ORDER BY vmd.vector_score DESC
        LIMIT match_count
    ),
    fts_matches AS (
        SELECT 
            m.id AS message_id,
            ROW_NUMBER() OVER (ORDER BY ts_rank(m.fts, websearch_to_tsquery('simple', query_text)) DESC) AS fts_rank
        FROM messages m
        WHERE (filter_date_min IS NULL OR m.message_ts >= filter_date_min)
          AND (filter_date_max IS NULL OR m.message_ts <= filter_date_max)
          AND (filter_source IS NULL OR m.source = filter_source)
          AND (filter_role IS NULL OR m.role = filter_role)
          AND m.fts @@ websearch_to_tsquery('simple', query_text)
        ORDER BY ts_rank(m.fts, websearch_to_tsquery('simple', query_text)) DESC
        LIMIT match_count
    ),
    unified AS (
        SELECT 
            COALESCE(v.message_id, f.message_id) AS msg_id,
            (
                CASE WHEN v.vector_rank IS NOT NULL THEN (1.0 / (60.0 + v.vector_rank)) ELSE 0.0 END +
                CASE WHEN f.fts_rank IS NOT NULL THEN (1.0 / (60.0 + f.fts_rank)) ELSE 0.0 END
            )::FLOAT8 AS rrf_score
        FROM vector_matches v
        FULL OUTER JOIN fts_matches f ON f.message_id = v.message_id
    )
    SELECT 
        u.msg_id,
        m.content,
        m.message_ts,
        m.conversation_id,
        u.rrf_score
    FROM unified u
    JOIN messages m ON m.id = u.msg_id
    ORDER BY u.rrf_score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_context(
    target_message_id BIGINT,
    n INT DEFAULT 5
) RETURNS TABLE (
    message_id BIGINT,
    source VARCHAR(50),
    conversation_id VARCHAR(100),
    role VARCHAR(50),
    content TEXT,
    message_ts TIMESTAMPTZ,
    seq INT
) AS $$
DECLARE
    target_conv VARCHAR(100);
    target_seq INT;
BEGIN
    SELECT m.conversation_id, m.seq INTO target_conv, target_seq 
    FROM messages m WHERE m.id = target_message_id;

    IF FOUND THEN
        RETURN QUERY
        SELECT m.id, m.source, m.conversation_id, m.role, m.content, m.message_ts, m.seq
        FROM messages m
        WHERE m.conversation_id = target_conv
          AND m.seq BETWEEN (target_seq - n) AND (target_seq + n)
        ORDER BY m.seq ASC;
    END IF;
END;
$$ LANGUAGE plpgsql;
