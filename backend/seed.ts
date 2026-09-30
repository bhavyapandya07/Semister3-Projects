import "dotenv/config";
import mongoose from "mongoose";
import { connectDB } from "./src/db";
import { User } from "./src/models/User";
import { Student } from "./src/models/Student";
import { Course } from "./src/models/Course";
import { Enrollment } from "./src/models/Enrollment";
import { createGradingScheme } from "./src/grading/GradingScheme";

async function seed() {
  await connectDB();
  await Promise.all([User.deleteMany({}), Student.deleteMany({}), Course.deleteMany({}), Enrollment.deleteMany({})]);
  const departments = ["CS", "IT", "ECE"];
  const faculty = await User.create([1, 2, 3].map((n) => ({ name: `Faculty ${n}`, email: `faculty${n}@srms.edu`, passwordHash: "StudentResult!2026", role: "faculty", department: departments[(n - 1) % departments.length] })));
  await User.create({ name: "SRMS Admin", email: "admin@srms.edu", passwordHash: "StudentResult!2026", role: "admin" });
  await User.create({ name: "Head of CS", email: "hod@srms.edu", passwordHash: "StudentResult!2026", role: "hod", department: "CS" });
  const students = await Student.insertMany(Array.from({ length: 2000 }, (_, i) => ({ rollNumber: `R${String(i + 1).padStart(5, "0")}`, name: `Student ${i + 1}`, program: "B.Tech", semester: 1 + i % 8, department: departments[i % departments.length] })));
  await User.create({ name: students[0].name, email: "student1@srms.edu", passwordHash: "StudentResult!2026", role: "student", department: students[0].department, student: students[0]._id });
  const courses = await Course.insertMany(Array.from({ length: 8 }, (_, i) => ({ code: `CSE10${i}`, title: `Course ${i + 1}`, credits: i % 2 ? 4 : 3, maxMarks: 100, department: departments[i % departments.length], faculty: faculty[i % faculty.length]._id, gradingScheme: i % 3 === 0 ? "relative" : "absolute" })));
  for (let offset = 0; offset < 10000; offset += 1000) {
    const docs = Array.from({ length: Math.min(1000, 10000 - offset) }, (_, j) => {
      const i = offset + j;
      const assessments = [{ kind: "internal", marks: (i * 7) % 21, maxMarks: 20 }, { kind: "midterm", marks: (i * 11) % 31, maxMarks: 30 }, { kind: "final", marks: (i * 13) % 51, maxMarks: 50 }];
      const totalMarks = assessments.reduce((sum, a) => sum + a.marks, 0);
      const course = courses[i % courses.length];
      return { student: students[Math.floor(i / courses.length)]._id, course: course._id, semester: 1 + i % 8, assessments, totalMarks, grade: createGradingScheme(course.gradingScheme, 100).computeGrade(totalMarks), published: true, completedAt: new Date(2026, i % 12, 1) };
    });
    await Enrollment.insertMany(docs, { ordered: true });
    console.info(`[seed] ${Math.min(offset + docs.length, 10000)}/10000 enrollments`);
  }
  console.info("Seed complete. Demo accounts (password: StudentResult!2026): admin@srms.edu, hod@srms.edu, faculty1@srms.edu, student1@srms.edu");
  await mongoose.disconnect();
}

seed().catch(async (error) => { console.error(error); await mongoose.disconnect(); process.exitCode = 1; });
