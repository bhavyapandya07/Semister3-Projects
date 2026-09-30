import { Router } from "express";
import { z } from "zod";
import * as ctrl from "../controllers/course.controller";
import { authenticate, authorize } from "../middleware/authenticate";
import { asyncRoute } from "../middleware/errors";
import { ownsCourse } from "../middleware/ownership";
import { validateBody } from "../middleware/validate";

const router = Router();
router.use(authenticate);
router.get("/", authorize("faculty", "hod", "admin"), asyncRoute(ctrl.list));
router.get("/:id", ownsCourse, asyncRoute(ctrl.get));
const courseInput = z.object({ code: z.string().min(1), title: z.string().min(1), credits: z.number().int().min(1), maxMarks: z.number().positive(), department: z.string().min(1), faculty: z.string().min(1), gradingScheme: z.enum(["absolute", "relative"]).default("absolute") });
router.post("/", authorize("admin"), validateBody(courseInput), asyncRoute(ctrl.create));
router.put("/:id", authorize("admin"), validateBody(courseInput.partial()), asyncRoute(ctrl.update));
router.delete("/:id", authorize("admin"), asyncRoute(ctrl.remove));
export default router;
