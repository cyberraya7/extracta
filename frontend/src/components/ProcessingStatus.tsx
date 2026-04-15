import { Loader2 } from 'lucide-react';

export function ProcessingStatus() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6">
      <Loader2 className="w-16 h-16 text-blue-400 animate-spin" />
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Analyzing Documents</h2>
        <p className="text-slate-400">
          Extracting entities, building relationships, and mapping evidence...
        </p>
      </div>
      <div className="w-64 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className="h-full bg-blue-500 rounded-full animate-pulse w-3/4" />
      </div>
    </div>
  );
}
