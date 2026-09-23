const mongoose = require("mongoose");
const Enrollment = require("../models/Enrollment");

const oid = (id) => new mongoose.Types.ObjectId(id);

// GET /api/reports/course/:courseId/summary
// count, average, pass rate, highest, lowest — all in one $group.
async function courseSummary(req, res) {
  const { courseId } = req.params;
  const [result] = await Enrollment.aggregate([
    { $match: { course: oid(courseId), published: true } },
    {
      $group: {
        _id: "$course",
        count: { $sum: 1 },
        average: { $avg: "$totalMarks" },
        highest: { $max: "$totalMarks" },
        lowest: { $min: "$totalMarks" },
        passCount: {
          $sum: { $cond: [{ $ne: ["$grade", "F"] }, 1, 0] },
        },
      },
    },
    {
      $project: {
        _id: 0,
        count: 1,
        average: { $round: ["$average", 2] },
        highest: 1,
        lowest: 1,
        passRate: {
          $round: [{ $multiply: [{ $divide: ["$passCount", "$count"] }, 100] }, 1],
        },
      },
    },
  ]);
  res.json(result || { count: 0, average: 0, highest: 0, lowest: 0, passRate: 0 });
}

// GET /api/reports/course/:courseId/histogram
// $bucket over grade bands (marks-based boundaries, since $bucket needs
// numeric boundaries — we bucket totalMarks and label by band afterwards).
async function courseHistogram(req, res) {
  const { courseId } = req.params;
  const buckets = await Enrollment.aggregate([
    { $match: { course: oid(courseId), published: true } },
    {
      $bucket: {
        groupBy: "$totalMarks",
        boundaries: [0, 60, 70, 80, 90, 101], // F,D,C,B,A — 101 to include a perfect 100
        default: "other",
        output: { count: { $sum: 1 } },
      },
    },
  ]);
  const labels = { 0: "F", 60: "D", 70: "C", 80: "B", 90: "A" };
  const histogram = buckets.map((b) => ({
    band: labels[b._id] ?? b._id,
    count: b.count,
  }));
  res.json(histogram);
}

// GET /api/reports/student/:studentId/transcript
// $lookup course details onto every enrollment, then $group to fold them
// into a single credit-weighted GPA. GPA points follow a standard 4.0 map.
const GRADE_POINTS = { A: 4, B: 3, C: 2, D: 1, F: 0 };

async function studentTranscript(req, res) {
  const { studentId } = req.params;
  const rows = await Enrollment.aggregate([
    { $match: { student: oid(studentId), published: true } },
    {
      $lookup: {
        from: "courses",
        localField: "course",
        foreignField: "_id",
        as: "courseInfo",
      },
    },
    { $unwind: "$courseInfo" },
    {
      $project: {
        _id: 0,
        courseCode: "$courseInfo.code",
        courseTitle: "$courseInfo.title",
        credits: "$courseInfo.credits",
        semester: 1,
        totalMarks: 1,
        grade: 1,
        gradePoint: {
          $switch: {
            branches: Object.entries(GRADE_POINTS).map(([g, p]) => ({
              case: { $eq: ["$grade", g] },
              then: p,
            })),
            default: 0,
          },
        },
      },
    },
    { $sort: { semester: 1, courseCode: 1 } },
  ]);

  const [gpaRow] = await Enrollment.aggregate([
    { $match: { student: oid(studentId), published: true } },
    {
      $lookup: {
        from: "courses",
        localField: "course",
        foreignField: "_id",
        as: "courseInfo",
      },
    },
    { $unwind: "$courseInfo" },
    {
      $project: {
        credits: "$courseInfo.credits",
        gradePoint: {
          $switch: {
            branches: Object.entries(GRADE_POINTS).map(([g, p]) => ({
              case: { $eq: ["$grade", g] },
              then: p,
            })),
            default: 0,
          },
        },
      },
    },
    {
      $group: {
        _id: null,
        totalCredits: { $sum: "$credits" },
        weightedPoints: { $sum: { $multiply: ["$credits", "$gradePoint"] } },
      },
    },
    {
      $project: {
        _id: 0,
        gpa: {
          $cond: [
            { $eq: ["$totalCredits", 0] },
            0,
            { $round: [{ $divide: ["$weightedPoints", "$totalCredits"] }, 2] },
          ],
        },
      },
    },
  ]);

  res.json({ courses: rows, gpa: gpaRow?.gpa ?? 0 });
}

// GET /api/reports/toppers?semester=4&limit=10
// $lookup students onto enrollments, $group per student to sum marks
// across the semester, $sort desc, $limit. Projection is role-gated:
// a student caller gets rank + own row only (never classmates' marks),
// faculty/hod/admin get the full table.
async function toppers(req, res) {
  const semester = Number(req.query.semester);
  const limit = Math.min(Number(req.query.limit) || 10, 100);
  if (!semester) return res.status(400).json({ error: "semester query param required" });

  const pipeline = [
    { $match: { semester, published: true } },
    {
      $group: {
        _id: "$student",
        totalMarks: { $sum: "$totalMarks" },
        coursesTaken: { $sum: 1 },
      },
    },
    { $sort: { totalMarks: -1 } },
    { $limit: limit },
    {
      $lookup: {
        from: "students",
        localField: "_id",
        foreignField: "_id",
        as: "studentInfo",
      },
    },
    { $unwind: "$studentInfo" },
    {
      $project: {
        _id: 0,
        studentId: "$_id",
        name: "$studentInfo.name",
        rollNumber: "$studentInfo.rollNumber",
        totalMarks: 1,
        coursesTaken: 1,
      },
    },
  ];

  const rows = await Enrollment.aggregate(pipeline);
  const ranked = rows.map((r, i) => ({ rank: i + 1, ...r }));

  if (req.user.role === "student") {
    // Same pipeline, different $project stage applied in JS post-pass:
    // rank-only view, marks hidden for everyone but the caller.
    const restricted = ranked.map((r) =>
      r.studentId.toString() === req.user.studentId
        ? { rank: r.rank, name: r.name, rollNumber: r.rollNumber, totalMarks: r.totalMarks, you: true }
        : { rank: r.rank, name: r.name, rollNumber: r.rollNumber }
    );
    return res.json(restricted);
  }

  return res.json(ranked);
}

// GET /api/reports/enrollments-by-month?year=2026
// $group on $month(completedAt); JS only zero-fills months with no data,
// it does not compute the counts themselves.
async function enrollmentsByMonth(req, res) {
  const year = Number(req.query.year) || new Date().getFullYear();
  const rows = await Enrollment.aggregate([
    {
      $match: {
        completedAt: {
          $gte: new Date(`${year}-01-01T00:00:00.000Z`),
          $lt: new Date(`${year + 1}-01-01T00:00:00.000Z`),
        },
      },
    },
    {
      $group: {
        _id: { $month: "$completedAt" },
        count: { $sum: 1 },
      },
    },
  ]);

  const byMonth = new Map(rows.map((r) => [r._id, r.count]));
  const result = Array.from({ length: 12 }, (_, i) => ({
    month: i + 1,
    count: byMonth.get(i + 1) || 0,
  }));
  res.json(result);
}

// GET /api/reports/course/:courseId/toppers
// Same shape as /toppers but scoped to one course. This is the "subtler"
// IDOR case from the spec: a student can legitimately hit this for their
// own course, but must never see classmates' marks — only rank + name.
async function courseToppers(req, res) {
  const { courseId } = req.params;
  const limit = Math.min(Number(req.query.limit) || 10, 100);

  const rows = await Enrollment.aggregate([
    { $match: { course: oid(courseId), published: true } },
    { $sort: { totalMarks: -1 } },
    { $limit: limit },
    {
      $lookup: {
        from: "students",
        localField: "student",
        foreignField: "_id",
        as: "studentInfo",
      },
    },
    { $unwind: "$studentInfo" },
    {
      $project: {
        _id: 0,
        studentId: "$student",
        name: "$studentInfo.name",
        rollNumber: "$studentInfo.rollNumber",
        totalMarks: 1,
        grade: 1,
      },
    },
  ]);
  const ranked = rows.map((r, i) => ({ rank: i + 1, ...r }));

  if (req.user.role === "student") {
    const restricted = ranked.map((r) =>
      r.studentId.toString() === req.user.studentId
        ? { rank: r.rank, name: r.name, rollNumber: r.rollNumber, totalMarks: r.totalMarks, grade: r.grade, you: true }
        : { rank: r.rank, name: r.name, rollNumber: r.rollNumber }
    );
    return res.json(restricted);
  }

  return res.json(ranked);
}

module.exports = {
  courseSummary,
  courseHistogram,
  studentTranscript,
  toppers,
  courseToppers,
  enrollmentsByMonth,
};
