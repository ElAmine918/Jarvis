import os
import subprocess

DIR = "/Users/amine/Code/MyCloud/jarvis_memory"
os.makedirs(DIR, exist_ok=True)

# 1. Compose
compose = """
services:
  pgvector:
    image: pgvector/pgvector:pg16-v0.8.0
    restart: unless-stopped
    environment:
      POSTGRES_USER: jarvis
      POSTGRES_PASSWORD: ${DB_PASSWORD:-testpass}
      POSTGRES_DB: jarvis_memory
    shm_size: 256mb
    command: ["postgres", "-c", "shared_buffers=256MB", "-c", "maintenance_work_mem=256MB"]
    volumes:
      - ./schema.sql:/docker-entrypoint-initdb.d/schema.sql:ro
    networks:
      - db_net
    deploy:
      resources:
        limits:
          memory: 1G

networks:
  db_net:
    name: ${JARVIS_NETWORK:-jarvis_api_net}
    external: false
"""
with open(f"{DIR}/docker-compose.yml", "w") as f: f.write(compose)

# 2. Schema
schema = """
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
"""
with open(f"{DIR}/schema.sql", "w") as f: f.write(schema)

# 3. Post Backfill
with open(f"{DIR}/post_backfill.sql", "w") as f:
    f.write("CREATE INDEX message_embeddings_idx ON message_embeddings USING hnsw (embedding halfvec_cosine_ops);")

# 4. Test Data
test_data = """
INSERT INTO messages (id, source, conversation_id, source_message_id, role, content, content_hash, message_ts, seq) VALUES
(1, 'webui', 'c1', 'm1', 'user', 'J aime beaucoup Docker et Proxmox', 'h1', '2026-10-01 10:00:00', 1),
(2, 'webui', 'c2', 'm2', 'user', 'Une recette de tarte', 'h2', '2026-10-02 10:00:00', 1),
(3, 'telegram', 'c3', 'm3', 'user', 'Le kernel linux', 'h3', '2026-10-03 10:00:00', 1),
(4, 'webui', 'c4', 'm4', 'user', 'ok', 'h_ok', '2026-10-04 10:00:00', 1),
(5, 'telegram', 'c5', 'm5', 'user', 'ok', 'h_ok', '2026-10-05 10:00:00', 1);

INSERT INTO message_embeddings (message_id, chunk_index, embedded_text, embedding_model, embedding) VALUES
(1, 0, 'Docker et Proxmox', 'nomic-embed-text', (ARRAY[1.0] || array_fill(0, ARRAY[767]))::halfvec(768)),
(2, 0, 'Recette de tarte', 'nomic-embed-text', (ARRAY[0.0, 1.0] || array_fill(0, ARRAY[766]))::halfvec(768)),
(3, 0, 'Kernel linux', 'nomic-embed-text', (ARRAY[0.0, 0.0, 1.0] || array_fill(0, ARRAY[765]))::halfvec(768)),
(4, 0, 'ok', 'nomic-embed-text', (ARRAY[0.0, 0.0, 0.0, 1.0] || array_fill(0, ARRAY[764]))::halfvec(768)),
(5, 0, 'ok', 'nomic-embed-text', (ARRAY[0.0, 0.0, 0.0, 1.0] || array_fill(0, ARRAY[764]))::halfvec(768)),
(1, 1, 'Docker et Proxmox', 'autre-modele', (ARRAY[0.5] || array_fill(0, ARRAY[767]))::halfvec(768));
"""
with open(f"{DIR}/test_data.sql", "w") as f: f.write(test_data)

# 5. Run Tests
run_tests = """#!/bin/bash
set -e
PROJECT="jarvis_test"
export JARVIS_NETWORK="jarvis_test_net"
export DB_PASSWORD="testpass"

cleanup() {
    echo "🧹 Nettoyage..."
    docker compose -p "$PROJECT" down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT ERR

docker compose -p "$PROJECT" up -d >/dev/null 2>&1

echo "Attente de PostgreSQL..."
until docker compose -p "$PROJECT" exec -T pgvector pg_isready -U jarvis >/dev/null 2>&1; do sleep 1; done
sleep 2

docker compose -p "$PROJECT" exec -T pgvector psql -U jarvis -d jarvis_memory < test_data.sql >/dev/null

run_sql() {
    docker compose -p "$PROJECT" exec -T pgvector psql -U jarvis -d jarvis_memory -tA -c "$1"
}

run_test() {
    local desc="$1"; local query="$2"; local expected="$3"
    local res; res=$(run_sql "$query")
    if [ "$res" = "$expected" ]; then
        echo "✅ PASS : $desc"
    else
        echo "❌ FAIL : $desc (Attendu '$expected', Reçu '$res')"
        exit 1
    fi
}

echo "=== TESTS ==="
run_test "a) Match mixte (mot-clé + vecteur)" "SELECT message_id FROM hybrid_search('Docker', (ARRAY[1.0] || array_fill(0, ARRAY[767]))::halfvec(768), 'nomic-embed-text', 1);" "1"
run_test "b) Mots-clés seul (Vecteur éloigné)" "SELECT message_id FROM hybrid_search('tarte', (array_fill(0, ARRAY[768]))::halfvec(768), 'nomic-embed-text', 1);" "2"
run_test "c) Vecteur seul" "SELECT message_id FROM hybrid_search('brouhaha', (ARRAY[0,0,1.0] || array_fill(0, ARRAY[765]))::halfvec(768), 'nomic-embed-text', 1);" "3"
run_test "d) Filtre de date" "SELECT message_id FROM hybrid_search('ok', (ARRAY[0,0,0,1.0] || array_fill(0, ARRAY[764]))::halfvec(768), 'nomic-embed-text', 1, filter_date_min := '2026-10-04 12:00:00');" "5"
run_test "e) Filtre de source" "SELECT message_id FROM hybrid_search('ok', (ARRAY[0,0,0,1.0] || array_fill(0, ARRAY[764]))::halfvec(768), 'nomic-embed-text', 1, filter_source := 'telegram');" "5"
run_test "f) Changement de modèle" "SELECT message_id FROM hybrid_search('Docker', (ARRAY[0.5] || array_fill(0, ARRAY[767]))::halfvec(768), 'autre-modele', 1);" "1"
run_test "g) Doublons ok conservés" "SELECT count(*) FROM messages WHERE content = 'ok';" "2"

echo "=== PERF TEST ==="
docker compose -p "$PROJECT" exec -T pgvector psql -U jarvis -d jarvis_memory -c "
DO \\\$\\\$ BEGIN
  FOR i IN 10..20000 LOOP
    INSERT INTO messages (source, conversation_id, source_message_id, role, content, content_hash, message_ts, seq)
    VALUES ('test', 'c'||i, 'm'||i, 'user', 'dummy', 'h'||i, now(), 1);
    INSERT INTO message_embeddings (message_id, chunk_index, embedded_text, embedding_model, embedding)
    VALUES ((SELECT id FROM messages WHERE source_message_id = 'm'||i), 0, 'dummy', 'nomic-embed-text', (array_fill(random(), ARRAY[768]))::halfvec(768));
  END LOOP;
END; \\\$\\\$;" >/dev/null

docker compose -p "$PROJECT" exec -T pgvector psql -U jarvis -d jarvis_memory < post_backfill.sql >/dev/null
echo "✅ Index HNSW créé"
res=$(run_sql "EXPLAIN ANALYZE SELECT message_id FROM message_embeddings WHERE embedding_model = 'nomic-embed-text' ORDER BY embedding <=> (array_fill(0.1, ARRAY[768]))::halfvec(768) LIMIT 10;")
if echo "$res" | grep -q "Index Scan"; then
    echo "✅ PASS : Index Scan utilisé par HNSW"
else
    echo "❌ FAIL : HNSW non utilisé. EXPLAIN:"
    echo "$res"
    exit 1
fi

echo "=== BACKUP & RESTORE ==="
docker compose -p "$PROJECT" exec -T pgvector pg_dump -U jarvis -d jarvis_memory -F c > test.dump
run_sql "CREATE DATABASE restore_db;" >/dev/null
docker compose -p "$PROJECT" exec -T pgvector pg_restore -U jarvis -d restore_db -1 < test.dump >/dev/null
echo "✅ PASS : Backup et Restore"
"""
with open(f"{DIR}/run_tests.sh", "w") as f: f.write(run_tests)
os.chmod(f"{DIR}/run_tests.sh", 0o755)

# Python Script
py_code = """
import re
import pytest

STOP_WORDS = {"le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "à", "a", "et", "ou", "mais", "donc", "or", "ni", "car", "pour", "dans", "en"}

def build_fts_query(text: str) -> str:
    cleaned = re.sub(r'[^\w\s]', ' ', text)
    words = cleaned.split()
    filtered = [w for w in words if w.lower() not in STOP_WORDS]
    if not filtered: return ""
    return " or ".join(filtered)

def test_build_fts_query_basic():
    assert build_fts_query("Recette de tarte-aux-pommes !") == "Recette tarte aux pommes"
"""
with open(f"{DIR}/query_builder.py", "w") as f: f.write(py_code)

# Backup scripts
with open(f"{DIR}/backup.sh", "w") as f:
    f.write("#!/bin/bash\nset -euo pipefail\nBACKUP_DIR=\"/opt/jarvis/backups/db\"\ndocker compose exec -T pgvector pg_dump -U jarvis -d jarvis_memory -F c > ${BACKUP_DIR}/dump.tmp\nmv ${BACKUP_DIR}/dump.tmp ${BACKUP_DIR}/dump.dump\nfind ${BACKUP_DIR} -mtime +7 -delete\n")
with open(f"{DIR}/pull_backup_mac.sh", "w") as f:
    f.write("#!/bin/bash\nrsync -avz root@100.x.y.z:/opt/jarvis/backups/db/ ~/JarvisBackups/\n")
