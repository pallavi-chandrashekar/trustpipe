"""v001: Initial schema for TrustPipe."""

SCHEMA_VERSION = 1

SQL = """
CREATE TABLE IF NOT EXISTS provenance_records (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    source          TEXT,
    parent_ids      TEXT,
    fingerprint     TEXT NOT NULL,
    row_count       INTEGER,
    column_count    INTEGER,
    column_names    TEXT,
    byte_size       INTEGER,
    statistical_summary TEXT,
    merkle_root     TEXT NOT NULL,
    merkle_index    INTEGER NOT NULL,
    previous_root   TEXT,
    tags            TEXT,
    metadata        TEXT,
    created_at      TEXT NOT NULL,
    data_timestamp  TEXT,
    project         TEXT NOT NULL DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_prov_name ON provenance_records(name);
CREATE INDEX IF NOT EXISTS idx_prov_project ON provenance_records(project);
CREATE INDEX IF NOT EXISTS idx_prov_created ON provenance_records(created_at);

CREATE TABLE IF NOT EXISTS trust_scores (
    id              TEXT PRIMARY KEY,
    record_id       TEXT,
    dataset_name    TEXT,
    composite       INTEGER NOT NULL,
    grade           TEXT NOT NULL,
    dimensions      TEXT NOT NULL,
    warnings        TEXT,
    computed_at     TEXT NOT NULL,
    config_snapshot TEXT,
    project         TEXT NOT NULL DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_trust_dataset ON trust_scores(dataset_name);

CREATE TABLE IF NOT EXISTS compliance_reports (
    id              TEXT PRIMARY KEY,
    dataset_name    TEXT NOT NULL,
    regulation      TEXT NOT NULL,
    content         TEXT NOT NULL,
    output_format   TEXT NOT NULL,
    generated_at    TEXT NOT NULL,
    record_ids      TEXT,
    trust_score_id  TEXT,
    project         TEXT NOT NULL DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS merkle_nodes (
    idx             INTEGER NOT NULL,
    hash            TEXT NOT NULL,
    project         TEXT NOT NULL DEFAULT 'default',
    PRIMARY KEY (project, idx)
);

CREATE TABLE IF NOT EXISTS schema_version (
    version         INTEGER PRIMARY KEY,
    applied_at      TEXT NOT NULL
);
"""
