import { X, FileText, Link2 } from 'lucide-react';
import type { EvidenceSnippet } from '../types';

interface EvidencePanelProps {
  snippets: EvidenceSnippet[];
  entityId: string | null;
  edge: { source: string; target: string } | null;
  onClose: () => void;
}

export function EvidencePanel({
  snippets,
  entityId,
  edge: _edge,
  onClose,
}: EvidencePanelProps) {
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {entityId ? (
            <FileText className="w-4 h-4 text-blue-400" />
          ) : (
            <Link2 className="w-4 h-4 text-green-400" />
          )}
          <h3 className="font-semibold text-sm">
            {entityId ? 'Entity Evidence' : 'Relationship Evidence'}
          </h3>
        </div>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-slate-300 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="text-xs text-slate-500">
        {snippets.length} source snippet{snippets.length !== 1 ? 's' : ''} found
      </div>

      <div className="space-y-3">
        {snippets.map((snippet, i) => (
          <div
            key={i}
            className="bg-slate-800/50 rounded-xl p-3 space-y-2 border border-slate-800"
          >
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <FileText className="w-3 h-3" />
              <span className="truncate">{snippet.document_name}</span>
            </div>
            <p className="text-sm text-slate-200 leading-relaxed">
              <HighlightedText
                text={snippet.text}
                highlights={
                  snippet.entity_text
                    ? [snippet.entity_text]
                    : snippet.entities || []
                }
              />
            </p>
          </div>
        ))}

        {snippets.length === 0 && (
          <div className="text-center text-slate-500 py-8 text-sm">
            No evidence snippets found
          </div>
        )}
      </div>
    </div>
  );
}

function HighlightedText({
  text,
  highlights,
}: {
  text: string;
  highlights: string[];
}) {
  if (highlights.length === 0) return <>{text}</>;

  const pattern = highlights
    .map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|');
  const regex = new RegExp(`(${pattern})`, 'gi');
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) => {
        const isHighlight = highlights.some(
          (h) => h.toLowerCase() === part.toLowerCase()
        );
        return isHighlight ? (
          <mark
            key={i}
            className="bg-yellow-500/30 text-yellow-200 rounded px-0.5"
          >
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        );
      })}
    </>
  );
}
