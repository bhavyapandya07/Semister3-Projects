import { useState } from "react";
import type { Transcript } from "@srms/shared";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function TranscriptPage() {
  const { user } = useAuth(); const [studentId, setStudentId] = useState(user?.studentId ?? ""); const [data, setData] = useState<Transcript | null>(null); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  async function load() { setLoading(true); setError(""); try { setData(await api.transcript(studentId)); } catch (e) { setError((e as Error).message); } finally { setLoading(false); } }
  return <section className="panel"><h1>Transcript</h1>{user?.role !== "student" && <label>Student ID<input value={studentId} onChange={(e) => setStudentId(e.target.value)} /></label>}<button onClick={load} disabled={!studentId || loading}>{loading ? "Loading…" : "Load transcript"}</button>
    {error && <p className="error" role="alert">{error}</p>}{data && <><article className="stat gpa"><strong>{data.gpa}</strong><span>Credit-weighted GPA</span></article><div className="table-wrap"><table><thead><tr><th>Course</th><th>Semester</th><th>Marks</th><th>Grade</th></tr></thead><tbody>{data.courses.map((row) => <tr key={row.courseCode}><td>{row.courseCode} — {row.courseTitle}</td><td>{row.semester}</td><td>{row.totalMarks}</td><td>{row.grade}</td></tr>)}</tbody></table></div></>}</section>;
}
