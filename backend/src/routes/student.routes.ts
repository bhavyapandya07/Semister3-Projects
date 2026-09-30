import { Router } from "express";
import { z } from "zod";
import * as ctrl from "../controllers/student.controller";
import { authenticate, authorize } from "../middleware/authenticate";
import { asyncRoute } from "../middleware/errors";
import { validateBody } from "../middleware/validate";
import { ownsStudentRecord } from "../middleware/ownership";
import { ownsCourse } from "../middleware/ownership";

const router = Router();
router.use(authenticate);
router.get("/", authorize("faculty", "hod", "admin"), asyncRoute(ctrl.list));
router.get("/eligible-for-course/:courseId", authorize("faculty", "hod", "admin"), ownsCourse, asyncRoute(ctrl.eligibleForCourse));
router.get("/:id", ownsStudentRecord, asyncRoute(ctrl.get));
const studentInput = z.object({ rollNumber: z.string().min(1), name: z.string().min(1), program: z.string().min(1), semester: z.number().int().min(1).max(12), department: z.string().min(1) });
router.post("/", authorize("admin"), validateBody(studentInput), asyncRoute(ctrl.create));
router.put("/:id", authorize("admin"), validateBody(studentInput.partial()), asyncRoute(ctrl.update));
router.delete("/:id", authorize("admin"), asyncRoute(ctrl.remove));
export default router;
