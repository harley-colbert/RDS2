import React from 'react';
import CostSheetPathSelector from './CostSheetPathSelector';

type TableResponse = {
  sheet: string;
  range: string;
  values: any[][];
};

export default function ExcelSummaryPanel() {
  const [data, setData] = React.useState<TableResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [showRaw, setShowRaw] = React.useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/cost-sheet/summary');
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const body = (await res.json()) as TableResponse;
      setData(body);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load.');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="min-h-screen flex flex-col border-l">
      <div className="p-3 border-b space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold">Excel Summary</div>
            <div className="text-xs text-gray-500">
              {data ? `${data.sheet}!${data.range}` : 'Summary!C4:K55'}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="text-xs underline" onClick={fetchData}>refresh</button>
            <label className="text-xs flex items-center gap-1">
              <input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} />
              raw
            </label>
          </div>
        </div>
        <CostSheetPathSelector />
      </div>
      <div className="p-3 flex-1 overflow-auto">
        {loading && <div className="text-sm">Loading…</div>}
        {error && (
          <div className="text-sm text-red-600">
            {error}{' '}
            <button className="underline" onClick={fetchData}>retry</button>
          </div>
        )}
        {!loading && !error && (
          <div className="overflow-auto space-y-3">
            <div className="overflow-auto">
              <table className="min-w-full text-xs border">
                <tbody>
                  {data?.values?.map((row, rIdx) => (
                    <tr key={rIdx} className="border-b">
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="px-2 py-1 border-r align-top">
                          {cell === null ? '' : String(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {!data?.values?.length && (
                <div className="text-sm text-gray-500">No data in range.</div>
              )}
            </div>
            {showRaw && (
              <pre className="text-[10px] bg-gray-50 border p-2 rounded overflow-auto">
                {JSON.stringify(data, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
