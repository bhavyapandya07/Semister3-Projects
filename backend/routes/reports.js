const express = require("express");
const { requireAuth, requireRole } = require("../middleware/auth");
const ownsCourse = require("../middleware/ownsCourse");
const ctrl = require("../controllers/reportController");

const router = express.Router();
router.use(requireAuth);

// Aggregate course reports: faculty only for courses they teach, hod for
// their department, admin for anything. Students never see aggregate
// course-level reports (spec: "read aggregate reports for those courses"
// is a faculty/hod/admin privilege).
router.get(
  "/course/:courseId/summary",
  requireRole("faculty", "hod", "admin"),
  ownsCourse,
  ctrl.courseSummary
);
router.get(
  "/course/:courseId/histogram",
  requireRole("faculty", "hod", "admin"),
  ownsCourse,
  ctrl.courseHistogram
);

// IDOR-critical: a student may only ever fetch their OWN transcript.
// This 403 is the single most important check in the project.
router.get("/student/:studentId/transcript", (req, res, next) => {
  if (req.user.role === "student" && req.params.studentId !== req.user.studentId) {
    return res.status(403).json({ error: "You may only view your own transcript" });
  }
  next();
}, ctrl.studentTranscript);

// Toppers is readable by everyone, but the controller itself narrows the
// $project for role=student (rank-only, no classmates' marks).
router.get("/toppers", ctrl.toppers);

// Course-level toppers: faculty/hod/admin via ownsCourse; a student may
// only view it for a course they're actually enrolled in (checked here,
// not skipped) — the controller then narrows the projection to rank-only.
const Enrollment = require("../models/Enrollment");
router.get(
  "/course/:courseId/toppers",
  async (req, res, next) => {
    if (req.user.role === "student") {
      const isEnrolled = await Enrollment.exists({
        course: req.params.courseId,
        student: req.user.studentId,
      });
      if (!isEnrolled) return res.status(403).json({ error: "Not enrolled in this course" });
      return next();
    }
    return ownsCourse(req, res, next);
  },
  ctrl.courseToppers
);

router.get("/enrollments-by-month", requireRole("faculty", "hod", "admin"), ctrl.enrollmentsByMonth);

module.exports = router;
