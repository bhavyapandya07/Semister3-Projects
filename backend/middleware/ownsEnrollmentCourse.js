const Enrollment = require("../models/Enrollment");
const ownsCourse = require("./ownsCourse");

/**
 * Marks-entry routes are keyed by :id (the enrollment), not :courseId.
 * Resolve the enrollment's course first, then delegate to the same
 * ownership logic ownsCourse uses — one rule, one implementation.
 */
async function ownsEnrollmentCourse(req, res, next) {
  const enrollment = await Enrollment.findById(req.params.id).select("course").lean();
  if (!enrollment) return res.status(404).json({ error: "Enrollment not found" });
  req.params.courseId = String(enrollment.course);
  return ownsCourse(req, res, next);
}

module.exports = ownsEnrollmentCourse;
