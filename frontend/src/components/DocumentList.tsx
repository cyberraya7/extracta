import { FileText, Trash2, Plus, Upload, FolderOpen } from 'lucide-react';
import { useRef, useState, useCallback } from 'react';
import type { UploadResult } from '../types';

const ACCEPTED = '.pdf,.docx,.txt,.csv,.mp3,.wav,.m4a,.mp4,.webm,.mkv';
const SUPPORTED_EXTS = new Set(['.pdf','.docx','.txt','.csv','.mp3','.wav','.m4a','.mp4','.webm','.mkv']);

function filterSupported(files: FileList | File[]): File[] {
  return Array.from(files).filter((f) => {
    const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase();
    return SUPPORTED_EXTS.has(ext);
  });
}

interface DocumentListProps {
  documents: UploadResult[];
  onAddFiles: (files: File[]) => void;
  onDeleteDocument: (documentId: string) => void;
  isProcessing: boolean;
}

export function DocumentList({
  documents,
  onAddFiles,
  onDeleteDocument,
  isProcessing,
}: DocumentListProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = useCallback(
    (fileList: FileList) => {
      const supported = filterSupported(fileList);
      if (supported.length > 0) onAddFiles(supported);
    },
    [onAddFiles]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-400" />
          <h3 className="font-semibold text-sm text-slate-300">
            Documents ({documents.length})
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => folderInputRef.current?.click()}
            disabled={isProcessing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-xs font-medium transition-colors"
          >
            <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
            Add Folder
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isProcessing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-xs font-medium transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Files
          </button>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED}
          multiple
          className="hidden"
          onChange={(e) => { if (e.target.files) handleFiles(e.target.files); e.target.value = ''; }}
        />
        <input
          ref={folderInputRef}
          type="file"
          className="hidden"
          {...{ webkitdirectory: '', directory: '' } as any}
          multiple
          onChange={(e) => { if (e.target.files) handleFiles(e.target.files); e.target.value = ''; }}
        />
      </div>

      {documents.length === 0 ? (
        <div
          className={`p-6 text-center transition-colors ${
            dragging ? 'bg-blue-400/10' : ''
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
        >
          <Upload className="w-8 h-8 mx-auto mb-2 text-slate-600" />
          <p className="text-sm text-slate-500">Drop files or folders here</p>
        </div>
      ) : (
        <div
          className={`divide-y divide-slate-800/50 max-h-48 overflow-y-auto ${
            dragging ? 'bg-blue-400/5' : ''
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
        >
          {documents.map((doc, index) => (
            <div
              key={doc.document_id}
              className="flex items-center gap-3 px-4 py-2.5 hover:bg-slate-800/50 transition-colors group"
            >
              <span className="w-6 text-xs text-slate-600 tabular-nums text-right shrink-0">
                {index + 1}.
              </span>
              <FileText className="w-4 h-4 text-slate-500 shrink-0" />
              <span className="flex-1 text-sm truncate" title={doc.filename}>
                {doc.filename}
              </span>
              <span className="text-xs text-slate-600 shrink-0">
                {(doc.size / 1024).toFixed(0)} KB
              </span>
              <button
                onClick={() => onDeleteDocument(doc.document_id)}
                disabled={isProcessing}
                className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 disabled:opacity-50 transition-all shrink-0"
                title="Delete document"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
