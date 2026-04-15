import { useState, useCallback, useEffect } from 'react';
import { Layout } from './components/Layout';
import { UploadPanel } from './components/UploadPanel';
import { ProcessingStatus } from './components/ProcessingStatus';
import { EntityTable } from './components/EntityTable';
import { GraphVisualization } from './components/GraphVisualization';
import { EvidencePanel } from './components/EvidencePanel';
import { Sidebar } from './components/Sidebar';
import { TimelineView } from './components/TimelineView';
import { LinkedEntitiesPanel } from './components/LinkedEntitiesPanel';
import { DocumentList } from './components/DocumentList';
import { TableProperties, GitGraph, Link2 } from 'lucide-react';
import {
  uploadFiles,
  processDocuments,
  getEntities,
  getGraph,
  getEntityEvidence,
  getEdgeEvidence,
  getLinkedEntities,
  deleteDocument as apiDeleteDocument,
  loadSession as apiLoadSession,
} from './services/api';
import type {
  UploadResult,
  Entity,
  GraphData,
  EvidenceSnippet,
  LinkedEntity,
} from './types';

type AppStage = 'upload' | 'processing' | 'results';
type ResultsTab = 'dashboard' | 'graph' | 'linked';

export default function App() {
  const [stage, setStage] = useState<AppStage>('upload');
  const [activeTab, setActiveTab] = useState<ResultsTab>('dashboard');
  const [documents, setDocuments] = useState<UploadResult[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [evidenceSnippets, setEvidenceSnippets] = useState<EvidenceSnippet[]>([]);
  const [linkedEntities, setLinkedEntities] = useState<LinkedEntity[]>([]);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<{ source: string; target: string } | null>(null);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  const [confidenceThreshold, setConfidenceThreshold] = useState(0.3);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [labels, setLabels] = useState<string[]>([
    'person', 'organization', 'location', 'date', 'money', 'communication platform',
    'email', 'phone', 'ic number',
  ]);

  const fetchLinked = useCallback(async () => {
    try {
      const linked = await getLinkedEntities();
      setLinkedEntities(linked);
    } catch {
      setLinkedEntities([]);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'linked' && stage === 'results') {
      fetchLinked();
    }
  }, [activeTab, stage, fetchLinked]);

  const clearViewState = useCallback(() => {
    setEvidenceSnippets([]);
    setSelectedEntityId(null);
    setSelectedEdge(null);
    setProcessingError(null);
  }, []);

  const runProcessing = useCallback(async (docIds: string[]) => {
    setStage('processing');
    clearViewState();

    try {
      const result = await processDocuments({
        document_ids: docIds,
        labels,
        confidence_threshold: confidenceThreshold,
      });

      if (result.session_id) {
        setCurrentSessionId(result.session_id);
      }

      const [ents, graph] = await Promise.all([getEntities(), getGraph()]);
      setEntities(ents);
      setGraphData(graph);
      setLinkedEntities([]);
      setStage('results');
      setHistoryRefreshKey((k) => k + 1);
    } catch (err: any) {
      setProcessingError(err?.response?.data?.detail || err.message || 'Processing failed');
      setStage('results');
    }
  }, [labels, confidenceThreshold, clearViewState]);

  const handleUpload = useCallback(async (files: File[]) => {
    try {
      const results = await uploadFiles(files);
      const allDocs = [...documents, ...results];
      setDocuments(allDocs);
      await runProcessing(allDocs.map((d) => d.document_id));
      setActiveTab('dashboard');
    } catch (err: any) {
      setProcessingError(err?.response?.data?.detail || err.message || 'Upload failed');
      if (stage === 'upload') setStage('results');
    }
  }, [documents, runProcessing, stage]);

  const handleAddFiles = useCallback(async (files: File[]) => {
    try {
      const results = await uploadFiles(files);
      const allDocs = [...documents, ...results];
      setDocuments(allDocs);
      await runProcessing(allDocs.map((d) => d.document_id));
    } catch (err: any) {
      setProcessingError(err?.response?.data?.detail || err.message || 'Upload failed');
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
        setSelectedEntityId(null);
        setSelectedEdge(null);
        setProcessingError(null);
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

      const [ents, graph] = await Promise.all([getEntities(), getGraph()]);
      setEntities(ents);
      setGraphData(graph);
      setLinkedEntities([]);
      clearViewState();
      setStage('results');
      setActiveTab('dashboard');
    } catch (err: any) {
      setProcessingError(err?.response?.data?.detail || err.message || 'Failed to load session');
    }
  }, [clearViewState]);

  const handleSelectEntity = useCallback(async (entityId: string) => {
    setSelectedEntityId(entityId);
    setSelectedEdge(null);
    try {
      const result = await getEntityEvidence(entityId);
      setEvidenceSnippets(result.snippets);
    } catch {
      setEvidenceSnippets([]);
    }
  }, []);

  const handleSelectEdge = useCallback(async (source: string, target: string) => {
    setSelectedEdge({ source, target });
    setSelectedEntityId(null);
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
  }, []);

  const handleReprocess = useCallback(async () => {
    if (documents.length === 0) return;
    await runProcessing(documents.map((d) => d.document_id));
  }, [documents, runProcessing]);

  const handleReset = useCallback(() => {
    setStage('upload');
    setActiveTab('dashboard');
    setDocuments([]);
    setEntities([]);
    setGraphData({ nodes: [], edges: [] });
    setEvidenceSnippets([]);
    setLinkedEntities([]);
    setSelectedEntityId(null);
    setSelectedEdge(null);
    setProcessingError(null);
    setCurrentSessionId(null);
  }, []);

  const filteredEntities = entities.filter((e) => {
    if (typeFilter && e.label !== typeFilter) return false;
    if (e.score < confidenceThreshold) return false;
    if (searchQuery && !e.text.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const showEvidence = selectedEntityId !== null || selectedEdge !== null;
  const isProcessing = stage === 'processing';

  const tabs: { id: ResultsTab; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <TableProperties className="w-4 h-4" /> },
    { id: 'graph', label: 'Graph', icon: <GitGraph className="w-4 h-4" /> },
    { id: 'linked', label: 'Linked', icon: <Link2 className="w-4 h-4" /> },
  ];

  return (
    <Layout
      sidebar={
        <Sidebar
          labels={labels}
          onLabelsChange={setLabels}
          confidenceThreshold={confidenceThreshold}
          onConfidenceChange={setConfidenceThreshold}
          typeFilter={typeFilter}
          onTypeFilterChange={setTypeFilter}
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
            entityId={selectedEntityId}
            edge={selectedEdge}
            onClose={handleCloseEvidence}
          />
        ) : null
      }
    >
      {stage === 'upload' && <UploadPanel onUpload={handleUpload} />}
      {stage === 'processing' && <ProcessingStatus />}
      {stage === 'results' && (
        <div className="flex flex-col h-full gap-4">
          {processingError && (
            <div className="bg-red-900/40 border border-red-700 rounded-xl p-4 text-red-200">
              {processingError}
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
              />
            </div>
          )}

          {activeTab === 'linked' && (
            <div className="flex-1 min-h-0">
              <LinkedEntitiesPanel
                linkedEntities={linkedEntities}
                onSelectEntity={handleSelectEntity}
              />
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
