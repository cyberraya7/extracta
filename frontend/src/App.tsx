import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { Layout } from './components/Layout';
import { UploadPanel } from './components/UploadPanel';
import { ProcessingStatus } from './components/ProcessingStatus';
import { EntityTable } from './components/EntityTable';
import { GraphVisualization } from './components/GraphVisualization';
import { EvidencePanel } from './components/EvidencePanel';
import { Sidebar } from './components/Sidebar';
import { TimelineView } from './components/TimelineView';
import { LinkedEntitiesPanel } from './components/LinkedEntitiesPanel';
import { FacesPanel } from './components/FacesPanel';
import { DocumentList } from './components/DocumentList';
import { MindmapPanel } from './components/MindmapPanel';
import { ExifMetadataPanel } from './components/ExifMetadataPanel';
import { TableProperties, GitGraph, Link2, UserRoundSearch, Camera } from 'lucide-react';
import {
  uploadFilesBatched,
  processDocuments,
  getProcessStatus,
  getEntities,
  getGraph,
  getEntityEvidence,
  getEntityInvestigation,
  runEntityInvestigation,
  getEdgeEvidence,
  getLinkedEntities,
  getFaces,
  getLinkedFaces,
  updateFaceClusterName,
  deleteDocument as apiDeleteDocument,
  loadSession as apiLoadSession,
} from './services/api';
import type {
  UploadResult,
  Entity,
  GraphData,
  EvidenceSnippet,
  InvestigationResult,
  InvestigationSource,
  LinkedEntity,
  FaceInstance,
  FaceCluster,
} from './types';

type AppStage = 'upload' | 'uploading' | 'processing' | 'results';
type ResultsTab = 'dashboard' | 'graph' | 'mindmap' | 'linked' | 'exif' | 'faces';

interface ProgressInfo {
  stage: 'uploading' | 'processing' | 'finalizing';
  progress: number;
  total: number;
  currentFile: string;
  warnings: string[];
  documentsWithNoText: number;
  documentsSkippedForExtraction: number;
}

export default function App() {
  const [stage, setStage] = useState<AppStage>('upload');
  const [activeTab, setActiveTab] = useState<ResultsTab>('dashboard');
  const [documents, setDocuments] = useState<UploadResult[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [evidenceSnippets, setEvidenceSnippets] = useState<EvidenceSnippet[]>([]);
  const [linkedEntities, setLinkedEntities] = useState<LinkedEntity[]>([]);
  const [allFaces, setAllFaces] = useState<FaceInstance[]>([]);
  const [linkedFaces, setLinkedFaces] = useState<FaceCluster[]>([]);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<{ source: string; target: string } | null>(null);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
  const [progressInfo, setProgressInfo] = useState<ProgressInfo | null>(null);
  const [analysisWarnings, setAnalysisWarnings] = useState<string[]>([]);
  const [investigationResult, setInvestigationResult] = useState<InvestigationResult | null>(null);
  const [investigationLoading, setInvestigationLoading] = useState(false);
  const [investigationSource, setInvestigationSource] = useState<InvestigationSource>('tools');
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [confidenceThreshold, setConfidenceThreshold] = useState(0.3);
  /** Empty = all entity types; otherwise show only these labels (multi-select). */
  const [typeFilters, setTypeFilters] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const fetchLinked = useCallback(async () => {
    try {
      const linked = await getLinkedEntities();
      setLinkedEntities(linked);
    } catch {
      setLinkedEntities([]);
    }
  }, []);

  const fetchFaces = useCallback(async () => {
    try {
      const faces = await getFaces();
      setAllFaces(faces);
    } catch {
      setAllFaces([]);
    }
  }, []);

  const fetchLinkedFaces = useCallback(async () => {
    try {
      const clusters = await getLinkedFaces();
      setLinkedFaces(clusters);
    } catch {
      setLinkedFaces([]);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'linked' && stage === 'results') {
      fetchLinked();
    }
  }, [activeTab, stage, fetchLinked]);

  useEffect(() => {
    if (activeTab === 'faces' && stage === 'results') {
      fetchFaces();
      fetchLinkedFaces();
    }
  }, [activeTab, stage, fetchFaces, fetchLinkedFaces]);

  const clearViewState = useCallback(() => {
    setEvidenceSnippets([]);
    setInvestigationResult(null);
    setInvestigationSource('tools');
    setSelectedEntityId(null);
    setSelectedEdge(null);
    setProcessingError(null);
    setProgressInfo(null);
    setAnalysisWarnings([]);
  }, []);

  const pollUntilDone = useCallback((sessionId: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await getProcessStatus(sessionId);

          if (status.status === 'completed') {
            stopPolling();
            setAnalysisWarnings(status.warnings || []);
            setProgressInfo(null);
            resolve();
          } else if (status.status === 'error') {
            stopPolling();
            setAnalysisWarnings(status.warnings || []);
            setProgressInfo(null);
            reject(new Error(status.error || 'Processing failed'));
          } else {
            setProgressInfo({
              stage:
                status.status === 'finalizing'
                  ? 'finalizing'
                  : status.status === 'investigating'
                    ? 'processing'
                    : 'processing',
              progress: status.progress,
              total: status.total,
              currentFile: status.current_file,
              warnings: status.warnings || [],
              documentsWithNoText: status.documents_with_no_text || 0,
              documentsSkippedForExtraction: status.documents_skipped_for_extraction || 0,
            });
          }
        } catch {
          stopPolling();
          reject(new Error('Lost connection to server'));
        }
      };

      poll();
      pollingRef.current = setInterval(poll, 2000);
    });
  }, [stopPolling]);

  const runProcessing = useCallback(async (docIds: string[]) => {
    setStage('processing');
    clearViewState();
    setProgressInfo({
      stage: 'processing',
      progress: 0,
      total: docIds.length,
      currentFile: 'Starting...',
      warnings: [],
      documentsWithNoText: 0,
      documentsSkippedForExtraction: 0,
    });

    try {
      const result = await processDocuments({
        document_ids: docIds,
        confidence_threshold: confidenceThreshold,
      });

      const sessionId = result.session_id!;
      setCurrentSessionId(sessionId);

      await pollUntilDone(sessionId);

      const [ents, graph, linked] = await Promise.all([
        getEntities(),
        getGraph(),
        getLinkedEntities(),
      ]);
      setEntities(ents);
      setGraphData(graph);
      setLinkedEntities(linked);
      await fetchFaces();
      await fetchLinkedFaces();
      setStage('results');
      setHistoryRefreshKey((k) => k + 1);
    } catch (err: any) {
      setProcessingError(err?.message || 'Processing failed');
      setStage('results');
    }
  }, [confidenceThreshold, clearViewState, pollUntilDone, fetchFaces, fetchLinkedFaces]);

  const handleUpload = useCallback(async (files: File[]) => {
    try {
      setStage('uploading');
      setProgressInfo({
        stage: 'uploading',
        progress: 0,
        total: files.length,
        currentFile: '',
        warnings: [],
        documentsWithNoText: 0,
        documentsSkippedForExtraction: 0,
      });

      const results = await uploadFilesBatched(files, (uploaded, total) => {
        setProgressInfo({
          stage: 'uploading',
          progress: uploaded,
          total,
          currentFile: '',
          warnings: [],
          documentsWithNoText: 0,
          documentsSkippedForExtraction: 0,
        });
      });
      const uploadWarnings = results
        .filter((r) => (r.extraction_status || 'ok') !== 'ok')
        .map((r) => `${r.filename}: ${r.extraction_message || r.extraction_status}`);
      setAnalysisWarnings(uploadWarnings);

      const allDocs = [...documents, ...results];
      setDocuments(allDocs);
      await runProcessing(allDocs.map((d) => d.document_id));
      setActiveTab('dashboard');
    } catch (err: any) {
      setProcessingError(err?.response?.data?.detail || err.message || 'Upload failed');
      if (documents.length === 0) setStage('upload');
      else setStage('results');
    }
  }, [documents, runProcessing]);

  const handleAddFiles = useCallback(async (files: File[]) => {
    try {
      setStage('uploading');
      setProgressInfo({
        stage: 'uploading',
        progress: 0,
        total: files.length,
        currentFile: '',
        warnings: [],
        documentsWithNoText: 0,
        documentsSkippedForExtraction: 0,
      });

      const results = await uploadFilesBatched(files, (uploaded, total) => {
        setProgressInfo({
          stage: 'uploading',
          progress: uploaded,
          total,
          currentFile: '',
          warnings: [],
          documentsWithNoText: 0,
          documentsSkippedForExtraction: 0,
        });
      });
      const uploadWarnings = results
        .filter((r) => (r.extraction_status || 'ok') !== 'ok')
        .map((r) => `${r.filename}: ${r.extraction_message || r.extraction_status}`);
      setAnalysisWarnings(uploadWarnings);

      const allDocs = [...documents, ...results];
      setDocuments(allDocs);
      await runProcessing(allDocs.map((d) => d.document_id));
    } catch (err: any) {
      setProcessingError(err?.response?.data?.detail || err.message || 'Upload failed');
      setStage('results');
    }
  }, [documents, runProcessing]);

  const handleDeleteDocument = useCallback(async (documentId: string) => {
    try {
      await apiDeleteDocument(documentId);
      const remaining = documents.filter((d) => d.document_id !== documentId);
      setDocuments(remaining);

      if (remaining.length === 0) {
        setStage('upload');
        setEntities([]);
        setGraphData({ nodes: [], edges: [] });
        setEvidenceSnippets([]);
        setLinkedEntities([]);
        setAllFaces([]);
        setLinkedFaces([]);
        setSelectedEntityId(null);
        setSelectedEdge(null);
        setProcessingError(null);
        setAnalysisWarnings([]);
        setCurrentSessionId(null);
        return;
      }

      await runProcessing(remaining.map((d) => d.document_id));
    } catch (err: any) {
      setProcessingError(err?.response?.data?.detail || err.message || 'Delete failed');
    }
  }, [documents, runProcessing]);

  const handleLoadSession = useCallback(async (sessionId: string) => {
    try {
      const detail = await apiLoadSession(sessionId);
      setCurrentSessionId(sessionId);
      setDocuments(detail.documents || []);

      const [ents, graph, linked] = await Promise.all([
        getEntities(),
        getGraph(),
        getLinkedEntities(),
      ]);
      setEntities(ents);
      setGraphData(graph);
      setLinkedEntities(linked);
      await fetchFaces();
      await fetchLinkedFaces();
      clearViewState();
      setStage('results');
      setActiveTab('dashboard');
    } catch (err: any) {
      setProcessingError(err?.response?.data?.detail || err.message || 'Failed to load session');
    }
  }, [clearViewState, fetchFaces, fetchLinkedFaces]);

  const handleSelectEntity = useCallback(async (entityId: string) => {
    setSelectedEntityId(entityId);
    setSelectedEdge(null);
    setInvestigationResult(null);
    setInvestigationLoading(false);
    setInvestigationSource('tools');
    try {
      const evidenceResult = await getEntityEvidence(entityId);
      setEvidenceSnippets(evidenceResult.snippets);
    } catch {
      setEvidenceSnippets([]);
      setInvestigationResult(null);
    }
  }, []);

  const handleSelectEdge = useCallback(async (source: string, target: string) => {
    setSelectedEdge({ source, target });
    setSelectedEntityId(null);
    setInvestigationResult(null);
    setInvestigationLoading(false);
    try {
      const result = await getEdgeEvidence(source, target);
      setEvidenceSnippets(result.snippets);
    } catch {
      setEvidenceSnippets([]);
    }
  }, []);

  const handleCloseEvidence = useCallback(() => {
    setSelectedEntityId(null);
    setSelectedEdge(null);
    setEvidenceSnippets([]);
    setInvestigationResult(null);
    setInvestigationLoading(false);
  }, []);

  useEffect(() => {
    if (!selectedEntityId || stage !== 'results') return;
    const ent = entities.find((e) => e.id === selectedEntityId);
    if (!ent || !['email', 'phone', 'username'].includes(ent.label)) {
      return;
    }
    let cancelled = false;
    const variant = investigationSource === 'tools' ? 'tools' : 'instagram_leak';
    getEntityInvestigation(selectedEntityId, variant)
      .then((inv) => {
        if (!cancelled) {
          setInvestigationResult(inv.status === 'not_requested' ? null : inv);
        }
      })
      .catch(() => {
        if (!cancelled) setInvestigationResult(null);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedEntityId, investigationSource, entities, stage]);

  const handleInvestigateEntity = useCallback(async () => {
    if (!selectedEntityId) return;
    setInvestigationLoading(true);
    try {
      const result = await runEntityInvestigation(selectedEntityId, {
        source: investigationSource,
      });
      setInvestigationResult(result);
    } catch (err: any) {
      setInvestigationResult({
        entity_id: selectedEntityId,
        status: 'failed',
        summary: '',
        findings: [],
        notes: [err?.response?.data?.detail || err?.message || 'Investigation failed.'],
      });
    } finally {
      setInvestigationLoading(false);
    }
  }, [selectedEntityId, investigationSource]);

  const handleReprocess = useCallback(async () => {
    if (documents.length === 0) return;
    await runProcessing(documents.map((d) => d.document_id));
  }, [documents, runProcessing]);

  const handleReset = useCallback(() => {
    stopPolling();
    setStage('upload');
    setActiveTab('dashboard');
    setDocuments([]);
    setEntities([]);
    setGraphData({ nodes: [], edges: [] });
    setEvidenceSnippets([]);
    setLinkedEntities([]);
    setAllFaces([]);
    setLinkedFaces([]);
    setSelectedEntityId(null);
    setSelectedEdge(null);
    setProcessingError(null);
    setCurrentSessionId(null);
    setProgressInfo(null);
    setAnalysisWarnings([]);
    setTypeFilters([]);
    setSearchQuery('');
  }, [stopPolling]);

  const handleUpdateFaceClusterName = useCallback(
    async (clusterId: string, displayName: string) => {
      await updateFaceClusterName(clusterId, displayName);
      setLinkedFaces((prev) =>
        prev.map((cluster) =>
          cluster.cluster_id === clusterId
            ? { ...cluster, display_name: displayName.trim() || null }
            : cluster
        )
      );
    },
    [],
  );

  const filteredEntities = entities.filter((e) => {
    if (typeFilters.length > 0 && !typeFilters.includes(e.label)) return false;
    if (e.score < confidenceThreshold) return false;
    if (searchQuery && !e.text.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const filteredLinkedEntities = useMemo(
    () =>
      linkedEntities.filter((e) => {
        if (typeFilters.length > 0 && !typeFilters.includes(e.label)) return false;
        if (e.score < confidenceThreshold) return false;
        if (searchQuery && !e.text.toLowerCase().includes(searchQuery.toLowerCase())) return false;
        return true;
      }),
    [linkedEntities, typeFilters, confidenceThreshold, searchQuery],
  );

  const showEvidence = selectedEntityId !== null || selectedEdge !== null;
  const isProcessing = stage === 'processing' || stage === 'uploading';
  const selectedEntityLabel = selectedEntityId
    ? entities.find((e) => e.id === selectedEntityId)?.label ?? null
    : null;
  const canInvestigateSelectedEntity = !!selectedEntityLabel
    && ['email', 'phone', 'username'].includes(selectedEntityLabel);

  const tabs: { id: ResultsTab; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <TableProperties className="w-4 h-4" /> },
    { id: 'graph', label: 'Graph', icon: <GitGraph className="w-4 h-4" /> },
    { id: 'mindmap', label: 'Mindmap', icon: <GitGraph className="w-4 h-4" /> },
    { id: 'linked', label: 'Linked', icon: <Link2 className="w-4 h-4" /> },
    { id: 'exif', label: 'Metadata', icon: <Camera className="w-4 h-4" /> },
    { id: 'faces', label: 'Faces', icon: <UserRoundSearch className="w-4 h-4" /> },
  ];

  return (
    <Layout
      sidebar={
        <Sidebar
          confidenceThreshold={confidenceThreshold}
          onConfidenceChange={setConfidenceThreshold}
          typeFilters={typeFilters}
          onTypeFiltersChange={setTypeFilters}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          hasResults={stage === 'results' && entities.length > 0}
          onReprocess={handleReprocess}
          onReset={handleReset}
          currentSessionId={currentSessionId}
          onLoadSession={handleLoadSession}
          historyRefreshKey={historyRefreshKey}
        />
      }
      evidence={
        showEvidence ? (
          <EvidencePanel
            snippets={evidenceSnippets}
            investigation={investigationResult}
            investigationLoading={investigationLoading}
            canInvestigate={canInvestigateSelectedEntity}
            investigationSource={investigationSource}
            onInvestigationSourceChange={setInvestigationSource}
            entityId={selectedEntityId}
            edge={selectedEdge}
            onInvestigate={handleInvestigateEntity}
            onClose={handleCloseEvidence}
          />
        ) : null
      }
    >
      {stage === 'upload' && <UploadPanel onUpload={handleUpload} />}
      {(stage === 'uploading' || stage === 'processing') && (
        <ProcessingStatus
          stage={progressInfo?.stage ?? 'processing'}
          progress={progressInfo?.progress ?? 0}
          total={progressInfo?.total ?? 0}
          currentFile={progressInfo?.currentFile ?? ''}
          warnings={progressInfo?.warnings ?? []}
          documentsWithNoText={progressInfo?.documentsWithNoText ?? 0}
          documentsSkippedForExtraction={progressInfo?.documentsSkippedForExtraction ?? 0}
        />
      )}
      {stage === 'results' && (
        <div className="flex flex-col h-full gap-4">
          {processingError && (
            <div className="bg-red-900/40 border border-red-700 rounded-xl p-4 text-red-200">
              {processingError}
            </div>
          )}
          {!processingError && analysisWarnings.length > 0 && (
            <div className="bg-amber-900/40 border border-amber-700 rounded-xl p-4 text-amber-200">
              <p className="font-medium mb-1">Some files had limited extraction</p>
              <ul className="text-sm list-disc pl-5 space-y-0.5">
                {analysisWarnings.slice(0, 5).map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}
          {!processingError && entities.length === 0 && documents.length > 0 && (
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 text-slate-300">
              <p className="font-medium mb-1">No extractable text found from selected files</p>
              <p className="text-sm text-slate-400">
                Check ffmpeg/whisper for WAV/MP4 and OCR dependencies for scanned PDFs/images,
                then reprocess.
              </p>
            </div>
          )}

          <DocumentList
            documents={documents}
            onAddFiles={handleAddFiles}
            onDeleteDocument={handleDeleteDocument}
            isProcessing={isProcessing}
          />

          <div className="flex items-center gap-1 bg-slate-900 rounded-xl p-1 self-start border border-slate-800">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'dashboard' && (
            <div className="flex flex-col gap-6 flex-1 min-h-0">
              <div className="flex-1 min-h-64">
                <EntityTable
                  entities={filteredEntities}
                  selectedId={selectedEntityId}
                  onSelect={handleSelectEntity}
                />
              </div>
              {entities.some((e) => e.label === 'date') && (
                <div className="h-48 shrink-0">
                  <TimelineView
                    entities={entities.filter((e) => e.label === 'date')}
                    onSelect={handleSelectEntity}
                  />
                </div>
              )}
            </div>
          )}

          {activeTab === 'graph' && (
            <div className="flex-1 min-h-0">
              <GraphVisualization
                data={graphData}
                selectedNodeId={selectedEntityId}
                onSelectNode={handleSelectEntity}
                onSelectEdge={handleSelectEdge}
                typeFilters={typeFilters}
                searchQuery={searchQuery}
                confidenceThreshold={confidenceThreshold}
              />
            </div>
          )}

          {activeTab === 'linked' && (
            <div className="flex-1 min-h-0">
              <LinkedEntitiesPanel
                linkedEntities={filteredLinkedEntities}
                totalLinkedBeforeFilter={linkedEntities.length}
                onSelectEntity={handleSelectEntity}
                documentCount={documents.length}
              />
            </div>
          )}

          {activeTab === 'exif' && (
            <div className="flex-1 min-h-0">
              <ExifMetadataPanel documents={documents} />
            </div>
          )}

          {activeTab === 'mindmap' && (
            <div className="flex-1 min-h-0">
              <MindmapPanel entities={filteredEntities} onSelectEntity={handleSelectEntity} />
            </div>
          )}

          {activeTab === 'faces' && (
            <div className="flex-1 min-h-0">
              <FacesPanel
                allFaces={allFaces}
                clusters={linkedFaces}
                documentNames={Object.fromEntries(documents.map((d) => [d.document_id, d.filename]))}
                onUpdateClusterName={handleUpdateFaceClusterName}
              />
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
