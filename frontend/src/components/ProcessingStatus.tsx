import { Loader2, Upload, Cpu, Sparkles } from 'lucide-react';

interface ProcessingStatusProps {
  stage: 'uploading' | 'processing' | 'finalizing';
  progress: number;
  total: number;
  currentFile: string;
}

const STAGE_CONFIG = {
  uploading: {
    icon: Upload,
    title: 'Uploading Files',
    description: 'Sending files to server and extracting text...',
    color: 'bg-blue-500',
  },
  processing: {
    icon: Cpu,
    title: 'Analyzing Documents',
    description: 'Running entity extraction on each document...',
    color: 'bg-blue-500',
  },
  finalizing: {
    icon: Sparkles,
    title: 'Finalizing',
    description: 'Building relationship graph and mapping evidence...',
    color: 'bg-emerald-500',
  },
};

export function ProcessingStatus({ stage, progress, total, currentFile }: ProcessingStatusProps) {
  const config = STAGE_CONFIG[stage];
  const Icon = config.icon;
  const pct = total > 0 ? Math.round((progress / total) * 100) : 0;

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6">
      <div className="relative">
        <Icon className="w-14 h-14 text-blue-400" />
        <Loader2 className="w-6 h-6 text-blue-300 animate-spin absolute -bottom-1 -right-1" />
      </div>

      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">{config.title}</h2>
        <p className="text-slate-400 text-sm">{config.description}</p>
      </div>

      <div className="w-80 space-y-2">
        <div className="flex justify-between text-xs text-slate-400">
          <span>
            {progress} / {total} {stage === 'uploading' ? 'files' : 'documents'}
          </span>
          <span>{pct}%</span>
        </div>
        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${config.color}`}
            style={{ width: `${Math.max(pct, stage === 'finalizing' ? 100 : 2)}%` }}
          />
        </div>
        {currentFile && (
          <p className="text-xs text-slate-500 truncate text-center" title={currentFile}>
            {currentFile}
          </p>
        )}
      </div>
    </div>
  );
}
