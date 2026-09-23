const Course = require("../models/Course");
const cache = require("./courseOwnershipCache");

/**
 * "Faculty may enter marks for courses they teach" cannot be decided from
 * the JWT alone — it depends on the relationship between req.user and the
 * specific :courseId in the URL. This middleware loads that relationship
 * and decides.
 *
 * Expects the route to have a :courseId param (or req.body.course for
 * bulk-import rows handled elsewhere — see utils/csvImport.js which
 * duplicates this check per-row instead of per-request).
 */
async function ownsCourse(req, res, next) {
  const { role, sub: userId, department } = req.user;
  const courseId = req.params.courseId || req.body.course;
  if (!courseId) return res.status(400).json({ error: "courseId is required" });

  if (role === "admin") return next(); // admin bypasses ownership entirely

  let course = cache.get(courseId);
  if (!course) {
    const doc = await Course.findById(courseId).select("faculty department").lean();
    if (!doc) return res.status(404).json({ error: "Course not found" });
    course = { facultyId: String(doc.faculty), department: doc.department };
    cache.set(courseId, course);
  }

  if (role === "hod") {
    if (course.department !== department) {
      return res.status(403).json({ error: "Course is outside your department" });
    }
    return next();
  }

  if (role === "faculty") {
    if (course.facultyId !== String(userId)) {
      return res.status(403).json({ error: "You do not teach this course" });
    }
    return next();
  }

  // students never reach write endpoints guarded by this middleware
  return res.status(403).json({ error: "Not permitted" });
}

module.exports = ownsCourse;
