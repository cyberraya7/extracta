import { Link2, FileText } from 'lucide-react';
import type { LinkedEntity } from '../types';
import { ENTITY_COLORS } from '../types';

interface LinkedEntitiesPanelProps {
  linkedEntities: LinkedEntity[];
  onSelectEntity: (entityId: string) => void;
}

export function LinkedEntitiesPanel({
  linkedEntities,
  onSelectEntity,
}: LinkedEntitiesPanelProps) {
  if (linkedEntities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-500">
        <Link2 className="w-12 h-12" />
        <p className="text-sm text-center px-4">
          No linked entities found. Upload multiple documents to see entities shared across them.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 h-full flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 shrink-0 flex items-center gap-2">
        <Link2 className="w-4 h-4 text-blue-400" />
        <h3 className="font-semibold text-sm text-slate-300">
          Cross-Document Entities ({linkedEntities.length})
        </h3>
      </div>
      <div className="flex-1 overflow-y-auto divide-y divide-slate-800/50">
        {linkedEntities.map((linked) => (
          <button
            key={linked.entity_id}
            onClick={() => onSelectEntity(linked.entity_id)}
            className="w-full text-left px-4 py-3 hover:bg-slate-800/50 transition-colors"
          >
            <div className="flex items-center gap-2 mb-1.5">
              <span
                className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium capitalize"
                style={{
                  backgroundColor: `${ENTITY_COLORS[linked.label] || '#64748b'}20`,
                  color: ENTITY_COLORS[linked.label] || '#64748b',
                }}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: ENTITY_COLORS[linked.label] || '#64748b' }}
                />
                {linked.label}
              </span>
              <span className="font-medium text-sm text-slate-100 truncate">
                {linked.text}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <FileText className="w-3 h-3" />
              <span>
                Found in {linked.document_count} document{linked.document_count > 1 ? 's' : ''}:
              </span>
            </div>
            <div className="flex flex-wrap gap-1 mt-1.5">
              {Object.entries(linked.document_names).map(([docId, docName]) => (
                <span
                  key={docId}
                  className="inline-block px-2 py-0.5 bg-slate-800 rounded text-xs text-slate-300 truncate max-w-48"
                >
                  {docName}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
