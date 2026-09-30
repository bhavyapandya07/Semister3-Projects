import { Router } from "express";
import { rateLimit } from "express-rate-limit";
import { z } from "zod";
import * as ctrl from "../controllers/auth.controller";
import { authenticate } from "../middleware/authenticate";
import { asyncRoute } from "../middleware/errors";
import { validateBody } from "../middleware/validate";

const router = Router();
const loginLimit = rateLimit({ windowMs: 15 * 60 * 1000, limit: 5, standardHeaders: true, legacyHeaders: false, message: { error: "Too many login attempts. Try again in 15 minutes." } });
router.post("/register", validateBody(z.object({ name: z.string().min(1), email: z.string().email(), password: z.string().min(12), rollNumber: z.string().min(1) })), asyncRoute(ctrl.register));
router.post("/login", loginLimit, validateBody(z.object({ email: z.string().email(), password: z.string().min(1) })), asyncRoute(ctrl.login));
router.post("/refresh", asyncRoute(ctrl.refresh));
router.post("/logout", asyncRoute(ctrl.logout));
router.get("/me", authenticate, asyncRoute(ctrl.me));
router.patch("/password", authenticate, validateBody(z.object({ currentPassword: z.string(), newPassword: z.string().min(12) })), asyncRoute(ctrl.password));
export default router;
