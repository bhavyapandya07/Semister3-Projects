import { Student } from "../models/Student";
import { Course } from "../models/Course";
import { Enrollment } from "../models/Enrollment";
import type { SessionUser } from "@srms/shared";
import { HttpError } from "../middleware/errors";

export async function listStudents(filter: Record<string, unknown> = {}) { return Student.find(filter).sort({ rollNumber: 1 }).lean(); }
export async function listStudentsForViewer(user: SessionUser) {
  if (user.role === "admin") return listStudents();
  if (user.role === "hod") return listStudents({ department: user.department });
  if (user.role === "faculty") {
    const courseIds = await Course.find({ faculty: user.id }).distinct("_id");
    const studentIds = await Enrollment.find({ course: { $in: courseIds } }).distinct("student");
    return Student.find({ _id: { $in: studentIds } }).sort({ rollNumber: 1 }).lean();
  }
  return user.studentId ? Student.find({ _id: user.studentId }).lean() : [];
}
export async function listEligibleStudentsForCourse(courseId: string) {
  const course = await Course.findById(courseId).select("department").lean();
  if (!course) throw new HttpError(404, "Course not found");
  const enrolledIds = await Enrollment.distinct("student", { course: courseId });
  return Student.find({ department: course.department, _id: { $nin: enrolledIds } }).sort({ rollNumber: 1 }).lean();
}
export async function getStudent(id: string) { const row = await Student.findById(id).lean(); if (!row) throw new HttpError(404, "Student not found"); return row; }
export async function createStudent(data: Record<string, unknown>) { return Student.create(data); }
export async function updateStudent(id: string, data: Record<string, unknown>) { const row = await Student.findByIdAndUpdate(id, data, { new: true, runValidators: true }); if (!row) throw new HttpError(404, "Student not found"); return row; }
export async function deleteStudent(id: string) { const row = await Student.findByIdAndDelete(id); if (!row) throw new HttpError(404, "Student not found"); }
