require("dotenv").config();
const mongoose = require("mongoose");
const connectDB = require("../config/db");
const User = require("../models/User");
const Student = require("../models/Student");
const Course = require("../models/Course");
const Enrollment = require("../models/Enrollment");

const DEPARTMENTS = ["CS", "IT", "ECE"];
const N_STUDENTS = 2000;
const N_ENROLLMENTS = 10000;

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

async function run() {
  await connectDB();
  console.log("Clearing existing data...");
  await Promise.all([
    User.deleteMany({}),
    Student.deleteMany({}),
    Course.deleteMany({}),
    Enrollment.deleteMany({}),
  ]);

  console.log("Creating users (admin, hod, faculty)...");
  const passwordHash = await User.hashPassword("password123");
  const admin = await User.create({ name: "Admin", email: "admin@srms.edu", passwordHash, role: "admin" });
  const hod = await User.create({
    name: "Dr. HOD",
    email: "hod@srms.edu",
    passwordHash,
    role: "hod",
    department: "CS",
  });
  const facultyDocs = await User.insertMany(
    Array.from({ length: 5 }, (_, i) => ({
      name: `Faculty ${i + 1}`,
      email: `faculty${i + 1}@srms.edu`,
      passwordHash,
      role: "faculty",
      department: pick(DEPARTMENTS),
    }))
  );

  console.log("Creating courses...");
  const courses = await Course.insertMany(
    Array.from({ length: 8 }, (_, i) => ({
      code: `CSE10${i}`,
      title: `Course ${i + 1}`,
      credits: [3, 4][i % 2],
      maxMarks: 100,
      department: pick(DEPARTMENTS),
      faculty: pick(facultyDocs)._id,
      gradingScheme: i % 3 === 0 ? "relative" : "absolute",
    }))
  );

  console.log(`Creating ${N_STUDENTS} students...`);
  const students = await Student.insertMany(
    Array.from({ length: N_STUDENTS }, (_, i) => ({
      rollNumber: `R${String(i + 1).padStart(5, "0")}`,
      name: `Student ${i + 1}`,
      program: "B.Tech",
      semester: 1 + (i % 8),
      department: pick(DEPARTMENTS),
    }))
  );

  // link one student to a demo login
  const demoStudentUser = await User.create({
    name: students[0].name,
    email: "student1@srms.edu",
    passwordHash,
    role: "student",
    student: students[0]._id,
  });

  console.log(`Creating ${N_ENROLLMENTS} enrollments...`);
  const BATCH = 1000;
  let created = 0;
  while (created < N_ENROLLMENTS) {
    const size = Math.min(BATCH, N_ENROLLMENTS - created);
    const docs = Array.from({ length: size }, () => {
      const internal = Math.floor(Math.random() * 20);
      const midterm = Math.floor(Math.random() * 30);
      const final = Math.floor(Math.random() * 50);
      const totalMarks = internal + midterm + final;
      const grade = totalMarks >= 90 ? "A" : totalMarks >= 80 ? "B" : totalMarks >= 70 ? "C" : totalMarks >= 60 ? "D" : "F";
      return {
        student: pick(students)._id,
        course: pick(courses)._id,
        semester: 1 + Math.floor(Math.random() * 8),
        assessments: [
          { kind: "internal", marks: internal, maxMarks: 20 },
          { kind: "midterm", marks: midterm, maxMarks: 30 },
          { kind: "final", marks: final, maxMarks: 50 },
        ],
        totalMarks,
        grade,
        published: true,
        completedAt: new Date(2026, Math.floor(Math.random() * 12), 1),
      };
    });
    // ordered:false + no unique-index collisions matter here because
    // (student, course) pairs may repeat across random picks in seed data;
    // duplicates are fine for benchmarking purposes, so unset the unique
    // index concern by inserting via insertMany with ordered:false.
    try {
      await Enrollment.insertMany(docs, { ordered: false });
    } catch (e) {
      // ignore duplicate key errors from the (student, course) unique index
    }
    created += size;
    console.log(`  ...${created}/${N_ENROLLMENTS}`);
  }

  console.log("\nSeed complete. Demo logins (password: password123):");
  console.log("  admin@srms.edu   (admin)");
  console.log("  hod@srms.edu     (hod, dept CS)");
  console.log(`  ${facultyDocs[0].email}  (faculty)`);
  console.log(`  student1@srms.edu (student, roll ${students[0].rollNumber})`);

  await mongoose.disconnect();
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
