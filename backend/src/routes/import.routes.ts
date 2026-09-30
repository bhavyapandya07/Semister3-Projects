import { Router } from "express";
import fs from "node:fs";
import multer from "multer";
import { authenticate, authorize } from "../middleware/authenticate";
import { asyncRoute } from "../middleware/errors";
import { importCsv } from "../controllers/import.controller";

fs.mkdirSync("uploads", { recursive: true });
const upload = multer({ dest: "uploads/", limits: { fileSize: 50 * 1024 * 1024 }, fileFilter: (_req, file, done) => done(null, file.mimetype === "text/csv" || file.originalname.toLowerCase().endsWith(".csv")) });
const router = Router();
router.use(authenticate, authorize("faculty", "hod", "admin"));
router.post("/", upload.single("file"), asyncRoute(importCsv));
export default router;
