-- Initialize pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Table for raw/parsed documents
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    tier INTEGER NOT NULL CHECK (tier IN (1, 2, 3)),
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    publish_date TEXT,
    content_type TEXT DEFAULT 'text',
    sha256 TEXT NOT NULL,
    is_simulated BOOLEAN DEFAULT FALSE,
    metadata_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table for searchable chunks with dense embeddings and sparse tsvector
CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    cleaned_content TEXT NOT NULL,
    token_count INTEGER DEFAULT 0,
    tier INTEGER NOT NULL CHECK (tier IN (1, 2, 3)),
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    publish_date TEXT,
    is_simulated BOOLEAN DEFAULT FALSE,
    institution_tags JSONB DEFAULT '[]'::jsonb,
    embedding vector(1536),
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON document_chunks(source);
CREATE INDEX IF NOT EXISTS idx_chunks_tier ON document_chunks(tier);
CREATE INDEX IF NOT EXISTS idx_chunks_simulated ON document_chunks(is_simulated);
CREATE INDEX IF NOT EXISTS idx_chunks_tsv ON document_chunks USING GIN(tsv);

-- HNSW vector index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
ON document_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Table for persistent human-in-the-loop review queue
CREATE TABLE IF NOT EXISTS approval_queue (
    post_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    approval_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    rejection_reason TEXT,
    editor_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_approval_queue_status ON approval_queue(approval_status);

