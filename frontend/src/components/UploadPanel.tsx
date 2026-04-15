import { useCallback, useState, useRef } from 'react';
import { Upload, FileText, X } from 'lucide-react';

interface UploadPanelProps {
  onUpload: (files: File[]) => void;
}

const ACCEPTED = '.pdf,.docx,.txt,.csv,.mp3,.wav,.m4a,.mp4,.webm,.mkv';

export function UploadPanel({ onUpload }: UploadPanelProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((incoming: FileList | File[]) => {
    const arr = Array.from(incoming);
    setFiles((prev) => [...prev, ...arr]);
  }, []);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleSubmit = useCallback(() => {
    if (files.length > 0) onUpload(files);
  }, [files, onUpload]);

  return (
    <div className="flex flex-col items-center justify-center h-full gap-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold mb-2">Upload Documents</h2>
        <p className="text-slate-400">
          Drag & drop documents, audio, or video files for intelligence analysis
        </p>
      </div>

      <div
        className={`w-full max-w-2xl border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-colors ${
          dragging
            ? 'border-blue-400 bg-blue-400/10'
            : 'border-slate-700 hover:border-slate-500 bg-slate-900/50'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="w-12 h-12 mx-auto mb-4 text-slate-500" />
        <p className="text-lg text-slate-300 mb-1">
          Drop files here or click to browse
        </p>
        <p className="text-sm text-slate-500">PDF, DOCX, TXT, CSV, MP3, WAV, M4A, MP4, WEBM, MKV</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          multiple
          className="hidden"
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <div className="w-full max-w-2xl space-y-2">
          {files.map((f, i) => (
            <div
              key={`${f.name}-${i}`}
              className="flex items-center gap-3 bg-slate-800 rounded-xl px-4 py-3"
            >
              <FileText className="w-5 h-5 text-blue-400 shrink-0" />
              <span className="flex-1 truncate text-sm">{f.name}</span>
              <span className="text-xs text-slate-500">
                {(f.size / 1024).toFixed(1)} KB
              </span>
              <button
                onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                className="text-slate-500 hover:text-red-400 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
          <button
            onClick={handleSubmit}
            className="w-full mt-4 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-semibold transition-colors"
          >
            Process {files.length} file{files.length > 1 ? 's' : ''}
          </button>
        </div>
      )}
    </div>
  );
}
