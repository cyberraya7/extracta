import { X, FileText, Link2 } from 'lucide-react';
import type { EvidenceSnippet, InvestigationResult, InvestigationSource } from '../types';

interface EvidencePanelProps {
  snippets: EvidenceSnippet[];
  investigation: InvestigationResult | null;
  investigationLoading: boolean;
  canInvestigate: boolean;
  investigationSource: InvestigationSource;
  onInvestigationSourceChange: (source: InvestigationSource) => void;
  entityId: string | null;
  edge: { source: string; target: string } | null;
  onInvestigate: () => void;
  onClose: () => void;
}

export function EvidencePanel({
  snippets,
  investigation,
  investigationLoading,
  canInvestigate,
  investigationSource,
  onInvestigationSourceChange,
  entityId,
  edge: _edge,
  onInvestigate,
  onClose,
}: EvidencePanelProps) {
  const hasInvestigationContent =
    !!investigation &&
    (investigation.summary.trim().length > 0 ||
      investigation.notes.length > 0 ||
      investigation.findings.length > 0 ||
      investigation.status === 'failed' ||
      investigation.status === 'partial' ||
      investigation.status === 'not_configured');

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

      {entityId && canInvestigate && (
        <div className="space-y-2 bg-slate-900/60 border border-slate-800 rounded-xl p-3">
          <div className="text-xs uppercase tracking-wider text-slate-400">Investigation</div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap gap-3 text-xs text-slate-300">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="investigation-source"
                  checked={investigationSource === 'tools'}
                  onChange={() => onInvestigationSourceChange('tools')}
                  className="accent-cyan-600"
                />
                External lookup (configured tools)
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="investigation-source"
                  checked={investigationSource === 'instagram_leak'}
                  onChange={() => onInvestigationSourceChange('instagram_leak')}
                  className="accent-cyan-600"
                />
                Leak database
              </label>
            </div>
            <button
              onClick={onInvestigate}
              disabled={investigationLoading}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-cyan-700/60 hover:bg-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed text-cyan-100 transition-colors shrink-0"
            >
              {investigationLoading ? 'Investigating...' : 'Investigate'}
            </button>
          </div>
        </div>
      )}

      {entityId && hasInvestigationContent && investigation && (
        <div className="space-y-2 bg-slate-900/60 border border-slate-800 rounded-xl p-3">
          {investigation.summary && <p className="text-sm text-slate-300">{investigation.summary}</p>}
          {investigation.notes.length > 0 && (
            <ul className="text-xs text-amber-300 list-disc pl-4 space-y-1">
              {investigation.notes.map((note, idx) => (
                <li key={idx}>{note}</li>
              ))}
            </ul>
          )}
          {investigation.findings.length > 0 && (
            <div className="space-y-2">
              {investigation.findings.slice(0, 50).map((f, idx) => {
                const showSitesUi = isRegisteredSitesFinding(f.attributes);
                const showUsernameSitesUi = isFoundSitesFinding(f.attributes);
                const showTelegramUi = isTelegramPhoneFinding(f.attributes);
                const showLeakUi = isInstagramLeakFinding(f.attributes);
                const compactUi =
                  showSitesUi || showUsernameSitesUi || showTelegramUi || showLeakUi;
                return (
                  <div key={idx} className="bg-slate-800/60 border border-slate-700 rounded-lg p-2 text-xs space-y-1">
                    {!compactUi && (
                      <>
                        <div className="text-slate-200 font-medium">{f.title}</div>
                        <div className="text-slate-400 capitalize">
                          {f.category} • {Math.round(f.confidence * 100)}%
                        </div>
                      </>
                    )}
                    {renderInvestigationAttributes(f.attributes)}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

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
                highlightRanges={snippet.highlight_ranges || []}
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
  highlightRanges,
  highlights,
}: {
  text: string;
  highlightRanges: Array<{ start: number; end: number }>;
  highlights: string[];
}) {
  const primaryHighlight = (highlights[0] || '').trim();
  const strictRanges = primaryHighlight
    ? highlightRanges.filter((r) => {
      const start = Math.max(0, Math.min(text.length, r.start));
      const end = Math.max(0, Math.min(text.length, r.end));
      if (end <= start) return false;
      return text.slice(start, end).toLowerCase() === primaryHighlight.toLowerCase();
    })
    : highlightRanges;

  if (strictRanges.length > 0) {
    const normalized = [...strictRanges]
      .map((r) => ({
        start: Math.max(0, Math.min(text.length, r.start)),
        end: Math.max(0, Math.min(text.length, r.end)),
      }))
      .filter((r) => r.end > r.start)
      .sort((a, b) => a.start - b.start);

    const merged: Array<{ start: number; end: number }> = [];
    for (const r of normalized) {
      const prev = merged[merged.length - 1];
      if (!prev || r.start > prev.end) {
        merged.push({ ...r });
      } else {
        prev.end = Math.max(prev.end, r.end);
      }
    }

    const chunks: Array<{ text: string; mark: boolean }> = [];
    let cursor = 0;
    for (const r of merged) {
      if (cursor < r.start) {
        chunks.push({ text: text.slice(cursor, r.start), mark: false });
      }
      chunks.push({ text: text.slice(r.start, r.end), mark: true });
      cursor = r.end;
    }
    if (cursor < text.length) {
      chunks.push({ text: text.slice(cursor), mark: false });
    }

    return (
      <>
        {chunks.map((chunk, i) =>
          chunk.mark ? (
            <mark key={i} className="bg-yellow-500/30 text-yellow-200 rounded px-0.5">
              {chunk.text}
            </mark>
          ) : (
            <span key={i}>{chunk.text}</span>
          )
        )}
      </>
    );
  }

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

function formatAttributeValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function isRegisteredSitesFinding(attributes: Record<string, unknown>): boolean {
  const sites = attributes.registered_sites;
  if (!Array.isArray(sites)) return false;
  return sites.some((s) => typeof s === 'string' && s.trim().length > 0);
}

function isTelegramPhoneFinding(attributes: Record<string, unknown>): boolean {
  if (typeof attributes.telegram_found === 'boolean') return true;
  const matches = attributes.telegram_matches;
  return Array.isArray(matches);
}

function isInstagramLeakFinding(attributes: Record<string, unknown>): boolean {
  return typeof attributes.formatted_line === 'string';
}

function toDisplayField(value: unknown): string {
  if (value === null || value === undefined) return 'N/A';
  const text = String(value).trim();
  return text.length > 0 ? text : 'N/A';
}

function renderInstagramLeakFinding(attributes: Record<string, unknown>) {
  const formattedLine = typeof attributes.formatted_line === 'string'
    ? attributes.formatted_line.trim()
    : '';
  const entityPrefix = formattedLine.split(' was found in instagram leak')[0] || 'Email';
  const headingEntity = entityPrefix.charAt(0).toUpperCase() + entityPrefix.slice(1);
  const row = attributes.row;
  if (row && typeof row === 'object') {
    const leakRow = row as Record<string, unknown>;
    return (
      <div className="text-slate-300 space-y-1">
        <p className="font-medium">{headingEntity} was found in instagram leak</p>
        <ol className="list-decimal pl-4 space-y-0.5">
          <li>ID: {toDisplayField(leakRow.id)}</li>
          <li>Email: {toDisplayField(leakRow.e)}</li>
          <li>Name: {toDisplayField(leakRow.n)}</li>
          <li>Username: {toDisplayField(leakRow.u)}</li>
          <li>Phone Number: {toDisplayField(leakRow.T ?? leakRow.t)}</li>
        </ol>
      </div>
    );
  }

  if (typeof formattedLine === 'string' && formattedLine.trim()) {
    return (
      <div className="text-slate-300 whitespace-pre-wrap break-words text-[11px] leading-relaxed font-mono">
        {formattedLine}
      </div>
    );
  }
  return null;
}

function isFoundSitesFinding(attributes: Record<string, unknown>): boolean {
  const sites = attributes.found_sites;
  if (!Array.isArray(sites)) return false;
  return sites.some((s) => typeof s === 'string' && s.trim().length > 0);
}

function normalizeWebsiteUrl(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return '';
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

function humanizeHost(hostname: string): string {
  const clean = hostname.toLowerCase().replace(/^www\./, '');
  const mappedNames: Record<string, string> = {
    'open.spotify.com': 'Spotify',
    'spotify.com': 'Spotify',
    'instagram.com': 'Instagram',
    'pinterest.com': 'Pinterest',
    'youtube.com': 'YouTube',
    'tiktok.com': 'TikTok',
    'xboxgamertag.com': 'Xbox',
    'roblox.com': 'Roblox',
    'auth.roblox.com': 'Roblox',
    'scribd.com': 'Scribd',
    'truckersmp.com': 'TruckersMP',
    't.me': 'Telegram',
    'etoro.com': 'eToro',
    'x.com': 'X',
  };
  if (mappedNames[clean]) return mappedNames[clean];
  const firstLabel = clean.split('.')[0] || clean;
  if (!firstLabel) return 'Website';
  return firstLabel.charAt(0).toUpperCase() + firstLabel.slice(1);
}

function toWebsiteItem(raw: string): { label: string; href: string; display: string } {
  const href = normalizeWebsiteUrl(raw);
  try {
    const parsed = new URL(href);
    return {
      label: humanizeHost(parsed.hostname),
      href,
      display: href,
    };
  } catch {
    return {
      label: 'Website',
      href,
      display: href || raw,
    };
  }
}

function normalizeComparableUrl(value: string): string {
  return normalizeWebsiteUrl(value).replace(/\/+$/, '').toLowerCase();
}

function isLikelyUrl(value: string): boolean {
  return /^https?:\/\//i.test(value) || /^[a-z0-9.-]+\.[a-z]{2,}(\/|$)/i.test(value);
}

function renderInvestigationAttributes(attributes: Record<string, unknown>) {
  if (isInstagramLeakFinding(attributes)) {
    return renderInstagramLeakFinding(attributes);
  }

  const sites = attributes.registered_sites;
  if (Array.isArray(sites)) {
    const normalizedSites = sites
      .map((s) => (typeof s === 'string' ? s.trim() : String(s).trim()))
      .filter((s) => s.length > 0);

    if (normalizedSites.length > 0) {
      return (
        <div className="text-slate-300 space-y-1">
          <p>This email has been registered on these websites:</p>
          <ol className="list-decimal pl-4 space-y-0.5">
            {normalizedSites.map((site) => (
              <li key={site}>{site}</li>
            ))}
          </ol>
        </div>
      );
    }
  }

  const foundSites = attributes.found_sites;
  if (Array.isArray(foundSites)) {
    const normalizedSites = foundSites
      .map((s) => (typeof s === 'string' ? s.trim() : String(s).trim()))
      .filter((s) => s.length > 0);

    if (normalizedSites.length > 0) {
      const websiteItems = normalizedSites.map(toWebsiteItem);
      const rawProfiles = Array.isArray(attributes.site_profiles) ? attributes.site_profiles : [];
      const profilesByUrl = new Map<string, Record<string, unknown>>();
      rawProfiles.forEach((item) => {
        if (!item || typeof item !== 'object') return;
        const profile = item as Record<string, unknown>;
        const url = typeof profile.url === 'string' ? profile.url : '';
        if (!url) return;
        profilesByUrl.set(normalizeComparableUrl(url), profile);
      });
      return (
        <div className="text-slate-300 space-y-1">
          <p>This username was found on these websites:</p>
          <ol className="list-decimal pl-4 space-y-1">
            {websiteItems.map((site, idx) => (
              <li key={`${site.href}-${idx}`} className="space-y-0.5">
                <div>
                  {site.label}:{' '}
                  <a
                    href={site.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-cyan-300 hover:text-cyan-200 underline break-all"
                  >
                    {site.display}
                  </a>
                </div>
                {(() => {
                  const profile = profilesByUrl.get(normalizeComparableUrl(site.href));
                  if (!profile || typeof profile.details !== 'object' || !profile.details) return null;
                  const detailEntries = Object.entries(profile.details as Record<string, unknown>)
                    .filter(([, value]) => value !== null && value !== undefined && String(value).trim().length > 0)
                    .slice(0, 12);
                  if (detailEntries.length === 0) return null;
                  return (
                    <ul className="list-none pl-4 text-slate-400 space-y-0.5">
                      {detailEntries.map(([key, value]) => {
                        const text = String(value).trim();
                        return (
                          <li key={`${site.href}-${key}`}>
                            {key}: {isLikelyUrl(text) ? (
                              <a
                                href={normalizeWebsiteUrl(text)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-cyan-300 hover:text-cyan-200 underline break-all"
                              >
                                {text}
                              </a>
                            ) : (
                              <span className="break-words">{text}</span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  );
                })()}
              </li>
            ))}
          </ol>
        </div>
      );
    }
  }

  const telegramMatches = attributes.telegram_matches;
  const telegramFound = attributes.telegram_found === true;
  if (Array.isArray(telegramMatches)) {
    const normalizedPhone = typeof attributes.normalized_phone === 'string' ? attributes.normalized_phone : '';
    if (!telegramFound || telegramMatches.length === 0) {
      return (
        <div className="text-slate-300">
          No telegram account found for this number{normalizedPhone ? ` (${normalizedPhone})` : ''}.
        </div>
      );
    }

    const toField = (value: unknown): string => {
      if (value === null || value === undefined) return 'No';
      if (typeof value === 'boolean') return value ? 'Yes' : 'No';
      const text = String(value).trim();
      return text.length > 0 && text.toLowerCase() !== 'null' ? text : 'No';
    };

    return (
      <div className="text-slate-300 space-y-1">
        <p>Telegram account found{normalizedPhone ? ` for ${normalizedPhone}` : ''}:</p>
        <div className="space-y-2">
          {telegramMatches.slice(0, 20).map((row, idx) => {
            const item = (row && typeof row === 'object') ? (row as Record<string, unknown>) : {};
            const fullName = toField(item.name);
            const nameParts = fullName === 'No' ? [] : fullName.split(' ');
            const firstName = toField(item.first_name ?? (nameParts[0] ?? ''));
            const lastName = toField(item.last_name ?? (nameParts.slice(1).join(' ') ?? ''));
            const username = toField(item.username);
            const id = toField(item.id);
            return (
              <ol key={`tg-${idx}`} className="list-decimal pl-4 space-y-0.5">
                <li>ID: {id}</li>
                <li>Username: {username}</li>
                <li>First Name: {firstName}</li>
                <li>Last Name: {lastName}</li>
                <li>Fake: {toField(item.fake)}</li>
                <li>Verified: {toField(item.verified)}</li>
                <li>Premium: {toField(item.premium)}</li>
                <li>Mutual Contact: {toField(item.mutual_contact)}</li>
                <li>Bot: {toField(item.bot)}</li>
                <li>Bot Chat History: {toField(item.bot_chat_history)}</li>
                <li>Restricted: {toField(item.restricted)}</li>
                <li>Restriction Reason: {toField(item.restriction_reason)}</li>
                <li>User Was Online: {toField(item.user_was_online)}</li>
                <li>Phone: {toField(item.phone)}</li>
              </ol>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="text-slate-300">
      {Object.entries(attributes)
        .slice(0, 4)
        .map(([k, v]) => `${k}: ${formatAttributeValue(v)}`)
        .join(' | ')}
    </div>
  );
}
