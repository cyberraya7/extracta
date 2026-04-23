import { useMemo, useState } from 'react';
import { Check, Pencil, X } from 'lucide-react';
import type { FaceCluster, FaceInstance } from '../types';

interface FacesPanelProps {
  allFaces: FaceInstance[];
  clusters: FaceCluster[];
  documentNames: Record<string, string>;
  onUpdateClusterName: (clusterId: string, displayName: string) => Promise<void>;
}

export function FacesPanel({
  allFaces,
  clusters,
  documentNames,
  onUpdateClusterName,
}: FacesPanelProps) {
  const [editingClusterId, setEditingClusterId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState('');
  const [savingClusterId, setSavingClusterId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const displayNamesByClusterId = useMemo(
    () =>
      new Map(
        clusters.map((cluster) => [
          cluster.cluster_id,
          cluster.display_name?.trim() ||
            cluster.suggested_name?.trim() ||
            `Cluster ${cluster.cluster_id}`,
        ]),
      ),
    [clusters],
  );

  const startEditing = (cluster: FaceCluster) => {
    setSaveError(null);
    setEditingClusterId(cluster.cluster_id);
    setDraftName(cluster.display_name ?? cluster.suggested_name ?? '');
  };

  const cancelEditing = () => {
    setEditingClusterId(null);
    setDraftName('');
    setSaveError(null);
  };

  const saveClusterName = async (clusterId: string) => {
    setSavingClusterId(clusterId);
    setSaveError(null);
    try {
      await onUpdateClusterName(clusterId, draftName);
      setEditingClusterId(null);
      setDraftName('');
    } catch (err: any) {
      setSaveError(err?.response?.data?.detail || err?.message || 'Failed to save cluster name');
    } finally {
      setSavingClusterId(null);
    }
  };

  if (allFaces.length === 0 && clusters.length === 0) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-800 h-full flex items-center justify-center text-slate-500 px-6 text-center">
        No faces found yet. Upload documents containing photos and run analysis again.
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 h-full overflow-auto divide-y divide-slate-800/50">
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">
            All Faces
          </h3>
          <span className="text-xs text-slate-400">
            {allFaces.length} detected
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {allFaces.map((face) => (
            <div
              key={face.id}
              className="w-24 h-24 bg-slate-800 rounded-lg border border-slate-700 overflow-hidden"
              title={`${documentNames[face.document_id] || face.document_id} • ${face.source_ref}`}
            >
              {face.thumbnail_path ? (
                <img src={`/api/faces/thumbnail/${encodeURIComponent(face.id)}`} alt={face.id} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-[10px] text-slate-500">
                  face
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">
            Linked Clusters
          </h3>
          <span className="text-xs text-slate-400">
            {clusters.length} cross-document
          </span>
        </div>

        {clusters.length === 0 ? (
          <p className="text-xs text-slate-500">
            No linked clusters yet. Upload multiple files with the same face to see cross-document matches.
          </p>
        ) : (
          <div className="space-y-4">
            {clusters.map((cluster) => (
              <div key={cluster.cluster_id} className="space-y-2">
                <div className="flex items-center justify-between">
                  {editingClusterId === cluster.cluster_id ? (
                    <div className="flex items-center gap-1.5">
                      <input
                        type="text"
                        value={draftName}
                        onChange={(e) => setDraftName(e.target.value)}
                        placeholder="Enter person name"
                        className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                      <button
                        onClick={() => saveClusterName(cluster.cluster_id)}
                        disabled={savingClusterId === cluster.cluster_id}
                        className="text-green-400 hover:text-green-300 disabled:opacity-50"
                        title="Save cluster name"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={cancelEditing}
                        disabled={savingClusterId === cluster.cluster_id}
                        className="text-slate-500 hover:text-slate-300 disabled:opacity-50"
                        title="Cancel"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-medium text-slate-300">
                        {displayNamesByClusterId.get(cluster.cluster_id)}
                      </p>
                      <button
                        onClick={() => startEditing(cluster)}
                        className="text-slate-500 hover:text-blue-400 transition-colors"
                        title="Rename cluster"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                  <span className="text-[11px] text-slate-500">
                    {cluster.face_count} faces in {cluster.document_count} documents
                  </span>
                </div>
                {saveError && editingClusterId === cluster.cluster_id && (
                  <p className="text-[11px] text-red-400">{saveError}</p>
                )}
                <div className="flex flex-wrap gap-2">
                  {cluster.faces.map((face) => (
                    <div
                      key={face.id}
                      className="w-20 h-20 bg-slate-800 rounded-lg border border-slate-700 overflow-hidden"
                      title={`${cluster.document_names[face.document_id] || face.document_id} • ${face.source_ref}`}
                    >
                      {face.thumbnail_path ? (
                        <img src={`/api/faces/thumbnail/${encodeURIComponent(face.id)}`} alt={face.id} className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-[10px] text-slate-500">
                          face
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
