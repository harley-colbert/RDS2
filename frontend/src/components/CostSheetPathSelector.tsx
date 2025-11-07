import React from 'react';

export default function CostSheetPathSelector() {
  const [path, setPath] = React.useState('');
  const [msg, setMsg] = React.useState<string | null>(null);
  const [err, setErr] = React.useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    try {
      const res = await fetch('/api/cost-sheet/path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      setMsg('Workbook opened.');
    } catch (e: any) {
      setErr(e?.message ?? 'Failed to open workbook.');
    }
  };

  return (
    <form onSubmit={submit} className="flex items-center gap-2">
      <input
        className="border px-2 py-1 rounded w-full"
        placeholder="C:\\path\\to\\Costing.xlsb"
        value={path}
        onChange={(e) => setPath(e.target.value)}
      />
      <button className="px-3 py-1 rounded bg-black text-white">Open</button>
      {msg && <div className="text-xs text-green-700">{msg}</div>}
      {err && <div className="text-xs text-red-700">{err}</div>}
    </form>
  );
}
