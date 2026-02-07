/**
 * Knowledge Base, Document, and Search types.
 *
 * Source of truth: API_CONTRACTS.md Section 6.6
 */

import type {
  DocumentProcessingState,
  KnowledgeBaseCategory,
  KnowledgeBaseSourceType,
} from "./enums";

export interface KnowledgeBaseResponse {
  id: string;
  tenant_id: string;
  name: string;
  category: KnowledgeBaseCategory;
  source_type: KnowledgeBaseSourceType;
  document_count: number;
  ready_document_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface DocumentResponse {
  id: string;
  tenant_id: string;
  knowledge_base_id: string;
  name: string;
  document_uri: string;
  source_uri: string | null;
  mime_type: string | null;
  byte_size: number | null;
  hash: string | null;
  processing_state: DocumentProcessingState;
  version_number: number;
  previous_version_id: string | null;
  metadata: Record<string, unknown>;
  chunk_count: number;
  retry_count: number;
  last_error_message: string | null;
  dead_letter: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface DocumentVersion {
  id: string;
  name: string;
  version_number: number;
  processing_state: DocumentProcessingState;
  byte_size: number | null;
  created_at: string | null;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_name: string;
  document_uri: string;
  knowledge_base_category: KnowledgeBaseCategory;
  chunk_index: number;
  content: string;
  contextual_prefix: string | null;
  score: number;
  source_uri: string | null;
  metadata: Record<string, unknown>;
}
