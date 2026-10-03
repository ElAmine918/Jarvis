#!/bin/bash
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
DO \\$\\$ BEGIN
  FOR i IN 10..20000 LOOP
    INSERT INTO messages (source, conversation_id, source_message_id, role, content, content_hash, message_ts, seq)
    VALUES ('test', 'c'||i, 'm'||i, 'user', 'dummy', 'h'||i, now(), 1);
    INSERT INTO message_embeddings (message_id, chunk_index, embedded_text, embedding_model, embedding)
    VALUES ((SELECT id FROM messages WHERE source_message_id = 'm'||i), 0, 'dummy', 'nomic-embed-text', (array_fill(random(), ARRAY[768]))::halfvec(768));
  END LOOP;
END; \\$\\$;" >/dev/null

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
