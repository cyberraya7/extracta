import axios from 'axios';
import type {
  UploadResult,
  ProcessRequest,
  ProcessResponse,
  Entity,
  GraphData,
  EvidenceResult,
  LinkedEntity,
  AnalysisSession,
  SessionDetail,
} from '../types';

const client = axios.create({
  baseURL: '/api',
  timeout: 300_000,
});

export async function uploadFiles(files: File[]): Promise<UploadResult[]> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  const { data } = await client.post<UploadResult[]>('/upload', form);
  return data;
}

export async function processDocuments(
  req: ProcessRequest
): Promise<ProcessResponse> {
  const { data } = await client.post<ProcessResponse>('/process', req);
  return data;
}

export async function getEntities(params?: {
  type?: string;
  min_confidence?: number;
  search?: string;
}): Promise<Entity[]> {
  const { data } = await client.get<Entity[]>('/entities', { params });
  return data;
}

export async function getGraph(type?: string): Promise<GraphData> {
  const { data } = await client.get<GraphData>('/graph', {
    params: type ? { type } : {},
  });
  return data;
}

export async function getEntityEvidence(
  entityId: string
): Promise<EvidenceResult> {
  const { data } = await client.get<EvidenceResult>(`/evidence/${entityId}`);
  return data;
}

export async function getEdgeEvidence(
  source: string,
  target: string
): Promise<EvidenceResult> {
  const { data } = await client.get<EvidenceResult>(
    `/evidence/edge/${source}/${target}`
  );
  return data;
}

export async function getLinkedEntities(): Promise<LinkedEntity[]> {
  const { data } = await client.get<LinkedEntity[]>('/entities/linked');
  return data;
}

export async function listDocuments(): Promise<UploadResult[]> {
  const { data } = await client.get<UploadResult[]>('/documents');
  return data;
}

export async function deleteDocument(documentId: string): Promise<void> {
  await client.delete(`/documents/${documentId}`);
}

export async function getSessions(): Promise<AnalysisSession[]> {
  const { data } = await client.get<AnalysisSession[]>('/sessions');
  return data;
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  const { data } = await client.get<SessionDetail>(`/sessions/${sessionId}`);
  return data;
}

export async function loadSession(sessionId: string): Promise<SessionDetail> {
  const { data } = await client.post<{ status: string; session: SessionDetail }>(
    `/sessions/${sessionId}/load`
  );
  return data.session;
}

export async function renameSession(sessionId: string, name: string): Promise<void> {
  await client.patch(`/sessions/${sessionId}`, { name });
}

export async function deleteSession(sessionId: string): Promise<void> {
  await client.delete(`/sessions/${sessionId}`);
}

export function getExportUrl(format: 'json' | 'csv'): string {
  return `/api/export/${format}`;
}
