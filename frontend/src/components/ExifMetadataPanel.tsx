import { Camera } from 'lucide-react';

export interface DocWithExif {
  document_id: string;
  filename: string;
  exif_metadata?: Record<string, unknown> | null;
}

interface ExifMetadataPanelProps {
  documents: DocWithExif[];
}

/** Flatten nested dicts one level for display */
function flattenExif(
  obj: Record<string, unknown>,
  prefix = '',
): Array<{ key: string; value: string }> {
  const rows: Array<{ key: string; value: string }> = [];
  for (const [k, v] of Object.entries(obj)) {
    const label = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      rows.push(...flattenExif(v as Record<string, unknown>, label));
    } else if (Array.isArray(v)) {
      rows.push({ key: label, value: JSON.stringify(v) });
    } else {
      rows.push({ key: label, value: String(v ?? '') });
    }
  }
  return rows;
}

export function ExifMetadataPanel({ documents }: ExifMetadataPanelProps) {
  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-500">
        <Camera className="w-12 h-12" />
        <p className="text-sm text-center px-4">
          Upload files to view embedded metadata: camera EXIF for photos, PDF document properties, Word core
          properties, and tags from common audio and video formats when available.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 h-full flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 shrink-0 flex items-center gap-2">
        <Camera className="w-4 h-4 text-cyan-400" />
        <h3 className="font-semibold text-sm text-slate-300">File metadata</h3>
        <span className="text-xs text-slate-500 ml-auto">{documents.length} file(s)</span>
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-6">
        {documents.map((doc) => {
          const meta = doc.exif_metadata;
          const isRasterMeta = meta !== undefined && meta !== null;
          const keys = meta && typeof meta === 'object' ? Object.keys(meta as object) : [];
          const hasExif = keys.length > 0;

          return (
            <section key={doc.document_id} className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
              <div className="px-3 py-2 bg-slate-800/60 border-b border-slate-800">
                <p className="text-sm font-medium text-slate-200 truncate" title={doc.filename}>
                  {doc.filename}
                </p>
              </div>
              {!isRasterMeta ? (
                <p className="text-xs text-slate-500 px-3 py-4">
                  No metadata payload for this document (legacy upload or extractor did not run).
                </p>
              ) : !hasExif ? (
                <p className="text-xs text-slate-500 px-3 py-4">
                  No embedded metadata found for this file (stripped export, plain text, or unsupported or empty
                  container).
                </p>
              ) : (
                <table className="w-full text-xs">
                  <tbody>
                    {flattenExif(meta as Record<string, unknown>).map(({ key, value }) => (
                      <tr key={key} className="border-t border-slate-800/80">
                        <td className="align-top py-2 px-3 text-slate-400 w-[40%] shrink-0 break-all">
                          {key}
                        </td>
                        <td className="align-top py-2 px-3 text-slate-200 break-all">{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
