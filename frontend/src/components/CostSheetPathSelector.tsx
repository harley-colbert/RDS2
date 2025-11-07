import React from 'react';

type BrowserEntry = {
  name: string;
  path: string;
  isDir: boolean;
  isFile: boolean;
  isExcel: boolean;
};

type BrowseState = {
  cwd: string;
  parent: string | null;
  entries: BrowserEntry[];
  roots: BrowserEntry[];
};

type Props = {
  onPathSaved?: () => void;
};

const INITIAL_BROWSE_STATE: BrowseState = {
  cwd: '',
  parent: null,
  entries: [],
  roots: [],
};

export default function CostSheetPathSelector({ onPathSaved }: Props) {
  const [path, setPath] = React.useState('');
  const [msg, setMsg] = React.useState<string | null>(null);
  const [err, setErr] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [showBrowser, setShowBrowser] = React.useState(false);
  const [browserState, setBrowserState] = React.useState<BrowseState>(INITIAL_BROWSE_STATE);
  const [browserError, setBrowserError] = React.useState<string | null>(null);
  const [browserLoading, setBrowserLoading] = React.useState(false);

  const loadStoredPath = React.useCallback(async () => {
    try {
      const res = await fetch('/api/cost-sheet/path');
      if (!res.ok) {
        return;
      }
      const body = await res.json().catch(() => ({}));
      if (body?.path) {
        setPath(String(body.path));
      }
    } catch (e) {
      // ignore failures when loading stored path
      console.warn('Failed to load stored cost sheet path', e); // eslint-disable-line no-console
    }
  }, []);

  React.useEffect(() => {
    loadStoredPath();
  }, [loadStoredPath]);

  const loadBrowser = React.useCallback(
    async (target?: string) => {
      setBrowserLoading(true);
      setBrowserError(null);
      try {
        const url = target ? `/api/cost-sheet/browse?path=${encodeURIComponent(target)}` : '/api/cost-sheet/browse';
        const res = await fetch(url);
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(body?.detail || `HTTP ${res.status}`);
        }
        setBrowserState({
          cwd: String(body.cwd || ''),
          parent: body.parent ?? null,
          entries: Array.isArray(body.entries) ? (body.entries as BrowserEntry[]) : [],
          roots: Array.isArray(body.roots) ? (body.roots as BrowserEntry[]) : [],
        });
      } catch (e: any) {
        setBrowserError(e?.message ?? 'Failed to browse directories.');
      } finally {
        setBrowserLoading(false);
      }
    },
    []
  );

  React.useEffect(() => {
    if (showBrowser) {
      const initial = path || undefined;
      loadBrowser(initial);
    }
  }, [showBrowser, loadBrowser, path]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!path.trim()) {
      setErr('Enter a workbook path.');
      return;
    }
    setMsg(null);
    setErr(null);
    setSaving(true);
    try {
      const res = await fetch('/api/cost-sheet/path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      setMsg('Workbook opened and saved.');
      onPathSaved?.();
    } catch (e: any) {
      setErr(e?.message ?? 'Failed to open workbook.');
    } finally {
      setSaving(false);
    }
  };

  const closeBrowser = () => {
    setShowBrowser(false);
    setBrowserError(null);
  };

  const selectPath = (selected: string) => {
    setPath(selected);
    setMsg(null);
    setErr(null);
    setShowBrowser(false);
  };

  return (
    <div className="space-y-2">
      <form onSubmit={submit} className="flex flex-col sm:flex-row sm:items-center gap-2">
        <input
          className="border px-2 py-1 rounded w-full"
          placeholder="C:\\path\\to\\Costing.xlsb"
          value={path}
          onChange={(e) => setPath(e.target.value)}
        />
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="px-3 py-1 rounded border text-xs"
            onClick={() => setShowBrowser(true)}
          >
            Browse
          </button>
          <button
            type="submit"
            className="px-3 py-1 rounded bg-black text-white text-xs"
            disabled={saving}
          >
            {saving ? 'Saving…' : 'Open'}
          </button>
        </div>
      </form>
      {msg && <div className="text-xs text-green-700">{msg}</div>}
      {err && <div className="text-xs text-red-700">{err}</div>}

      {showBrowser && (
        <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded shadow-lg w-[min(90vw,640px)] max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-4 py-2 border-b">
              <div className="text-sm font-semibold">Select Cost Sheet</div>
              <button type="button" className="text-sm" onClick={closeBrowser}>
                ✕
              </button>
            </div>
            <div className="px-4 py-2 text-xs text-gray-600 border-b">
              Current folder: <span className="font-mono break-all">{browserState.cwd || 'Drives'}</span>
            </div>
            {browserError && <div className="px-4 py-2 text-xs text-red-600">{browserError}</div>}
            <div className="px-4 py-3 flex-1 overflow-auto space-y-3">
              {browserState.roots.length > 0 && (
                <div>
                  <div className="text-[11px] uppercase text-gray-500 mb-2">Drives</div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {browserState.roots.map((root) => (
                      <button
                        key={root.path}
                        type="button"
                        className="border rounded px-2 py-1 text-xs text-left hover:bg-gray-100"
                        onClick={() => loadBrowser(root.path)}
                      >
                        {root.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <div className="flex items-center justify-between text-[11px] uppercase text-gray-500 mb-2">
                  <span>Contents</span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="text-xs underline"
                      disabled={!browserState.parent}
                      onClick={() => browserState.parent && loadBrowser(browserState.parent!)}
                    >
                      Up One Level
                    </button>
                    <button type="button" className="text-xs underline" onClick={() => loadBrowser()}>
                      Reset
                    </button>
                  </div>
                </div>
                <div className="border rounded divide-y">
                  {browserLoading && <div className="px-3 py-2 text-sm">Loading…</div>}
                  {!browserLoading && browserState.entries.length === 0 && (
                    <div className="px-3 py-2 text-sm text-gray-500">No items in this folder.</div>
                  )}
                  {!browserLoading &&
                    browserState.entries.map((entry) => (
                      <div key={entry.path} className="px-3 py-2 text-sm flex items-center justify-between gap-3">
                        <button
                          type="button"
                          className="flex-1 text-left truncate hover:underline"
                          onClick={() => (entry.isDir ? loadBrowser(entry.path) : selectPath(entry.path))}
                        >
                          <span className="mr-2" aria-hidden>
                            {entry.isDir ? '📁' : entry.isExcel ? '📄' : '📃'}
                          </span>
                          <span className="align-middle">{entry.name || entry.path}</span>
                        </button>
                        {entry.isFile && (
                          <button
                            type="button"
                            className="text-xs px-2 py-1 border rounded"
                            onClick={() => selectPath(entry.path)}
                            disabled={!entry.isExcel}
                          >
                            Select
                          </button>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            </div>
            <div className="px-4 py-2 border-t flex justify-end">
              <button type="button" className="text-xs underline" onClick={closeBrowser}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
