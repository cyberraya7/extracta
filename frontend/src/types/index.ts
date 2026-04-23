export interface UploadResult {
  document_id: string;
  filename: string;
  size: number;
  text_length: number;
  extraction_status?: string;
  extraction_message?: string;
  extractor_used?: string;
  /** Embedded file metadata (EXIF, PDF/DOCX props, media tags, etc.); empty object if none found. */
  exif_metadata?: Record<string, unknown> | null;
}

export interface ProcessRequest {
  document_ids?: string[];
  labels?: string[];
  confidence_threshold?: number;
  enable_osint?: boolean;
  osint_timeout_seconds?: number;
}

export interface ProcessResponse {
  status: string;
  entity_count: number;
  edge_count: number;
  document_ids: string[];
  session_id?: string;
}

export interface EntityPosition {
  start: number;
  end: number;
}

export interface Entity {
  id: string;
  text: string;
  label: string;
  score: number;
  occurrences: number;
  variants: string[];
  positions: EntityPosition[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  score: number;
  occurrences: number;
  connections: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  relationship: string;
  source_label: string;
  target_label: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface EvidenceSnippet {
  text: string;
  entity_text?: string;
  entities?: string[];
  highlight_ranges?: Array<{ start: number; end: number }>;
  start?: number;
  end?: number;
  document_id: string;
  document_name: string;
}

export interface EvidenceResult {
  entity_id?: string;
  edge_key?: string;
  snippets: EvidenceSnippet[];
}

export interface InvestigationFinding {
  title: string;
  category: string;
  confidence: number;
  attributes: Record<string, unknown>;
  collected_at: string;
}

export interface InvestigationResult {
  entity_id: string;
  status: 'not_requested' | 'pending' | 'completed' | 'partial' | 'failed' | 'not_configured';
  summary: string;
  findings: InvestigationFinding[];
  notes: string[];
  variant?: string | null;
}

export type InvestigationSource = 'tools' | 'instagram_leak';

export interface InvestigationRunRequest {
  source: InvestigationSource;
}

export type EntityType =
  | 'person'
  | 'organization'
  | 'location'
  | 'date'
  | 'money'
  | 'communication platform'
  | 'social media platform'
  | 'username'
  | 'email'
  | 'phone'
  | 'ic number'
  | 'ip address'
  | 'port number'
  | 'asn number';

export const ENTITY_COLORS: Record<string, string> = {
  person: '#3b82f6',
  organization: '#22c55e',
  location: '#ef4444',
  date: '#f59e0b',
  money: '#a855f7',
  'communication platform': '#06b6d4',
  'social media platform': '#f43f5e',
  username: '#0ea5e9',
  email: '#ec4899',
  phone: '#14b8a6',
  'ic number': '#f97316',
  'ip address': '#6366f1',
  'port number': '#8b5cf6',
  'asn number': '#ca8a04',
};

export const ENTITY_LABELS: string[] = [
  'person',
  'organization',
  'location',
  'date',
  'money',
  'communication platform',
  'social media platform',
  'username',
  'email',
  'phone',
  'ic number',
  'ip address',
  'port number',
  'asn number',
];

export const ENTITY_LABEL_DISPLAY: Record<string, string> = {
  person: 'Person',
  organization: 'Organization',
  location: 'Location',
  date: 'Date',
  money: 'Money',
  'communication platform': 'Messaging platform',
  'social media platform': 'Social media platform',
  username: 'Username',
  email: 'Email',
  phone: 'Phone',
  'ic number': 'IC Number',
  'ip address': 'IP Address',
  'port number': 'Port number',
  'asn number': 'ASN number',
};

export function getEntityLabelDisplay(label: string): string {
  return ENTITY_LABEL_DISPLAY[label] || label;
}

export interface ProcessStatus {
  session_id: string;
  status: 'processing' | 'investigating' | 'finalizing' | 'completed' | 'error';
  progress: number;
  total: number;
  current_file: string;
  entity_count: number;
  edge_count: number;
  documents_with_no_text?: number;
  documents_skipped_for_extraction?: number;
  warnings?: string[];
  error?: string;
}

export interface AnalysisSession {
  id: string;
  name: string;
  created_at: string | null;
  document_count: number;
  entity_count: number;
  edge_count: number;
}

export interface SessionDetail extends AnalysisSession {
  documents: UploadResult[];
}

export interface BulkSessionDeleteResponse {
  deleted_ids: string[];
  not_found_ids: string[];
}

export interface LinkedEntity {
  entity_id: string;
  text: string;
  label: string;
  score: number;
  document_count: number;
  document_ids: string[];
  document_names: Record<string, string>;
}

export interface FaceInstance {
  id: string;
  document_id: string;
  source_type: string;
  source_ref: string;
  bbox: number[];
  confidence: number;
  cluster_id: string;
  thumbnail_path: string;
}

export interface FaceCluster {
  cluster_id: string;
  face_count: number;
  document_count: number;
  document_ids: string[];
  document_names: Record<string, string>;
  suggested_name?: string | null;
  display_name?: string | null;
  faces: FaceInstance[];
}
