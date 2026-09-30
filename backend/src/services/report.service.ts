import type { CourseSummary, Transcript } from "@srms/shared";
import { Enrollment } from "../models/Enrollment";
import { Course } from "../models/Course";
import { Types } from "mongoose";
import { HttpError } from "../middleware/errors";

export async function courseSummary(courseId: string): Promise<CourseSummary> {
  const [row] = await Enrollment.aggregate([
    { $match: { course: new Types.ObjectId(courseId) } },
    { $group: { _id: null, count: { $sum: 1 }, average: { $avg: "$totalMarks" }, highest: { $max: "$totalMarks" }, lowest: { $min: "$totalMarks" }, passed: { $sum: { $cond: [{ $ne: ["$grade", "F"] }, 1, 0] } } } },
  ]);
  if (!row) return { count: 0, average: 0, passRate: 0, highest: 0, lowest: 0 };
  return { count: row.count, average: Number(row.average.toFixed(2)), passRate: Number((row.passed / row.count * 100).toFixed(1)), highest: row.highest, lowest: row.lowest };
}

export async function courseHistogram(courseId: string) {
  return Enrollment.aggregate([
    { $match: { course: new Types.ObjectId(courseId) } },
    { $bucket: { groupBy: "$totalMarks", boundaries: [0, 60, 70, 80, 90, 101], default: "other", output: { count: { $sum: 1 } } } },
    { $project: { band: { $switch: { branches: [ { case: { $eq: ["$_id", 0] }, then: "F" }, { case: { $eq: ["$_id", 60] }, then: "D" }, { case: { $eq: ["$_id", 70] }, then: "C" }, { case: { $eq: ["$_id", 80] }, then: "B" }, { case: { $eq: ["$_id", 90] }, then: "A" } ], default: "Other" } }, count: 1, _id: 0 } },
  ]);
}

export async function transcript(studentId: string): Promise<Transcript> {
  const [result] = await Enrollment.aggregate([
    { $match: { student: new Types.ObjectId(studentId) } },
    { $lookup: { from: "courses", localField: "course", foreignField: "_id", as: "course" } },
    { $unwind: "$course" },
    { $project: { courseCode: "$course.code", courseTitle: "$course.title", credits: "$course.credits", semester: 1, totalMarks: 1, grade: 1, qualityPoints: { $switch: { branches: [{case:{$eq:["$grade","A"]},then:4},{case:{$eq:["$grade","B"]},then:3},{case:{$eq:["$grade","C"]},then:2},{case:{$eq:["$grade","D"]},then:1}],default:0 } } } },
    { $group: { _id: null, courses: { $push: { courseCode: "$courseCode", courseTitle: "$courseTitle", credits: "$credits", semester: "$semester", totalMarks: "$totalMarks", grade: "$grade" } }, points: { $sum: { $multiply: ["$qualityPoints", "$credits"] } }, credits: { $sum: "$credits" } } },
    { $project: { courses: 1, gpa: { $cond: [{ $gt: ["$credits", 0] }, { $round: [{ $divide: ["$points", "$credits"] }, 2] }, 0] } } },
  ]);
  return result ?? { courses: [], gpa: 0 };
}

export async function toppers(semester = 4, limit = 10, courseId?: string, viewerIsStudent = false) {
  const match: Record<string, unknown> = { semester };
  if (courseId) match.course = new Types.ObjectId(courseId);
  const rows = await Enrollment.aggregate([
    { $match: match },
    { $group: { _id: "$student", totalMarks: { $sum: "$totalMarks" } } },
    { $sort: { totalMarks: -1 } }, { $limit: Math.min(Math.max(limit, 1), 100) },
    { $lookup: { from: "students", localField: "_id", foreignField: "_id", as: "student" } }, { $unwind: "$student" },
    { $setWindowFields: { sortBy: { totalMarks: -1 }, output: { rank: { $rank: {} } } } },
    { $project: viewerIsStudent ? { rank: 1, name: "$student.name", rollNumber: "$student.rollNumber" } : { rank: 1, name: "$student.name", rollNumber: "$student.rollNumber", totalMarks: 1 } },
  ]);
  return rows;
}

export async function enrollmentsByMonth(year: number, viewer?: { role: string; id: string; department?: string }) {
  const match: Record<string, unknown> = { completedAt: { $gte: new Date(year, 0, 1), $lt: new Date(year + 1, 0, 1) } };
  if (viewer?.role === "faculty") match.course = { $in: await Course.find({ faculty: viewer.id }).distinct("_id") };
  if (viewer?.role === "hod") match.course = { $in: await Course.find({ department: viewer.department }).distinct("_id") };
  const rows = await Enrollment.aggregate([
    { $match: match },
    { $group: { _id: { $month: "$completedAt" }, count: { $sum: 1 } } }, { $sort: { _id: 1 } },
  ]);
  const monthCounts = new Map(rows.map((row) => [row._id as number, row.count as number]));
  return Array.from({ length: 12 }, (_, index) => ({ month: index + 1, count: monthCounts.get(index + 1) ?? 0 }));
}
