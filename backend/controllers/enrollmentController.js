const Enrollment = require("../models/Enrollment");
const Course = require("../models/Course");
const AuditLog = require("../models/AuditLog");
const { createGradingScheme } = require("../grading/GradingScheme");

function sumMarks(assessments) {
  return assessments.reduce((sum, a) => sum + a.marks, 0);
}

async function computeAndSetGrade(enrollment, course) {
  enrollment.totalMarks = sumMarks(enrollment.assessments);
  const scheme = createGradingScheme(course.gradingScheme, course.maxMarks);

  let courseMarks;
  if (course.gradingScheme === "relative") {
    const peers = await Enrollment.find({ course: course._id, published: true })
      .select("totalMarks")
      .lean();
    courseMarks = peers.map((p) => p.totalMarks);
  }
  enrollment.grade = scheme.computeGrade(enrollment.totalMarks, courseMarks);
}

// POST /api/enrollments  — create enrollment (not yet published, freely editable)
async function createEnrollment(req, res) {
  const { student, course, semester, assessments = [] } = req.body;
  const courseDoc = await Course.findById(course);
  if (!courseDoc) return res.status(404).json({ error: "Course not found" });

  const enrollment = new Enrollment({ student, course, semester, assessments });
  await computeAndSetGrade(enrollment, courseDoc);
  await enrollment.save();
  res.status(201).json(enrollment);
}

// PUT /api/enrollments/:id/marks — enter/update marks BEFORE publication.
// Freely editable; this is normal grading workflow, not amendment.
async function enterMarks(req, res) {
  const enrollment = await Enrollment.findById(req.params.id);
  if (!enrollment) return res.status(404).json({ error: "Enrollment not found" });
  if (enrollment.published) {
    return res.status(409).json({
      error: "Enrollment is published; use /amend with a reason instead",
    });
  }

  const courseDoc = await Course.findById(enrollment.course);
  enrollment.assessments = req.body.assessments;
  await computeAndSetGrade(enrollment, courseDoc);
  await enrollment.save();
  res.json(enrollment);
}

// POST /api/enrollments/:id/publish — freezes marks; future edits require /amend
async function publish(req, res) {
  const enrollment = await Enrollment.findById(req.params.id);
  if (!enrollment) return res.status(404).json({ error: "Enrollment not found" });
  enrollment.published = true;
  enrollment.completedAt = enrollment.completedAt || new Date();
  await enrollment.save();
  res.json(enrollment);
}

// PATCH /api/enrollments/:id/amend
// The only legal way to change a published mark. Requires a reason, writes
// an AuditLog with old/new value, and recomputes the grade. This is the
// enforcement point for the "grade tampering" threat model.
async function amend(req, res) {
  const { kind, marks, reason } = req.body;
  if (!reason || !reason.trim()) {
    return res.status(400).json({ error: "A reason is required to amend a published mark" });
  }

  const enrollment = await Enrollment.findById(req.params.id);
  if (!enrollment) return res.status(404).json({ error: "Enrollment not found" });
  if (!enrollment.published) {
    return res.status(409).json({ error: "Enrollment is not yet published; edit it directly" });
  }

  const idx = enrollment.assessments.findIndex((a) => a.kind === kind);
  if (idx === -1) return res.status(404).json({ error: `No '${kind}' assessment on this enrollment` });

  const oldValue = enrollment.assessments[idx].marks;
  enrollment.assessments[idx].marks = marks;

  const courseDoc = await Course.findById(enrollment.course);
  await computeAndSetGrade(enrollment, courseDoc);
  await enrollment.save();

  await AuditLog.create({
    enrollment: enrollment._id,
    changedBy: req.user.sub,
    field: `assessments.${kind}.marks`,
    oldValue,
    newValue: marks,
    reason,
  });

  res.json(enrollment);
}

// GET /api/enrollments/course/:courseId  — full roster for a course (faculty/hod/admin)
async function rosterForCourse(req, res) {
  const rows = await Enrollment.find({ course: req.params.courseId })
    .populate("student", "name rollNumber")
    .sort({ totalMarks: -1 })
    .lean();
  res.json(rows);
}

module.exports = { createEnrollment, enterMarks, publish, amend, rosterForCourse };
