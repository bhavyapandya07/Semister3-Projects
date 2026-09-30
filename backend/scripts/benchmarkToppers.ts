import "dotenv/config";
import mongoose from "mongoose";
import { connectDB } from "../src/db";
import { Enrollment } from "../src/models/Enrollment";

async function measure(name: string, run: () => Promise<unknown>) {
  global.gc?.();
  const before = process.memoryUsage().rss;
  let peakRss = before;
  const watcher = setInterval(() => { peakRss = Math.max(peakRss, process.memoryUsage().rss); }, 5);
  const started = performance.now();
  const result = await run();
  clearInterval(watcher);
  peakRss = Math.max(peakRss, process.memoryUsage().rss);
  const elapsedMs = performance.now() - started;
  const rssDeltaBytes = process.memoryUsage().rss - before;
  console.log(JSON.stringify({ name, elapsedMs: Number(elapsedMs.toFixed(2)), rssDeltaBytes, peakRssBytes: peakRss, peakDeltaBytes: peakRss - before, returnedRows: Array.isArray(result) ? result.length : null }));
}

async function run() {
  await connectDB();
  await measure("aggregation-pipeline", () => Enrollment.aggregate([
    { $group: { _id: "$student", totalMarks: { $sum: "$totalMarks" } } },
    { $sort: { totalMarks: -1 } }, { $limit: 10 },
    { $lookup: { from: "students", localField: "_id", foreignField: "_id", as: "student" } },
    { $unwind: "$student" }, { $project: { name: "$student.name", totalMarks: 1 } },
  ]));
  await measure("find-and-js-reduce", async () => {
    const rows = await Enrollment.find({}).select("student totalMarks").lean();
    const totals = new Map<string, number>();
    for (const row of rows) totals.set(String(row.student), (totals.get(String(row.student)) ?? 0) + row.totalMarks);
    return [...totals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);
  });
  await mongoose.disconnect();
}
run().catch(async (error) => { console.error(error); await mongoose.disconnect(); process.exitCode = 1; });
