import axios from 'axios';
import type {
  UploadResult,
  ProcessRequest,
  ProcessResponse,
  ProcessStatus,
  Entity,
  GraphData,
  EvidenceResult,
  InvestigationResult,
  InvestigationRunRequest,
  LinkedEntity,
  FaceInstance,
  FaceCluster,
  AnalysisSession,
  SessionDetail,
  BulkSessionDeleteResponse,
} from '../types';

const client = axios.create({
  baseURL: '/api',
  timeout: 120_000,
});

function toUserError(err: any, fallback: string): Error {
  const code = err?.code as string | undefined;
  const detail = err?.response?.data?.detail as string | undefined;
  if (detail) return new Error(detail);
  if (code === 'ECONNABORTED') {
    return new Error(
      'Upload timed out. Large audio/video transcription can take longer; please retry or increase timeout.',
    );
  }
  if (!err?.response) {
    return new Error(
      'Connection lost during upload. The backend may have restarted while processing media files.',
    );
  }
  return new Error(err?.message || fallback);
}

export async function uploadFiles(files: File[]): Promise<UploadResult[]> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  try {
    const { data } = await client.post<UploadResult[]>('/upload', form, {
      timeout: 30 * 60_000,
    });
    return data;
  } catch (err: any) {
    throw toUserError(err, 'Upload failed');
  }
}

const BATCH_SIZE = 10;

export async function uploadFilesBatched(
  files: File[],
  onProgress?: (uploaded: number, total: number) => void,
): Promise<UploadResult[]> {
  const allResults: UploadResult[] = [];
  const total = files.length;

  for (let i = 0; i < total; i += BATCH_SIZE) {
    const batch = files.slice(i, i + BATCH_SIZE);
    const results = await uploadFiles(batch);
    allResults.push(...results);
    onProgress?.(Math.min(i + batch.length, total), total);
  }

  return allResults;
}

export async function processDocuments(
  req: ProcessRequest
): Promise<ProcessResponse> {
  const { data } = await client.post<ProcessResponse>('/process', req);
  return data;
}

export async function getProcessStatus(sessionId: string): Promise<ProcessStatus> {
  const { data } = await client.get<ProcessStatus>(`/process/status/${sessionId}`);
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

export async function getEntityInvestigation(
  entityId: string,
  variant?: string
): Promise<InvestigationResult> {
  const { data } = await client.get<InvestigationResult>(`/entities/${entityId}/investigation`, {
    params: variant ? { variant } : {},
  });
  return data;
}

export async function runEntityInvestigation(
  entityId: string,
  body?: InvestigationRunRequest
): Promise<InvestigationResult> {
  const { data } = await client.post<InvestigationResult>(
    `/entities/${entityId}/investigation/run`,
    body ?? { source: 'tools' }
  );
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

export async function getFaces(): Promise<FaceInstance[]> {
  const { data } = await client.get<FaceInstance[]>('/faces');
  return data;
}

export async function getSimilarFaces(faceId: string): Promise<FaceInstance[]> {
  const { data } = await client.get<FaceInstance[]>(`/faces/${faceId}/similar`);
  return data;
}

export async function getLinkedFaces(): Promise<FaceCluster[]> {
  const { data } = await client.get<FaceCluster[]>('/faces/linked');
  return data;
}

export async function updateFaceClusterName(
  clusterId: string,
  displayName: string,
): Promise<void> {
  await client.patch(`/faces/linked/${encodeURIComponent(clusterId)}/name`, {
    display_name: displayName,
  });
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

export async function deleteSessionsBulk(sessionIds: string[]): Promise<BulkSessionDeleteResponse> {
  const { data } = await client.post<BulkSessionDeleteResponse>('/sessions/delete-bulk', {
    session_ids: sessionIds,
  });
  return data;
}

export function getExportUrl(format: 'json' | 'csv'): string {
  return `/api/export/${format}`;
}
