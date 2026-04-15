import {
  Settings,
  Tag,
  SlidersHorizontal,
  Search,
  Download,
  RotateCcw,
  Trash2,
} from 'lucide-react';
import { ENTITY_LABELS, ENTITY_COLORS } from '../types';
import { getExportUrl } from '../services/api';
import { HistoryPanel } from './HistoryPanel';

interface SidebarProps {
  labels: string[];
  onLabelsChange: (labels: string[]) => void;
  confidenceThreshold: number;
  onConfidenceChange: (v: number) => void;
  typeFilter: string | null;
  onTypeFilterChange: (v: string | null) => void;
  searchQuery: string;
  onSearchChange: (v: string) => void;
  hasResults: boolean;
  onReprocess: () => void;
  onReset: () => void;
  currentSessionId: string | null;
  onLoadSession: (sessionId: string) => void;
  historyRefreshKey: number;
}

export function Sidebar({
  labels,
  onLabelsChange,
  confidenceThreshold,
  onConfidenceChange,
  typeFilter,
  onTypeFilterChange,
  searchQuery,
  onSearchChange,
  hasResults,
  onReprocess,
  onReset,
  currentSessionId,
  onLoadSession,
  historyRefreshKey,
}: SidebarProps) {
  const toggleLabel = (label: string) => {
    if (labels.includes(label)) {
      onLabelsChange(labels.filter((l) => l !== label));
    } else {
      onLabelsChange([...labels, label]);
    }
  };

  return (
    <div className="p-4 space-y-6 text-sm">
      <div>
        <div className="flex items-center gap-2 text-slate-400 mb-3 font-medium uppercase text-xs tracking-wider">
          <Settings className="w-3.5 h-3.5" />
          Model Settings
        </div>
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-slate-400 mb-2">
            <Tag className="w-3.5 h-3.5" />
            <span>Entity Labels</span>
          </div>
          {ENTITY_LABELS.map((label) => (
            <label
              key={label}
              className="flex items-center gap-2 cursor-pointer hover:bg-slate-800 rounded-lg px-2 py-1.5 transition-colors"
            >
              <input
                type="checkbox"
                checked={labels.includes(label)}
                onChange={() => toggleLabel(label)}
                className="rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: ENTITY_COLORS[label] }}
              />
              <span className="capitalize">{label}</span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center gap-2 text-slate-400 mb-3 font-medium uppercase text-xs tracking-wider">
          <SlidersHorizontal className="w-3.5 h-3.5" />
          Confidence
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={confidenceThreshold}
          onChange={(e) => onConfidenceChange(parseFloat(e.target.value))}
          className="w-full accent-blue-500"
        />
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          <span>0%</span>
          <span className="text-blue-400 font-medium">
            {Math.round(confidenceThreshold * 100)}%
          </span>
          <span>100%</span>
        </div>
      </div>

      <div>
        <div className="flex items-center gap-2 text-slate-400 mb-3 font-medium uppercase text-xs tracking-wider">
          <Search className="w-3.5 h-3.5" />
          Filter
        </div>
        <input
          type="text"
          placeholder="Search entities..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder:text-slate-600"
        />
        <div className="flex flex-wrap gap-1.5 mt-3">
          <button
            onClick={() => onTypeFilterChange(null)}
            className={`px-2.5 py-1 rounded-full text-xs transition-colors ${
              typeFilter === null
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            All
          </button>
          {ENTITY_LABELS.map((label) => (
            <button
              key={label}
              onClick={() =>
                onTypeFilterChange(typeFilter === label ? null : label)
              }
              className={`px-2.5 py-1 rounded-full text-xs transition-colors capitalize ${
                typeFilter === label
                  ? 'text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
              style={
                typeFilter === label
                  ? { backgroundColor: ENTITY_COLORS[label] }
                  : undefined
              }
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {hasResults && (
        <div className="space-y-2 pt-2 border-t border-slate-800">
          <div className="flex items-center gap-2 text-slate-400 mb-3 font-medium uppercase text-xs tracking-wider">
            <Download className="w-3.5 h-3.5" />
            Export
          </div>
          <a
            href={getExportUrl('json')}
            download
            className="flex items-center gap-2 w-full px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors text-slate-300"
          >
            <Download className="w-4 h-4" />
            Export JSON
          </a>
          <a
            href={getExportUrl('csv')}
            download
            className="flex items-center gap-2 w-full px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors text-slate-300"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </a>
          <button
            onClick={onReprocess}
            className="flex items-center gap-2 w-full px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors text-slate-300"
          >
            <RotateCcw className="w-4 h-4" />
            Reprocess
          </button>
          <button
            onClick={onReset}
            className="flex items-center gap-2 w-full px-3 py-2 bg-red-900/30 hover:bg-red-900/50 rounded-lg transition-colors text-red-400"
          >
            <Trash2 className="w-4 h-4" />
            New Analysis
          </button>
        </div>
      )}

      <HistoryPanel
        currentSessionId={currentSessionId}
        onLoadSession={onLoadSession}
        refreshKey={historyRefreshKey}
      />
    </div>
  );
}
