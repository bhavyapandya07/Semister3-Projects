const fs = require("fs");
const csv = require("csv-parser");
const Course = require("../models/Course");
const Student = require("../models/Student");
const Enrollment = require("../models/Enrollment");
const { createGradingScheme } = require("../grading/GradingScheme");

const BATCH_SIZE = 500;

/**
 * Streams a CSV of rows shaped like:
 *   rollNumber,courseCode,semester,internal,midterm,final
 *
 * Why streaming + bulkWrite instead of reading the whole file into an
 * array: a 10,000-row file read with fs.readFileSync and processed with a
 * for-loop of individual .save() calls blocks the event loop for the
 * duration and issues 10,000 round trips. Here, csv-parser emits rows
 * incrementally off the same event loop the server uses for everything
 * else, and rows are buffered into BATCH_SIZE-sized bulkWrite calls — a
 * handful of round trips total, with natural yield points between them
 * where other requests get serviced.
 *
 * Authorization: a faculty uploader can only import rows for courses they
 * teach. This is checked per row (a single CSV can legitimately mix
 * courses), not once for the whole file, and a rejected row does not
 * abort the batch — it's reported and the import continues.
 *
 * @param {string} filePath - path to the uploaded CSV (on disk via multer)
 * @param {{sub: string, role: string}} uploader - req.user
 * @param {(progress: {processed: number, total?: number}) => void} onProgress
 * @returns {Promise<{imported: number, failed: {row: number, reason: string}[]}>}
 */
async function importEnrollmentsFromCsv(filePath, uploader, onProgress) {
  // Pre-load the uploader's own course set once (cheap: faculty teach a
  // handful of courses), so per-row auth is a Set lookup, not a query.
  const courseFilter =
    uploader.role === "admin" ? {} : { faculty: uploader.role === "faculty" ? uploader.sub : undefined };
  const myCourses = await Course.find(courseFilter).select("code maxMarks gradingScheme").lean();
  const courseByCode = new Map(myCourses.map((c) => [c.code, c]));
  const allowAnyCourse = uploader.role === "admin";

  let batch = [];
  let processed = 0;
  let imported = 0;
  const failed = [];

  async function flush() {
    if (batch.length === 0) return;
    const ops = batch.map((doc) => ({
      updateOne: {
        filter: { student: doc.student, course: doc.course },
        update: { $set: doc },
        upsert: true,
      },
    }));
    const result = await Enrollment.bulkWrite(ops, { ordered: false });
    imported += (result.upsertedCount || 0) + (result.modifiedCount || 0);
    batch = [];
  }

  return new Promise((resolve, reject) => {
    const rows = [];
    let rowNum = 0;

    const stream = fs
      .createReadStream(filePath)
      .pipe(csv())
      .on("data", (row) => {
        rowNum += 1;
        rows.push({ rowNum, row });
        // Backpressure: pause the stream while we resolve student/course
        // lookups and grading for this chunk, so memory stays bounded on
        // very large files instead of buffering everything at once.
        if (rows.length >= BATCH_SIZE) {
          stream.pause();
          processChunk(rows.splice(0, rows.length)).then(() => stream.resume());
        }
      })
      .on("end", async () => {
        await processChunk(rows.splice(0, rows.length));
        await flush();
        resolve({ imported, failed });
      })
      .on("error", reject);

    async function processChunk(chunk) {
      for (const { rowNum, row } of chunk) {
        try {
          const course = courseByCode.get(row.courseCode);
          if (!allowAnyCourse && !course) {
            failed.push({ row: rowNum, reason: `You do not teach course '${row.courseCode}'` });
            continue;
          }
          const resolvedCourse = course || (await Course.findOne({ code: row.courseCode }).lean());
          if (!resolvedCourse) {
            failed.push({ row: rowNum, reason: `Unknown course code '${row.courseCode}'` });
            continue;
          }
          const student = await Student.findOne({ rollNumber: row.rollNumber }).select("_id").lean();
          if (!student) {
            failed.push({ row: rowNum, reason: `Unknown student roll number '${row.rollNumber}'` });
            continue;
          }

          const assessments = ["internal", "midterm", "final"]
            .filter((k) => row[k] !== undefined && row[k] !== "")
            .map((k) => ({ kind: k, marks: Number(row[k]), maxMarks: resolvedCourse.maxMarks }));
          const totalMarks = assessments.reduce((s, a) => s + a.marks, 0);
          const scheme = createGradingScheme(resolvedCourse.gradingScheme, resolvedCourse.maxMarks);
          const grade = scheme.computeGrade(totalMarks);

          batch.push({
            student: student._id,
            course: resolvedCourse._id,
            semester: Number(row.semester),
            assessments,
            totalMarks,
            grade,
            completedAt: new Date(),
          });

          if (batch.length >= BATCH_SIZE) await flush();
        } catch (err) {
          failed.push({ row: rowNum, reason: err.message });
        }
        processed += 1;
      }
      onProgress?.({ processed });
    }
  });
}

module.exports = { importEnrollmentsFromCsv };
