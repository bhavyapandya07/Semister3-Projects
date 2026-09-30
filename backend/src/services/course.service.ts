import { Course } from "../models/Course";
import { HttpError } from "../middleware/errors";
import type { SessionUser } from "@srms/shared";

export async function listCourses(filter: Record<string, unknown> = {}) { return Course.find(filter).populate("faculty", "name email").sort({ code: 1 }).lean(); }
export async function listCoursesForViewer(user: SessionUser) {
  if (user.role === "admin") return listCourses();
  if (user.role === "hod") return listCourses({ department: user.department });
  if (user.role === "faculty") return listCourses({ faculty: user.id });
  return [];
}
export async function getCourse(id: string) { const row = await Course.findById(id).lean(); if (!row) throw new HttpError(404, "Course not found"); return row; }
export async function createCourse(data: Record<string, unknown>) { return Course.create(data); }
export async function updateCourse(id: string, data: Record<string, unknown>) { const row = await Course.findByIdAndUpdate(id, data, { new: true, runValidators: true }); if (!row) throw new HttpError(404, "Course not found"); return row; }
export async function deleteCourse(id: string) { const row = await Course.findByIdAndDelete(id); if (!row) throw new HttpError(404, "Course not found"); }
