const express = require("express");
const multer = require("multer");
const { requireAuth, requireRole } = require("../middleware/auth");
const ownsCourse = require("../middleware/ownsCourse");
const ownsEnrollmentCourse = require("../middleware/ownsEnrollmentCourse");
const ctrl = require("../controllers/enrollmentController");
const { importCsv } = require("../controllers/importController");

const upload = multer({ dest: "uploads/" });
const router = express.Router();
router.use(requireAuth);

router.get("/course/:courseId", requireRole("faculty", "hod", "admin"), ownsCourse, ctrl.rosterForCourse);
router.post("/", requireRole("faculty", "hod", "admin"), ownsCourse, ctrl.createEnrollment);
router.put("/:id/marks", requireRole("faculty", "hod", "admin"), ownsEnrollmentCourse, ctrl.enterMarks);
router.post("/:id/publish", requireRole("faculty", "hod", "admin"), ownsEnrollmentCourse, ctrl.publish);
router.patch("/:id/amend", requireRole("faculty", "hod", "admin"), ownsEnrollmentCourse, ctrl.amend);

router.post(
  "/import",
  requireRole("faculty", "hod", "admin"),
  upload.single("file"),
  importCsv
);

module.exports = router;
