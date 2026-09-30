import { useEffect, useState } from "react";
import type { CourseSummary } from "@srms/shared";
import { api } from "../api/client";

type Course = { _id: string; code: string; title: string };
type Band = { band: string; count: number };
const colors: Record<string,string> = { A: "#21865b", B: "#5365ca", C: "#aa8618", D: "#af641e", F: "#a63642" };
export function DashboardPage() {
  const [courses, setCourses] = useState<Course[]>([]); const [courseId, setCourseId] = useState(""); const [summary, setSummary] = useState<CourseSummary | null>(null); const [bands, setBands] = useState<Band[]>([]); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  useEffect(() => { api.get<Course[]>("/courses").then(setCourses).catch((e) => setError(e.message)); }, []);
  async function load() { setLoading(true); setError(""); try { const [s,h] = await Promise.all([api.summary(courseId), api.get<Band[]>(`/reports/course/${courseId}/histogram`)]); setSummary(s); setBands(h); } catch (e) { setError((e as Error).message); } finally { setLoading(false); } }
  const max = Math.max(1, ...bands.map((b) => b.count));
  return <section className="panel"><h1>Course dashboard</h1><div className="toolbar"><select value={courseId} onChange={(e) => setCourseId(e.target.value)}><option value="">Choose a course</option>{courses.map((c) => <option key={c._id} value={c._id}>{c.code} — {c.title}</option>)}</select><button disabled={!courseId || loading} onClick={load}>Load dashboard</button></div>
    {loading && <p role="status">Loading analytics…</p>}{error && <p className="error" role="alert">{error}</p>}
    {summary && <><div className="stats">{[["Enrolled", summary.count],["Average", summary.average],["Pass rate", `${summary.passRate}%`],["High / low", `${summary.highest} / ${summary.lowest}`]].map(([label,value]) => <article className="stat" key={label}><strong>{value}</strong><span>{label}</span></article>)}</div><h2>Grade bands</h2>{bands.map((item) => <div className="bar-row" key={item.band}><span>{item.band}</span><div className="bar-track"><div style={{ width: `${item.count / max * 100}%`, backgroundColor: colors[item.band] ?? "#52617d" }} /></div><span>{item.count}</span></div>)}</>}
  </section>;
}
