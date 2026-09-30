import { useState } from "react";
import { api } from "../api/client";

type ImportResult = { imported: number; failedCount: number; failures: Array<{row:number;reason:string}> };
export function ImportPage() {
  const [file, setFile] = useState<File | null>(null); const [result, setResult] = useState<ImportResult | null>(null); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function submit() { setError(""); setResult(null); if (!file) { setError("Choose a CSV file first."); return; } const data = new FormData(); data.append("file", file); setBusy(true); try { setResult(await api.post<ImportResult>("/enrollments/import", data)); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  return <section className="panel"><h1>Bulk CSV import</h1><p>Columns: <code>rollNumber,courseCode,semester,internal,midterm,final</code></p><input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /><button disabled={busy} onClick={submit}>{busy ? "Importing…" : "Upload and import"}</button>
    {error && <p className="error" role="alert">{error}</p>}{result && <><p className="success">Imported {result.imported}; {result.failedCount} rows need attention.</p><ul>{result.failures.map((item) => <li key={`${item.row}-${item.reason}`}>Row {item.row}: {item.reason}</li>)}</ul></>}</section>;
}
