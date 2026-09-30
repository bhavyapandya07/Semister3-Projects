import { Router } from "express";
import { z } from "zod";
import * as ctrl from "../controllers/report.controller";
import { authenticate, authorize } from "../middleware/authenticate";
import { asyncRoute } from "../middleware/errors";
import { canReadCourseToppers, ownsCourse, ownsTranscript } from "../middleware/ownership";

const router = Router();
router.use(authenticate);
router.get("/course/:courseId/summary", authorize("faculty", "hod", "admin"), ownsCourse, asyncRoute(ctrl.summary));
router.get("/course/:courseId/histogram", authorize("faculty", "hod", "admin"), ownsCourse, asyncRoute(ctrl.histogram));
router.get("/student/:studentId/transcript", ownsTranscript, asyncRoute(ctrl.transcript));
router.get("/toppers", asyncRoute(ctrl.toppers));
router.get("/course/:courseId/toppers", canReadCourseToppers, asyncRoute(ctrl.courseToppers));
router.get("/enrollments-by-month", authorize("faculty", "hod", "admin"), asyncRoute(ctrl.byMonth));
export default router;
