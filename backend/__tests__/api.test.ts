import request from "supertest";
import jwt from "jsonwebtoken";
import mongoose from "mongoose";
import { MongoMemoryServer } from "mongodb-memory-server";
import { app } from "../src/app";
import { User } from "../src/models/User";
import { Student } from "../src/models/Student";
import { Course } from "../src/models/Course";
import { Enrollment } from "../src/models/Enrollment";
import { AuditLog } from "../src/models/AuditLog";
import type { Role } from "@srms/shared";

let memory: MongoMemoryServer;
let ids: Record<Role, string>;
let facultyId: string;
let ownStudentId: string;
let otherStudentId: string;
let courseId: string;
const password = "TestPassword!2026";

async function loginAs(role: Role) {
  const id = ids[role];
  const user = await User.findById(id).lean();
  return jwt.sign({ sub: id, name: user?.name, email: user?.email, role, department: user?.department, studentId: role === "student" ? ownStudentId : undefined, ver: user?.refreshTokenVersion ?? 0 }, process.env.JWT_SECRET!, { expiresIn: "1h" });
}
const auth = (token: string) => ({ Authorization: `Bearer ${token}` });

beforeAll(async () => {
  process.env.JWT_SECRET = "a-test-secret-with-more-than-thirty-two-characters";
  memory = await MongoMemoryServer.create();
  await mongoose.connect(memory.getUri());
  const own = await Student.create({ rollNumber: "R00001", name: "Own Student", program: "B.Tech", semester: 4, department: "CS" });
  const other = await Student.create({ rollNumber: "R00002", name: "Other Student", program: "B.Tech", semester: 4, department: "CS" });
  ownStudentId = String(own._id); otherStudentId = String(other._id);
  const admin = await User.create({ name: "Admin", email: "admin@test.edu", passwordHash: password, role: "admin" });
  const hod = await User.create({ name: "HOD", email: "hod@test.edu", passwordHash: password, role: "hod", department: "CS" });
  const faculty = await User.create({ name: "Faculty", email: "faculty@test.edu", passwordHash: password, role: "faculty", department: "CS" });
  const student = await User.create({ name: "Student", email: "student@test.edu", passwordHash: password, role: "student", student: own._id, department: "CS" });
  ids = { admin: String(admin._id), hod: String(hod._id), faculty: String(faculty._id), student: String(student._id) };
  facultyId = String(faculty._id);
  const course = await Course.create({ code: "CS101", title: "Algorithms", credits: 3, maxMarks: 100, department: "CS", faculty: faculty._id, gradingScheme: "absolute" });
  courseId = String(course._id);
}, 60000);

afterAll(async () => { await mongoose.disconnect(); await memory.stop(); });

describe("authentication and authorization", () => {
  it("rejects a protected request without a token (401)", async () => { await request(app).get("/api/students").expect(401); });
  it("rejects a valid token with the wrong role (403)", async () => { await request(app).post("/api/students").set(auth(await loginAs("student"))).send({}).expect(403); });
  it("blocks a student from another student's transcript (IDOR, 403)", async () => { await request(app).get(`/api/reports/student/${otherStudentId}/transcript`).set(auth(await loginAs("student"))).expect(403); });
  it("rejects an expired access token", async () => {
    const token = jwt.sign({ sub: ids.admin, role: "admin", ver: 0 }, process.env.JWT_SECRET!, { expiresIn: -1 });
    await request(app).get("/api/auth/me").set(auth(token)).expect(401);
  });
  it("rejects a token with a tampered signature", async () => {
    const token = await loginAs("admin");
    await request(app).get("/api/auth/me").set(auth(`${token.slice(0, -1)}x`)).expect(401);
  });
  it("rotates the HttpOnly refresh cookie and rejects its replay", async () => {
    const login = await request(app).post("/api/auth/login").send({ email: "admin@test.edu", password }).expect(200);
    const cookies = login.headers["set-cookie"];
    const cookieHeader = Array.isArray(cookies) ? cookies[0] : cookies;
    const oldCookie = String(cookieHeader).split(";")[0];
    expect(cookieHeader).toMatch(/HttpOnly/i);
    const rotated = await request(app).post("/api/auth/refresh").set("Cookie", oldCookie).expect(200);
    expect(rotated.body.token).toBeTruthy();
    await request(app).post("/api/auth/refresh").set("Cookie", oldCookie).expect(401);
  });
  it("uses the same login failure response for unknown email and wrong password", async () => {
    const missing = await request(app).post("/api/auth/login").send({ email: "absent@test.edu", password }).expect(401);
    const wrong = await request(app).post("/api/auth/login").send({ email: "admin@test.edu", password: "wrong password" }).expect(401);
    expect(missing.body.error).toBe(wrong.body.error);
  });
  it("invalidates an access token after password change", async () => {
    const token = await loginAs("admin");
    await request(app).patch("/api/auth/password").set(auth(token)).send({ currentPassword: password, newPassword: "ChangedPassword!2026" }).expect(204);
    await request(app).get("/api/auth/me").set(auth(token)).expect(401);
  });
});

describe("primary resource CRUD and result pipelines", () => {
  it("creates, reads, updates, and deletes a student", async () => {
    const token = await loginAs("admin");
    const created = await request(app).post("/api/students").set(auth(token)).send({ rollNumber: "R01000", name: "New Student", program: "B.Tech", semester: 2, department: "CS" }).expect(201);
    await request(app).get(`/api/students/${created.body._id}`).set(auth(token)).expect(200);
    await request(app).put(`/api/students/${created.body._id}`).set(auth(token)).send({ name: "Updated Student" }).expect(200);
    await request(app).delete(`/api/students/${created.body._id}`).set(auth(token)).expect(204);
  });

  it("creates, reads, updates, and deletes a course", async () => {
    const token = await loginAs("admin");
    const created = await request(app).post("/api/courses").set(auth(token)).send({ code: "CS202", title: "Databases", credits: 4, maxMarks: 100, department: "CS", faculty: facultyId, gradingScheme: "absolute" }).expect(201);
    await request(app).get(`/api/courses/${created.body._id}`).set(auth(token)).expect(200);
    await request(app).put(`/api/courses/${created.body._id}`).set(auth(token)).send({ title: "Advanced Databases" }).expect(200);
    await request(app).delete(`/api/courses/${created.body._id}`).set(auth(token)).expect(204);
  });

  it("creates, reads, updates, and deletes an enrollment, and returns 409 for duplicates", async () => {
    const token = await loginAs("admin");
    const payload = { student: otherStudentId, course: courseId, semester: 4, assessments: [{kind:"internal",marks:18,maxMarks:20},{kind:"midterm",marks:26,maxMarks:30},{kind:"final",marks:42,maxMarks:50}] };
    const created = await request(app).post("/api/enrollments").set(auth(token)).send(payload).expect(201);
    await request(app).get(`/api/enrollments/${created.body._id}`).set(auth(token)).expect(200);
    await request(app).post("/api/enrollments").set(auth(token)).send(payload).expect(409);
    await request(app).put(`/api/enrollments/${created.body._id}/marks`).set(auth(token)).send({ assessments: payload.assessments }).expect(200);
    await request(app).post(`/api/enrollments/${created.body._id}/publish`).set(auth(token)).expect(200);
    await request(app).patch(`/api/enrollments/${created.body._id}/amend`).set(auth(token)).send({ kind: "final", marks: 40, reason: "Correction approved" }).expect(200);
    expect(await AuditLog.countDocuments({ enrollment: created.body._id })).toBe(1);
    await request(app).delete(`/api/enrollments/${created.body._id}`).set(auth(token)).expect(204);
  });

  it("returns 404 and 422 with useful HTTP semantics", async () => {
    const token = await loginAs("admin");
    await request(app).get(`/api/students/${new mongoose.Types.ObjectId()}`).set(auth(token)).expect(404);
    await request(app).post("/api/students").set(auth(token)).send({ name: "missing fields" }).expect(422);
  });

  it("executes the report aggregation pipeline", async () => {
    await Enrollment.create({ student: ownStudentId, course: courseId, semester: 4, assessments: [{kind:"internal",marks:18,maxMarks:20},{kind:"midterm",marks:25,maxMarks:30},{kind:"final",marks:40,maxMarks:50}], totalMarks: 83, grade: "B" });
    const summary = await request(app).get(`/api/reports/course/${courseId}/summary`).set(auth(await loginAs("admin"))).expect(200);
    expect(summary.body.count).toBe(1);
    expect(summary.body.average).toBe(83);
  });
});
