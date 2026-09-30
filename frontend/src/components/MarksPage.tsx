import { useEffect, useState, type FormEvent } from "react";
import type { CreateEnrollmentInput } from "@srms/shared";
import { api } from "../api/client";

type Choice = { _id: string; name?: string; rollNumber?: string; code?: string; title?: string };
export function MarksPage() {
  const [students, setStudents] = useState<Choice[]>([]); const [courses, setCourses] = useState<Choice[]>([]);
  const [student, setStudent] = useState(""); const [course, setCourse] = useState(""); const [semester, setSemester] = useState(4);
  const [internal, setInternal] = useState(""); const [midterm, setMidterm] = useState(""); const [finalMark, setFinalMark] = useState("");
  const [message, setMessage] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { api.get<Choice[]>("/courses").then(setCourses).catch((e) => setError(e.message)); }, []);
  useEffect(() => { setStudent(""); setStudents([]); if (course) api.get<Choice[]>(`/students/eligible-for-course/${course}`).then(setStudents).catch((e) => setError(e.message)); }, [course]);
  async function submit(event: FormEvent) { event.preventDefault(); setError(""); setMessage("");
    const values = [["Internal", Number(internal), 20], ["Midterm", Number(midterm), 30], ["Final", Number(finalMark), 50]] as const;
    const invalid = values.find(([_, value, max]) => !Number.isFinite(value) || value < 0 || value > max);
    if (invalid) { setError(`${invalid[0]} marks must be between 0 and ${invalid[2]}.`); return; }
    if (!student || !course || semester < 1 || semester > 12) { setError("Choose a student, course, and valid semester."); return; }
    const payload: CreateEnrollmentInput = { student, course, semester, assessments: [{kind:"internal",marks:Number(internal),maxMarks:20},{kind:"midterm",marks:Number(midterm),maxMarks:30},{kind:"final",marks:Number(finalMark),maxMarks:50}] };
    setBusy(true); try { const result = await api.createEnrollment(payload); setMessage(`Created — total ${result.totalMarks}, grade ${result.grade}`); }
    catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }
  return <section className="panel"><h1>Marks entry</h1><form className="form-grid" onSubmit={submit}>
    <label>Course<select required value={course} onChange={(e) => setCourse(e.target.value)}><option value="">Choose a course</option>{courses.map((item) => <option key={item._id} value={item._id}>{item.code} — {item.title}</option>)}</select></label>
    <label>Student<select required value={student} onChange={(e) => setStudent(e.target.value)}><option value="">Choose a student</option>{students.map((item) => <option key={item._id} value={item._id}>{item.rollNumber} — {item.name}</option>)}</select></label>
    <label>Semester<input type="number" min={1} max={12} required value={semester} onChange={(e) => setSemester(Number(e.target.value))} /></label>
    <label>Internal (0–20)<input type="number" min={0} max={20} required value={internal} onChange={(e) => setInternal(e.target.value)} /></label>
    <label>Midterm (0–30)<input type="number" min={0} max={30} required value={midterm} onChange={(e) => setMidterm(e.target.value)} /></label>
    <label>Final (0–50)<input type="number" min={0} max={50} required value={finalMark} onChange={(e) => setFinalMark(e.target.value)} /></label>
    <button disabled={busy}>{busy ? "Saving…" : "Create enrollment"}</button>
  </form>{error && <p className="error" role="alert">{error}</p>}{message && <p className="success" role="status">{message}</p>}</section>;
}
