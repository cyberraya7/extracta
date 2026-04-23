import { useCallback, useState, useRef } from 'react';
import { Upload, FileText, FolderOpen, X } from 'lucide-react';

interface UploadPanelProps {
  onUpload: (files: File[]) => void;
}

const ACCEPTED = '.pdf,.docx,.txt,.csv,.jpg,.jpeg,.png,.mp3,.wav,.m4a,.mp4,.webm,.mkv';
const SUPPORTED_EXTS = new Set(['.pdf','.docx','.txt','.csv','.jpg','.jpeg','.png','.mp3','.wav','.m4a','.mp4','.webm','.mkv']);

function filterSupported(files: FileList | File[]): File[] {
  return Array.from(files).filter((f) => {
    const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase();
    return SUPPORTED_EXTS.has(ext);
  });
}

export function UploadPanel({ onUpload }: UploadPanelProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((incoming: FileList | File[]) => {
    const supported = filterSupported(incoming);
    if (supported.length > 0) {
      setFiles((prev) => [...prev, ...supported]);
    }
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
          Drag & drop files or folders for intelligence analysis
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
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload className="w-12 h-12 mx-auto mb-4 text-slate-500" />
        <p className="text-lg text-slate-300 mb-1">
          Drop files here or click to browse
        </p>
        <p className="text-sm text-slate-500">PDF, DOCX, TXT, CSV, JPG, JPEG, PNG, MP3, WAV, M4A, MP4, WEBM, MKV</p>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED}
          multiple
          className="hidden"
          onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = ''; }}
        />
      </div>

      <button
        onClick={(e) => { e.stopPropagation(); folderInputRef.current?.click(); }}
        className="flex items-center gap-2 px-5 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-sm font-medium transition-colors text-slate-300"
      >
        <FolderOpen className="w-4 h-4 text-amber-400" />
        Upload Folder
      </button>
      <input
        ref={folderInputRef}
        type="file"
        className="hidden"
        {...{ webkitdirectory: '', directory: '' } as any}
        multiple
        onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = ''; }}
      />

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
