-- =============================================================================
-- YourAI — Canonical Database Schema
-- =============================================================================
-- PostgreSQL 16 | UUIDv7 primary keys | Row-Level Security on all tenant tables
--
-- This file is the single source of truth. All SQLAlchemy models MUST match
-- this schema exactly. Run against a fresh database to verify syntax.
--
-- Conventions:
--   - UUIDv7 generated at application layer; gen_random_uuid() as DB fallback
--   - All tables have created_at / updated_at TIMESTAMPTZ columns
--   - Tenant-scoped tables have tenant_id UUID NOT NULL + RLS policy
--   - British English in all comments and user-facing strings
--   - ON DELETE CASCADE on child entities; SET NULL on informational refs
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 2. Enum Types (23)
-- ---------------------------------------------------------------------------
CREATE TYPE subscription_tier       AS ENUM ('starter', 'professional', 'enterprise');
CREATE TYPE user_status             AS ENUM ('pending', 'active', 'disabled', 'deleted');
CREATE TYPE conversation_state      AS ENUM ('pending', 'waiting_for_reply', 'generating_reply', 'outputting_reply', 'ready');
CREATE TYPE message_role            AS ENUM ('user', 'assistant');
CREATE TYPE message_state           AS ENUM ('pending', 'success', 'error', 'cancelled');
CREATE TYPE confidence_level        AS ENUM ('high', 'medium', 'low');
CREATE TYPE verification_status     AS ENUM ('verified', 'unverified', 'removed', 'pre_1963_digitised');
CREATE TYPE agent_invocation_mode   AS ENUM ('conversation', 'policy_review');
CREATE TYPE model_tier              AS ENUM ('haiku', 'sonnet', 'opus');
CREATE TYPE knowledge_base_category AS ENUM ('legislation', 'case_law', 'explanatory_notes', 'amendments', 'company_policy', 'sector_knowledge', 'parliamentary');
CREATE TYPE knowledge_base_source_type AS ENUM ('lex_api', 'uploaded', 'catalog', 'parliament_mcp');
CREATE TYPE document_processing_state AS ENUM ('uploaded', 'validating', 'extracting_text', 'chunking', 'contextualising', 'embedding', 'indexing', 'ready', 'failed');
CREATE TYPE guardrail_status        AS ENUM ('creating', 'updating', 'versioning', 'ready', 'failed', 'deleting');
CREATE TYPE review_cycle            AS ENUM ('annual', 'monthly', 'quarterly');
CREATE TYPE policy_review_state     AS ENUM ('pending', 'processing', 'verifying', 'complete', 'error', 'cancelled');
CREATE TYPE rag_rating              AS ENUM ('green', 'amber', 'red');
CREATE TYPE regulatory_change_type  AS ENUM ('new_legislation', 'amendment', 'new_regulatory_standard', 'consultation');
CREATE TYPE alert_status            AS ENUM ('pending', 'acknowledged', 'dismissed', 'actioned');
CREATE TYPE billing_event_type      AS ENUM ('credit', 'usage', 'adjustment');
CREATE TYPE billing_feature         AS ENUM ('conversation', 'policy_review', 'title_generation', 'regulatory_monitoring');
CREATE TYPE activity_log_tag        AS ENUM ('user', 'system', 'security', 'ai');
CREATE TYPE feedback_rating         AS ENUM ('up', 'down');
CREATE TYPE feedback_review_status  AS ENUM ('pending', 'reviewed', 'actioned');

-- ---------------------------------------------------------------------------
-- 3. Helper: updated_at trigger function
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================================================================
-- 4. Platform-Level Tables (no tenant_id, no RLS)
-- ===========================================================================

-- 4a. tenants -----------------------------------------------------------
CREATE TABLE tenants (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                        TEXT NOT NULL,
    slug                        TEXT NOT NULL UNIQUE,
    industry_vertical           TEXT,
    branding_config             JSONB NOT NULL DEFAULT '{}',
    subscription_tier           subscription_tier NOT NULL DEFAULT 'starter',
    credit_limit                NUMERIC(12, 4) NOT NULL DEFAULT 0,
    billing_period_start        TIMESTAMPTZ,
    billing_period_end          TIMESTAMPTZ,
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    news_feed_urls              JSONB NOT NULL DEFAULT '[]',
    external_source_integrations JSONB NOT NULL DEFAULT '[]',
    ai_config                   JSONB NOT NULL DEFAULT '{}',
    vector_namespace            TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4b. permissions -------------------------------------------------------
CREATE TABLE permissions (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                        TEXT NOT NULL UNIQUE,
    description                 TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===========================================================================
-- 5. Tenant-Scoped Tables (all have tenant_id; RLS applied later)
-- ===========================================================================

-- 5a. users -------------------------------------------------------------
CREATE TABLE users (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email                       TEXT NOT NULL,
    given_name                  TEXT NOT NULL,
    family_name                 TEXT NOT NULL,
    job_role                    TEXT,
    status                      user_status NOT NULL DEFAULT 'pending',
    last_active_at              TIMESTAMPTZ,
    notification_preferences    JSONB NOT NULL DEFAULT '{}',
    data_deletion_requested_at  TIMESTAMPTZ,
    deleted_at                  TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5b. roles -------------------------------------------------------------
CREATE TABLE roles (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                        TEXT NOT NULL,
    description                 TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, name)
);

-- 5c. personas ----------------------------------------------------------
CREATE TABLE personas (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                        TEXT NOT NULL,
    description                 TEXT,
    system_instructions         TEXT,
    activated_skills            JSONB NOT NULL DEFAULT '[]',
    usage_count                 INTEGER NOT NULL DEFAULT 0,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5d. guardrails --------------------------------------------------------
CREATE TABLE guardrails (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                        TEXT NOT NULL,
    description                 TEXT,
    status                      guardrail_status NOT NULL DEFAULT 'creating',
    configuration_rules         JSONB NOT NULL DEFAULT '{}',
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5e. conversation_templates --------------------------------------------
CREATE TABLE conversation_templates (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                        TEXT NOT NULL,
    prompt_text                 TEXT NOT NULL,
    category                    TEXT,
    industry_vertical           TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5f. conversations -----------------------------------------------------
CREATE TABLE conversations (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id                     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title                       TEXT,
    state                       conversation_state NOT NULL DEFAULT 'pending',
    template_id                 UUID REFERENCES conversation_templates(id) ON DELETE SET NULL,
    deleted_at                  TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5g. messages ----------------------------------------------------------
CREATE TABLE messages (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id             UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    request_id                  UUID,
    role                        message_role NOT NULL,
    content                     TEXT NOT NULL DEFAULT '',
    state                       message_state NOT NULL DEFAULT 'pending',
    metadata                    JSONB NOT NULL DEFAULT '{}',
    file_attachments            JSONB NOT NULL DEFAULT '[]',
    confidence_level            confidence_level,
    verification_result         JSONB,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5h. agent_invocations -------------------------------------------------
CREATE TABLE agent_invocations (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id             UUID REFERENCES conversations(id) ON DELETE CASCADE,
    request_id                  UUID,
    user_id                     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode                        agent_invocation_mode NOT NULL,
    query                       TEXT,
    persona_id                  UUID REFERENCES personas(id) ON DELETE SET NULL,
    context_id                  UUID,
    state                       VARCHAR(50) NOT NULL DEFAULT 'pending',
    attachments                 JSONB NOT NULL DEFAULT '[]',
    model_used                  TEXT,
    model_tier                  model_tier,
    cache_hit                   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5i. agent_invocation_events -------------------------------------------
CREATE TABLE agent_invocation_events (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_invocation_id         UUID NOT NULL REFERENCES agent_invocations(id) ON DELETE CASCADE,
    event_type                  VARCHAR(100) NOT NULL,
    payload                     JSONB NOT NULL DEFAULT '{}',
    sequence_number             INTEGER NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5j. knowledge_bases ---------------------------------------------------
CREATE TABLE knowledge_bases (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                        TEXT NOT NULL,
    category                    knowledge_base_category NOT NULL,
    source_type                 knowledge_base_source_type NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5k. documents ---------------------------------------------------------
CREATE TABLE documents (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    knowledge_base_id           UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    name                        TEXT NOT NULL,
    document_uri                TEXT NOT NULL UNIQUE,
    source_uri                  TEXT,
    mime_type                   TEXT,
    byte_size                   BIGINT,
    hash                        TEXT,
    processing_state            document_processing_state NOT NULL DEFAULT 'uploaded',
    text_extraction_strategy    TEXT,
    extracted_text              TEXT,
    chunking_strategy           TEXT,
    version_number              INTEGER NOT NULL DEFAULT 1,
    previous_version_id         UUID REFERENCES documents(id) ON DELETE SET NULL,
    metadata                    JSONB NOT NULL DEFAULT '{}',
    retry_count                 INTEGER NOT NULL DEFAULT 0,
    last_error_message          TEXT,
    dead_letter                 BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5l. document_chunks ---------------------------------------------------
CREATE TABLE document_chunks (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id                 UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index                 INTEGER NOT NULL,
    parent_chunk_id             UUID REFERENCES document_chunks(id) ON DELETE SET NULL,
    language                    TEXT,
    source_uri                  TEXT,
    byte_range_start            BIGINT,
    byte_range_end              BIGINT,
    byte_range_size             BIGINT,
    hash                        TEXT,
    content                     TEXT NOT NULL,
    contextual_prefix           TEXT,
    embedding_model             TEXT,
    embedding_version           TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5m. document_annotations ----------------------------------------------
CREATE TABLE document_annotations (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id                 UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    document_uri                TEXT,
    annotation_type             TEXT NOT NULL,
    content                     TEXT NOT NULL,
    contributor                 TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5n. policy_definition_groups ------------------------------------------
CREATE TABLE policy_definition_groups (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                        TEXT NOT NULL,
    description                 TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5o. policy_definition_topics ------------------------------------------
CREATE TABLE policy_definition_topics (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                        TEXT NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5p. policy_definitions ------------------------------------------------
CREATE TABLE policy_definitions (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                        TEXT NOT NULL,
    uri                         TEXT NOT NULL,
    status                      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    group_id                    UUID REFERENCES policy_definition_groups(id) ON DELETE SET NULL,
    description                 TEXT,
    is_required                 BOOLEAN NOT NULL DEFAULT FALSE,
    review_cycle                review_cycle,
    name_variants               JSONB NOT NULL DEFAULT '[]',
    scoring_criteria            JSONB NOT NULL DEFAULT '{}',
    compliance_criteria         JSONB NOT NULL DEFAULT '{}',
    required_sections           JSONB NOT NULL DEFAULT '[]',
    legislation_references      JSONB NOT NULL DEFAULT '[]',
    last_regulatory_update_date TIMESTAMPTZ,
    regulatory_change_flags     JSONB NOT NULL DEFAULT '[]',
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, uri)
);

-- 5q. policy_reviews ----------------------------------------------------
CREATE TABLE policy_reviews (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    request_id                  UUID,
    user_id                     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    policy_definition_id        UUID REFERENCES policy_definitions(id) ON DELETE SET NULL,
    state                       policy_review_state NOT NULL DEFAULT 'pending',
    result                      JSONB,
    source                      TEXT,
    citation_verification_result JSONB,
    version                     INTEGER NOT NULL DEFAULT 1,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5r. regulatory_change_alerts ------------------------------------------
CREATE TABLE regulatory_change_alerts (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    change_type                 regulatory_change_type NOT NULL,
    source_reference            TEXT,
    summary                     TEXT,
    affected_policy_definition_ids JSONB NOT NULL DEFAULT '[]',
    status                      alert_status NOT NULL DEFAULT 'pending',
    detected_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at             TIMESTAMPTZ,
    actioned_at                 TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5s. news_stories ------------------------------------------------------
CREATE TABLE news_stories (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title                       TEXT NOT NULL,
    url                         TEXT NOT NULL,
    snippet                     TEXT,
    source                      TEXT,
    image_url                   TEXT,
    published_at                TIMESTAMPTZ,
    fetched_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5t. canvases ----------------------------------------------------------
CREATE TABLE canvases (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id                     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title                       TEXT,
    content                     TEXT,
    html_content                TEXT,
    save_state                  TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5u. activity_logs -----------------------------------------------------
CREATE TABLE activity_logs (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    timestamp                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id                     UUID REFERENCES users(id) ON DELETE SET NULL,
    action                      TEXT NOT NULL,
    detail                      TEXT,
    tags                        activity_log_tag[] NOT NULL DEFAULT '{}',
    retention_expiry_at         TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5v. billing_events ----------------------------------------------------
CREATE TABLE billing_events (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type                  billing_event_type NOT NULL,
    amount                      NUMERIC(12, 4) NOT NULL DEFAULT 0,
    agent_invocation_id         UUID REFERENCES agent_invocations(id) ON DELETE SET NULL,
    model_id                    TEXT,
    feature                     billing_feature,
    description                 TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5w. semantic_cache_entries --------------------------------------------
CREATE TABLE semantic_cache_entries (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    query_embedding             BYTEA,
    query_text                  TEXT NOT NULL,
    response                    TEXT NOT NULL,
    sources                     JSONB NOT NULL DEFAULT '[]',
    ttl_seconds                 INTEGER NOT NULL DEFAULT 3600,
    hit_count                   INTEGER NOT NULL DEFAULT 0,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5x. user_feedback -----------------------------------------------------
CREATE TABLE user_feedback (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    message_id                  UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id                     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating                      feedback_rating NOT NULL,
    comment                     TEXT,
    review_status               feedback_review_status NOT NULL DEFAULT 'pending',
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===========================================================================
-- 6. Join Tables (no tenant_id — parent tables provide isolation)
-- ===========================================================================

-- 6a. role_permissions --------------------------------------------------
CREATE TABLE role_permissions (
    role_id                     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id               UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- 6b. user_roles --------------------------------------------------------
CREATE TABLE user_roles (
    user_id                     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id                     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- 6c. policy_definition_topic_links ------------------------------------
CREATE TABLE policy_definition_topic_links (
    policy_definition_id        UUID NOT NULL REFERENCES policy_definitions(id) ON DELETE CASCADE,
    policy_definition_topic_id  UUID NOT NULL REFERENCES policy_definition_topics(id) ON DELETE CASCADE,
    PRIMARY KEY (policy_definition_id, policy_definition_topic_id)
);

-- ===========================================================================
-- 7. Indexes
-- ===========================================================================

-- Unique indexes (beyond those created by UNIQUE constraints)
-- tenants(slug) — handled by UNIQUE constraint
-- users(tenant_id, email) — composite unique
CREATE UNIQUE INDEX idx_users_tenant_email ON users (tenant_id, email);
-- documents(document_uri) — handled by UNIQUE constraint
-- policy_definitions(tenant_id, uri) — handled by UNIQUE constraint
-- roles(tenant_id, name) — handled by UNIQUE constraint

-- Composite indexes for common query patterns
CREATE INDEX idx_messages_conversation_created
    ON messages (conversation_id, created_at);

CREATE INDEX idx_agent_invocations_conversation_created
    ON agent_invocations (conversation_id, created_at);

CREATE INDEX idx_agent_invocation_events_invocation_seq
    ON agent_invocation_events (agent_invocation_id, sequence_number);

CREATE INDEX idx_documents_kb_state
    ON documents (knowledge_base_id, processing_state);

CREATE INDEX idx_activity_logs_tenant_timestamp
    ON activity_logs (tenant_id, timestamp);

CREATE INDEX idx_billing_events_tenant_created
    ON billing_events (tenant_id, created_at);

CREATE INDEX idx_conversations_user_created
    ON conversations (user_id, created_at);

CREATE INDEX idx_policy_reviews_tenant_state
    ON policy_reviews (tenant_id, state);

CREATE INDEX idx_news_stories_tenant_published
    ON news_stories (tenant_id, published_at DESC);

CREATE INDEX idx_document_chunks_document_index
    ON document_chunks (document_id, chunk_index);

CREATE INDEX idx_users_tenant_status
    ON users (tenant_id, status);

-- Partial index for dead-letter documents
CREATE INDEX idx_documents_dead_letter
    ON documents (tenant_id, dead_letter) WHERE dead_letter = TRUE;

-- GIN indexes for JSONB and array columns
CREATE INDEX idx_documents_metadata_gin
    ON documents USING GIN (metadata);

CREATE INDEX idx_activity_logs_tags_gin
    ON activity_logs USING GIN (tags);

CREATE INDEX idx_messages_metadata_gin
    ON messages USING GIN (metadata);

CREATE INDEX idx_regulatory_alerts_affected_gin
    ON regulatory_change_alerts USING GIN (affected_policy_definition_ids);

-- Foreign key indexes (on FK columns not already covered by composites)
CREATE INDEX idx_conversations_tenant_id ON conversations (tenant_id);
CREATE INDEX idx_conversations_template_id ON conversations (template_id);
CREATE INDEX idx_messages_tenant_id ON messages (tenant_id);
CREATE INDEX idx_agent_invocations_tenant_id ON agent_invocations (tenant_id);
CREATE INDEX idx_agent_invocations_user_id ON agent_invocations (user_id);
CREATE INDEX idx_agent_invocations_persona_id ON agent_invocations (persona_id);
CREATE INDEX idx_agent_invocation_events_tenant_id ON agent_invocation_events (tenant_id);
CREATE INDEX idx_knowledge_bases_tenant_id ON knowledge_bases (tenant_id);
CREATE INDEX idx_documents_tenant_id ON documents (tenant_id);
CREATE INDEX idx_documents_previous_version_id ON documents (previous_version_id);
CREATE INDEX idx_document_chunks_tenant_id ON document_chunks (tenant_id);
CREATE INDEX idx_document_chunks_parent_chunk_id ON document_chunks (parent_chunk_id);
CREATE INDEX idx_document_annotations_tenant_id ON document_annotations (tenant_id);
CREATE INDEX idx_document_annotations_document_id ON document_annotations (document_id);
CREATE INDEX idx_policy_definition_groups_tenant_id ON policy_definition_groups (tenant_id);
CREATE INDEX idx_policy_definition_topics_tenant_id ON policy_definition_topics (tenant_id);
CREATE INDEX idx_policy_definitions_tenant_id ON policy_definitions (tenant_id);
CREATE INDEX idx_policy_definitions_group_id ON policy_definitions (group_id);
CREATE INDEX idx_policy_reviews_user_id ON policy_reviews (user_id);
CREATE INDEX idx_policy_reviews_policy_def_id ON policy_reviews (policy_definition_id);
CREATE INDEX idx_regulatory_change_alerts_tenant_id ON regulatory_change_alerts (tenant_id);
CREATE INDEX idx_news_stories_tenant_id ON news_stories (tenant_id);
CREATE INDEX idx_canvases_tenant_id ON canvases (tenant_id);
CREATE INDEX idx_canvases_user_id ON canvases (user_id);
CREATE INDEX idx_activity_logs_user_id ON activity_logs (user_id);
CREATE INDEX idx_billing_events_agent_invocation_id ON billing_events (agent_invocation_id);
CREATE INDEX idx_semantic_cache_entries_tenant_id ON semantic_cache_entries (tenant_id);
CREATE INDEX idx_user_feedback_tenant_id ON user_feedback (tenant_id);
CREATE INDEX idx_user_feedback_message_id ON user_feedback (message_id);
CREATE INDEX idx_user_feedback_user_id ON user_feedback (user_id);

-- Join table FK indexes (composite PK covers first column; index the second)
CREATE INDEX idx_role_permissions_permission_id ON role_permissions (permission_id);
CREATE INDEX idx_user_roles_role_id ON user_roles (role_id);
CREATE INDEX idx_policy_def_topic_links_topic_id ON policy_definition_topic_links (policy_definition_topic_id);

-- ===========================================================================
-- 8. Row-Level Security (24 tenant-scoped tables)
-- ===========================================================================

-- Enable RLS + FORCE on all tenant-scoped tables, then create policy.
-- FORCE ensures RLS applies even to table owners (defence in depth).
-- Policy reads app.current_tenant_id set by application middleware via
-- SET LOCAL at the start of each database transaction.

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON users
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON roles
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE personas ENABLE ROW LEVEL SECURITY;
ALTER TABLE personas FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON personas
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE guardrails ENABLE ROW LEVEL SECURITY;
ALTER TABLE guardrails FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON guardrails
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE conversation_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_templates FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON conversation_templates
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON conversations
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON messages
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE agent_invocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_invocations FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON agent_invocations
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE agent_invocation_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_invocation_events FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON agent_invocation_events
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE knowledge_bases ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_bases FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON knowledge_bases
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON document_chunks
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE document_annotations ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_annotations FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON document_annotations
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE policy_definition_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE policy_definition_groups FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON policy_definition_groups
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE policy_definition_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE policy_definition_topics FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON policy_definition_topics
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE policy_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE policy_definitions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON policy_definitions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE policy_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE policy_reviews FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON policy_reviews
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE regulatory_change_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE regulatory_change_alerts FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON regulatory_change_alerts
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE news_stories ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_stories FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON news_stories
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE canvases ENABLE ROW LEVEL SECURITY;
ALTER TABLE canvases FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON canvases
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON activity_logs
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE billing_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_events FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON billing_events
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE semantic_cache_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_cache_entries FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON semantic_cache_entries
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_feedback FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON user_feedback
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- ===========================================================================
-- 9. updated_at Triggers (26 non-join tables)
-- ===========================================================================

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_permissions_updated_at
    BEFORE UPDATE ON permissions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_roles_updated_at
    BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_personas_updated_at
    BEFORE UPDATE ON personas
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_guardrails_updated_at
    BEFORE UPDATE ON guardrails
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_conversation_templates_updated_at
    BEFORE UPDATE ON conversation_templates
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_messages_updated_at
    BEFORE UPDATE ON messages
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_agent_invocations_updated_at
    BEFORE UPDATE ON agent_invocations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_agent_invocation_events_updated_at
    BEFORE UPDATE ON agent_invocation_events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_knowledge_bases_updated_at
    BEFORE UPDATE ON knowledge_bases
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_document_chunks_updated_at
    BEFORE UPDATE ON document_chunks
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_document_annotations_updated_at
    BEFORE UPDATE ON document_annotations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_policy_definition_groups_updated_at
    BEFORE UPDATE ON policy_definition_groups
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_policy_definition_topics_updated_at
    BEFORE UPDATE ON policy_definition_topics
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_policy_definitions_updated_at
    BEFORE UPDATE ON policy_definitions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_policy_reviews_updated_at
    BEFORE UPDATE ON policy_reviews
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_regulatory_change_alerts_updated_at
    BEFORE UPDATE ON regulatory_change_alerts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_news_stories_updated_at
    BEFORE UPDATE ON news_stories
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_canvases_updated_at
    BEFORE UPDATE ON canvases
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_activity_logs_updated_at
    BEFORE UPDATE ON activity_logs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_billing_events_updated_at
    BEFORE UPDATE ON billing_events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_semantic_cache_entries_updated_at
    BEFORE UPDATE ON semantic_cache_entries
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_user_feedback_updated_at
    BEFORE UPDATE ON user_feedback
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
