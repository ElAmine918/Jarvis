
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
