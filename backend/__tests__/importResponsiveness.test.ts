import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import mongoose from "mongoose";
import { MongoMemoryServer } from "mongodb-memory-server";
import request from "supertest";
import { app } from "../src/app";
import { connectDB } from "../src/db";
import { User } from "../src/models/User";
import { Student } from "../src/models/Student";
import { Course } from "../src/models/Course";
import { Enrollment } from "../src/models/Enrollment";
import { importEnrollments } from "../src/services/import.service";

describe("10,000-row CSV event-loop behavior", () => {
  let memory: MongoMemoryServer;
  let csvPath: string;
  let tempDir: string;

  beforeAll(async () => {
    memory = await MongoMemoryServer.create();
    await connectDB(memory.getUri());
    const faculty = await User.create({ name: "Import Admin", email: "import-admin@test.edu", passwordHash: "ImportTestPassword!2026", role: "admin" });
    const students = await Student.insertMany(Array.from({ length: 100 }, (_, i) => ({ rollNumber: `I${String(i + 1).padStart(5, "0")}`, name: `Import Student ${i + 1}`, program: "B.Tech", semester: 1, department: "CS" })));
    const courses = await Course.insertMany(Array.from({ length: 100 }, (_, i) => ({ code: `I${String(i + 1).padStart(3, "0")}`, title: `Import Course ${i + 1}`, credits: 3, maxMarks: 100, department: "CS", faculty: faculty._id, gradingScheme: "absolute" })));
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "srms-import-"));
    csvPath = path.join(tempDir, "ten-thousand.csv");
    const rows = ["rollNumber,courseCode,semester,internal,midterm,final"];
    for (const student of students) for (const course of courses) rows.push(`${student.rollNumber},${course.code},1,10,20,30`);
    fs.writeFileSync(csvPath, rows.join("\n"));
  }, 60000);

  afterAll(async () => {
    await Enrollment.deleteMany({});
    await mongoose.disconnect();
    await memory.stop();
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  it("serves a health request while the CSV stream imports 10,000 rows", async () => {
    const admin = await User.findOne({ email: "import-admin@test.edu" }).lean();
    let processedRows = 0;
    let healthDuringImport: Promise<{ status: number; body: { ok: boolean }; requestId: string; processedRows: number }> | undefined;
    const operation = importEnrollments(csvPath, { id: String(admin!._id), name: admin!.name, email: admin!.email, role: "admin" }, (count) => {
      processedRows = count;
      if (count === 500) healthDuringImport = request(app).get("/api/health").then((response) => ({ status: response.status, body: response.body, requestId: response.headers["x-request-id"], processedRows }));
    });
    const result = await operation;
    const health = await healthDuringImport!;
    expect(health.status).toBe(200);
    expect(health.body.ok).toBe(true);
    expect(health.requestId).toBeTruthy();
    expect(health.processedRows).toBeLessThan(10000);
    expect(result.imported).toBe(10000);
    expect(result.failed).toHaveLength(0);
  }, 60000);
});
