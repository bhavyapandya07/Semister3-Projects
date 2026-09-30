import { useEffect, useState } from "react";
import { api } from "../api/client";

type Course = { _id: string; code: string; title: string };
type Row = { _id: string; totalMarks: number; grade: string; student?: { name: string; rollNumber: string } };
export function ResultsPage() {
  const [courses, setCourses] = useState<Course[]>([]); const [courseId, setCourseId] = useState(""); const [rows, setRows] = useState<Row[]>([]);
  const [sort, setSort] = useState<"totalMarks" | "name">("totalMarks"); const [ascending, setAscending] = useState(false);
  const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  useEffect(() => { api.get<Course[]>("/courses").then(setCourses).catch((e) => setError(e.message)); }, []);
  async function load() { if (!courseId) return; setLoading(true); setError(""); try { setRows(await api.get<Row[]>(`/enrollments/course/${courseId}`)); } catch (e) { setError((e as Error).message); } finally { setLoading(false); } }
  const sortedRows = [...rows].sort((a, b) => { const result = sort === "totalMarks" ? a.totalMarks - b.totalMarks : (a.student?.name ?? "").localeCompare(b.student?.name ?? ""); return ascending ? result : -result; });
  return <section className="panel"><h1>Course results</h1><div className="toolbar"><select value={courseId} onChange={(e) => setCourseId(e.target.value)}><option value="">Choose a course</option>{courses.map((c) => <option key={c._id} value={c._id}>{c.code} — {c.title}</option>)}</select><button onClick={load} disabled={!courseId || loading}>Load roster</button></div>
    {loading && <p role="status">Loading results…</p>}{error && <p className="error" role="alert">{error}</p>}
    <div className="table-wrap"><table><thead><tr><th>Roll no.</th><th><button className="sort-button" onClick={() => { setSort("name"); setAscending(!ascending); }}>Name ↕</button></th><th><button className="sort-button" onClick={() => { setSort("totalMarks"); setAscending(!ascending); }}>Total ↕</button></th><th>Grade</th></tr></thead><tbody>{sortedRows.map((row) => <tr key={row._id} className={`grade-row grade-${row.grade}`}><td>{row.student?.rollNumber}</td><td>{row.student?.name}</td><td>{row.totalMarks}</td><td>{row.grade}</td></tr>)}</tbody></table></div>
  </section>;
}
