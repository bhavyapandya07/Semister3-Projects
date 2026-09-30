import fs from "node:fs";
import type { RequestHandler } from "express";
import { importEnrollments } from "../services/import.service";

export const importCsv: RequestHandler = async (req, res) => {
  if (!req.file) { res.status(400).json({ error: "Upload a CSV file in the 'file' field" }); return; }
  try {
    const result = await importEnrollments(req.file.path, req.user!, (count) => console.info(`[import] ${count} rows processed`));
    res.json({ imported: result.imported, failedCount: result.failed.length, failures: result.failed });
  } finally { fs.unlink(req.file.path, () => undefined); }
};
