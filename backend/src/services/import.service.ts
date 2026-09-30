import fs from "node:fs";
import csv from "csv-parser";
import { Course } from "../models/Course";
import { Student } from "../models/Student";
import { Enrollment } from "../models/Enrollment";
import { createGradingScheme } from "../grading/GradingScheme";
import { HttpError } from "../middleware/errors";
import type { SessionUser } from "@srms/shared";

type CsvRow = { rollNumber?: string; courseCode?: string; semester?: string; internal?: string; midterm?: string; final?: string };
type Failure = { row: number; reason: string };
const BATCH_SIZE = 500;

export async function importEnrollments(filePath: string, actor: SessionUser, progress: (count: number) => void) {
  const courseFilter = actor.role === "admin" ? {} : actor.role === "hod" ? { department: actor.department } : { faculty: actor.id };
  const courses = await Course.find(courseFilter).lean();
  const byCode = new Map(courses.map((course) => [course.code, course]));
  const failed: Failure[] = [];
  let imported = 0;
  let rowNumber = 0;
  let processed = 0;
  let buffer: Array<{ number: number; row: CsvRow }> = [];

  async function flush() {
    if (!buffer.length) return;
    const studentIds = [...new Set(buffer.map(({ row }) => row.rollNumber).filter((v): v is string => Boolean(v)))];
    const students = await Student.find({ rollNumber: { $in: studentIds } }).select("rollNumber").lean();
    const studentByRoll = new Map(students.map((student) => [student.rollNumber, student]));
    const existing = await Enrollment.find({ student: { $in: students.map((s) => s._id) }, course: { $in: courses.map((c) => c._id) } }).select("student course").lean();
    const existingPairs = new Set(existing.map((entry) => `${entry.student}:${entry.course}`));
    const operations: Array<{ insertOne: { document: Record<string, unknown> } }> = [];
    const sourceRows: number[] = [];
    for (const item of buffer) {
      const course = byCode.get(String(item.row.courseCode ?? "").trim().toUpperCase());
      const student = studentByRoll.get(String(item.row.rollNumber ?? "").trim());
      if (!course) { failed.push({ row: item.number, reason: "Unknown course or course is outside your assignment" }); continue; }
      if (!student) { failed.push({ row: item.number, reason: "Student roll number was not found" }); continue; }
      const pair = `${student._id}:${course._id}`;
      if (existingPairs.has(pair)) { failed.push({ row: item.number, reason: "Student is already enrolled in this course" }); continue; }
      const maxes = { internal: 20, midterm: 30, final: 50 };
      const assessments = (["internal", "midterm", "final"] as const).map((kind) => ({ kind, marks: Number(item.row[kind]), maxMarks: maxes[kind] }));
      if (assessments.some((a) => !Number.isFinite(a.marks) || a.marks < 0 || a.marks > a.maxMarks)) { failed.push({ row: item.number, reason: "Marks must be numeric and within the assessment maximum" }); continue; }
      const semester = Number(item.row.semester);
      if (!Number.isInteger(semester) || semester < 1 || semester > 12) { failed.push({ row: item.number, reason: "Semester must be a whole number from 1 to 12" }); continue; }
      const totalMarks = assessments.reduce((sum, assessment) => sum + assessment.marks, 0);
      const grade = createGradingScheme(course.gradingScheme, course.maxMarks).computeGrade(totalMarks);
      operations.push({ insertOne: { document: { student: student._id, course: course._id, semester, assessments, totalMarks, grade, completedAt: new Date() } } });
      sourceRows.push(item.number);
      existingPairs.add(pair);
    }
    if (operations.length) {
      try {
        const result = await Enrollment.bulkWrite(operations, { ordered: false });
        imported += result.insertedCount;
      } catch (error) {
        const writeErrors = (error as { writeErrors?: Array<{ index: number; errmsg?: string }> }).writeErrors ?? [];
        const badIndices = new Set(writeErrors.map((entry) => entry.index));
        imported += operations.length - badIndices.size;
        for (const entry of writeErrors) failed.push({ row: sourceRows[entry.index] ?? 0, reason: entry.errmsg ?? "Database rejected this row" });
      }
    }
    processed += buffer.length;
    progress(processed);
    buffer = [];
  }

  try {
    const stream = fs.createReadStream(filePath).pipe(csv());
    for await (const row of stream as AsyncIterable<CsvRow>) {
      rowNumber += 1;
      buffer.push({ number: rowNumber, row });
      if (buffer.length >= BATCH_SIZE) await flush();
    }
    await flush();
  } catch (error) {
    throw new HttpError(422, `CSV import failed: ${(error as Error).message}`);
  }
  return { imported, failed };
}
