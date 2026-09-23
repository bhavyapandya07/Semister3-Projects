const fs = require("fs");
const { importEnrollmentsFromCsv } = require("../utils/csvImport");

// POST /api/enrollments/import  (multipart/form-data, field name "file")
async function importCsv(req, res) {
  if (!req.file) return res.status(400).json({ error: "No file uploaded (field name 'file')" });

  try {
    const result = await importEnrollmentsFromCsv(req.file.path, req.user, (progress) => {
      console.log(`[import] processed ${progress.processed} rows`);
    });
    res.json({
      imported: result.imported,
      failedCount: result.failed.length,
      failures: result.failed,
    });
  } finally {
    fs.unlink(req.file.path, () => {});
  }
}

module.exports = { importCsv };
