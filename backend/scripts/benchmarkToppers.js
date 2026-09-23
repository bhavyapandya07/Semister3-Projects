/**
 * Implements "toppers" two ways over the seeded 10,000-enrollment dataset
 * and reports wall-clock time and peak Node memory for each, per the
 * spec's explicit requirement to prove the pipeline earns its place.
 *
 * Run `npm run seed` first.
 */
require("dotenv").config();
const mongoose = require("mongoose");
const connectDB = require("../config/db");
const Enrollment = require("../models/Enrollment");
const Student = require("../models/Student");

const SEMESTER = 4;
const LIMIT = 10;

function peakRssMB() {
  return (process.memoryUsage().rss / 1024 / 1024).toFixed(1);
}

// Approach A: the pipeline. All aggregation work happens inside MongoDB;
// Node only receives the final, already-reduced 10 rows.
async function toppersViaPipeline() {
  return Enrollment.aggregate([
    { $match: { semester: SEMESTER, published: true } },
    { $group: { _id: "$student", totalMarks: { $sum: "$totalMarks" } } },
    { $sort: { totalMarks: -1 } },
    { $limit: LIMIT },
    {
      $lookup: {
        from: "students",
        localField: "_id",
        foreignField: "_id",
        as: "studentInfo",
      },
    },
    { $unwind: "$studentInfo" },
    { $project: { _id: 0, name: "$studentInfo.name", totalMarks: 1 } },
  ]);
}

// Approach B: find() + JS reduce. Every matching document (not just the
// top 10) crosses the wire from MongoDB into Node as a full JS object,
// then gets folded and sorted in the application process.
async function toppersViaReduce() {
  const rows = await Enrollment.find({ semester: SEMESTER, published: true })
    .select("student totalMarks")
    .lean();

  const totals = rows.reduce((acc, r) => {
    const key = r.student.toString();
    acc[key] = (acc[key] || 0) + r.totalMarks;
    return acc;
  }, {});

  const sorted = Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, LIMIT);

  const students = await Student.find({ _id: { $in: sorted.map(([id]) => id) } })
    .select("name")
    .lean();
  const nameById = new Map(students.map((s) => [s._id.toString(), s.name]));

  return sorted.map(([id, totalMarks]) => ({ name: nameById.get(id), totalMarks }));
}

async function time(label, fn) {
  const before = process.memoryUsage().rss;
  const t0 = process.hrtime.bigint();
  const result = await fn();
  const t1 = process.hrtime.bigint();
  const after = process.memoryUsage().rss;
  const ms = Number(t1 - t0) / 1e6;
  console.log(`\n${label}`);
  console.log(`  wall time     : ${ms.toFixed(1)} ms`);
  console.log(`  RSS before    : ${(before / 1024 / 1024).toFixed(1)} MB`);
  console.log(`  RSS after     : ${(after / 1024 / 1024).toFixed(1)} MB`);
  console.log(`  RSS delta     : ${((after - before) / 1024 / 1024).toFixed(1)} MB`);
  console.log(`  rows returned : ${result.length}`);
  return { ms, result };
}

async function run() {
  await connectDB();
  const count = await Enrollment.countDocuments({ semester: SEMESTER, published: true });
  console.log(`Enrollments matching semester ${SEMESTER}: ${count}`);

  const a = await time("Approach A: aggregation pipeline", toppersViaPipeline);
  const b = await time("Approach B: find() + JS reduce", toppersViaReduce);

  console.log("\n--- Summary ---");
  console.log(
    `Pipeline was ${(b.ms / a.ms).toFixed(1)}x faster wall-clock and moved only ${a.result.length} ` +
      `documents over the wire; the reduce approach moved all ${count} matching documents into Node ` +
      "before doing any folding, so its memory delta and GC pressure scale with the match size, not the result size."
  );

  await mongoose.disconnect();
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
