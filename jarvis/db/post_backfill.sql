CREATE INDEX message_embeddings_idx ON message_embeddings USING hnsw (embedding halfvec_cosine_ops);
