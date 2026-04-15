export interface UploadResult {
  document_id: string;
  filename: string;
  size: number;
  text_length: number;
}

export interface ProcessRequest {
  document_ids?: string[];
  labels?: string[];
  confidence_threshold?: number;
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

export type EntityType =
  | 'person'
  | 'organization'
  | 'location'
  | 'date'
  | 'money'
  | 'communication platform'
  | 'email'
  | 'phone'
  | 'ic number';

export const ENTITY_COLORS: Record<string, string> = {
  person: '#3b82f6',
  organization: '#22c55e',
  location: '#ef4444',
  date: '#f59e0b',
  money: '#a855f7',
  'communication platform': '#06b6d4',
  email: '#ec4899',
  phone: '#14b8a6',
  'ic number': '#f97316',
};

export const ENTITY_LABELS: string[] = [
  'person',
  'organization',
  'location',
  'date',
  'money',
  'communication platform',
  'email',
  'phone',
  'ic number',
];

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

export interface LinkedEntity {
  entity_id: string;
  text: string;
  label: string;
  score: number;
  document_count: number;
  document_ids: string[];
  document_names: Record<string, string>;
}
