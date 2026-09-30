import { Enrollment } from "../models/Enrollment";
import { Course } from "../models/Course";
import { Student } from "../models/Student";
import { AuditLog } from "../models/AuditLog";
import { createGradingScheme } from "../grading/GradingScheme";
import { HttpError } from "../middleware/errors";

const assessmentMax: Record<string, number> = { internal: 20, midterm: 30, final: 50 };
function validateAssessments(assessments: Array<{kind:string;marks:number;maxMarks:number}>) {
  const kinds = assessments.map((item) => item.kind);
  if (new Set(kinds).size !== kinds.length) throw new HttpError(422, "Each assessment kind may appear only once");
  if (assessments.length !== 3 || !["internal", "midterm", "final"].every((kind) => kinds.includes(kind))) throw new HttpError(422, "Internal, midterm, and final marks are required");
  for (const item of assessments) {
    const expectedMax = assessmentMax[item.kind];
    if (item.maxMarks !== expectedMax || item.marks < 0 || item.marks > expectedMax) throw new HttpError(422, `${item.kind} must be between 0 and ${expectedMax}`);
  }
}

async function gradeFor(courseId: string, total: number, schemeKind: string, maxMarks: number) {
  const courseMarks = schemeKind === "relative"
    ? (await Enrollment.find({ course: courseId, published: true }).select("totalMarks").lean()).map((row) => row.totalMarks)
    : undefined;
  return createGradingScheme(schemeKind, maxMarks).computeGrade(total, courseMarks);
}

export async function createEnrollment(input: { student: string; course: string; semester: number; assessments: Array<{kind:string;marks:number;maxMarks:number}> }) {
  const [course, student] = await Promise.all([Course.findById(input.course).lean(), Student.findById(input.student).lean()]);
  if (!course) throw new HttpError(404, "Course not found");
  if (!student) throw new HttpError(404, "Student not found");
  validateAssessments(input.assessments);
  const totalMarks = input.assessments.reduce((sum, item) => sum + item.marks, 0);
  const grade = await gradeFor(String(course._id), totalMarks, course.gradingScheme, course.maxMarks);
  return Enrollment.create({ ...input, totalMarks, grade });
}

export async function listCourseEnrollments(courseId: string) {
  return Enrollment.find({ course: courseId }).populate("student", "name rollNumber").sort({ totalMarks: -1 }).lean();
}
export async function getEnrollment(id: string) { const row = await Enrollment.findById(id).populate("student", "name rollNumber").lean(); if (!row) throw new HttpError(404, "Enrollment not found"); return row; }
export async function deleteEnrollment(id: string) { const row = await Enrollment.findByIdAndDelete(id); if (!row) throw new HttpError(404, "Enrollment not found"); }

export async function editMarks(id: string, assessments: Array<{kind:string;marks:number;maxMarks:number}>) {
  const row = await Enrollment.findById(id);
  if (!row) throw new HttpError(404, "Enrollment not found");
  if (row.published) throw new HttpError(409, "Enrollment is published; use the amendment endpoint");
  const course = await Course.findById(row.course).lean();
  if (!course) throw new HttpError(404, "Course not found");
  validateAssessments(assessments);
  row.assessments = assessments as typeof row.assessments;
  row.totalMarks = assessments.reduce((sum, item) => sum + item.marks, 0);
  row.grade = await gradeFor(String(course._id), row.totalMarks, course.gradingScheme, course.maxMarks);
  await row.save();
  return row;
}

export async function publishEnrollment(id: string) {
  const row = await Enrollment.findById(id);
  if (!row) throw new HttpError(404, "Enrollment not found");
  row.published = true;
  row.completedAt = row.completedAt ?? new Date();
  await row.save();
  return row;
}

export async function amendEnrollment(id: string, input: { kind: string; marks: number; reason: string }, userId: string) {
  if (!input.reason.trim()) throw new HttpError(422, "A reason is required");
  const row = await Enrollment.findById(id);
  if (!row) throw new HttpError(404, "Enrollment not found");
  if (!row.published) throw new HttpError(409, "Enrollment is not published");
  const target = row.assessments.find((item) => item.kind === input.kind);
  if (!target) throw new HttpError(404, "Assessment not found");
  if (input.marks < 0 || input.marks > target.maxMarks || target.maxMarks !== assessmentMax[input.kind]) throw new HttpError(422, "Marks are outside the allowed range");
  const oldValue = target.marks;
  target.marks = input.marks;
  row.totalMarks = row.assessments.reduce((sum, item) => sum + item.marks, 0);
  const course = await Course.findById(row.course).lean();
  if (!course) throw new HttpError(404, "Course not found");
  row.grade = await gradeFor(String(course._id), row.totalMarks, course.gradingScheme, course.maxMarks);
  const audit = await AuditLog.create({ enrollment: row._id, changedBy: userId, field: `assessments.${input.kind}.marks`, oldValue, newValue: input.marks, reason: input.reason });
  try { await row.save(); }
  catch (error) { await AuditLog.deleteOne({ _id: audit._id }); throw error; }
  return row;
}
