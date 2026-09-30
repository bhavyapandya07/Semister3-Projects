import { Types } from "mongoose";
import type { RequestHandler } from "express";
import { Course } from "../models/Course";
import { Enrollment } from "../models/Enrollment";
import { Student } from "../models/Student";
import { HttpError } from "./errors";

export const ownsCourse: RequestHandler = async (req, _res, next) => {
  try {
    if (!req.user) throw new HttpError(401, "Authentication required");
    const course = await Course.findById(req.params.courseId ?? req.params.id).select("faculty department").lean();
    if (!course) throw new HttpError(404, "Course not found");
    if (req.user.role === "admin") return next();
    const allowed = req.user.role === "hod"
      ? course.department === req.user.department
      : req.user.role === "faculty" && String(course.faculty) === req.user.id;
    if (!allowed) throw new HttpError(403, "You do not own this course");
    next();
  } catch (err) { next(err); }
};

export const ownsStudentRecord: RequestHandler = async (req, _res, next) => {
  try {
    if (!req.user) throw new HttpError(401, "Authentication required");
    const student = await Student.findById(req.params.id).select("department").lean();
    if (!student) throw new HttpError(404, "Student not found");
    if (req.user.role === "admin") return next();
    if (req.user.role === "student" && req.user.studentId === req.params.id) return next();
    if (req.user.role === "hod" && student.department === req.user.department) return next();
    if (req.user.role === "faculty") {
      const courses = await Course.find({ faculty: req.user.id }).distinct("_id");
      if (await Enrollment.exists({ student: student._id, course: { $in: courses } })) return next();
    }
    throw new HttpError(403, "You may only view students in your assigned courses or department");
  } catch (err) { next(err); }
};

export const ownsTranscript: RequestHandler = (req, _res, next) => {
  const actor = req.user;
  if (!actor) return next(new HttpError(401, "Authentication required"));
  if (actor.role === "student") return actor.studentId === req.params.studentId ? next() : next(new HttpError(403, "You may only view your own transcript"));
  if (actor.role === "admin") return next();
  void Student.findById(req.params.studentId).select("department").lean().then(async (student) => {
    if (!student) return next(new HttpError(404, "Student not found"));
    if (actor.role === "hod" && student.department === actor.department) return next();
    if (actor.role === "faculty") {
      const courseIds = await Course.find({ faculty: actor.id }).distinct("_id");
      if (await Enrollment.exists({ student: student._id, course: { $in: courseIds } })) return next();
    }
    next(new HttpError(403, "You may only view transcripts in your assigned courses or department"));
  }).catch(next);
};

export const canReadCourseToppers: RequestHandler = async (req, res, next) => {
  if (req.user?.role !== "student") return ownsCourse(req, res, next);
  try {
    const enrolled = await Enrollment.exists({ course: req.params.courseId, student: req.user.studentId });
    if (!enrolled) throw new HttpError(403, "Not enrolled in this course");
    next();
  } catch (err) { next(err); }
};

export const ownsEnrollmentRead: RequestHandler = async (req, _res, next) => {
  try {
    const row = await Enrollment.findById(req.params.id).select("student course").lean();
    if (!row) throw new HttpError(404, "Enrollment not found");
    if (req.user?.role === "student") {
      if (String(row.student) !== req.user.studentId) throw new HttpError(403, "You may only view your own marks");
      return next();
    }
    req.params.courseId = String(row.course);
    ownsCourse(req, _res, next);
  } catch (err) { next(err); }
};

export const ownsSubmittedCourse: RequestHandler = (req, res, next) => {
  req.params.courseId = String(req.body.course);
  ownsCourse(req, res, next);
};

export const ownsEnrollmentCourse: RequestHandler = async (req, _res, next) => {
  try {
    const enrollment = await Enrollment.findById(req.params.id).select("course").lean();
    if (!enrollment) throw new HttpError(404, "Enrollment not found");
    req.params.courseId = String(enrollment.course);
    ownsCourse(req, _res, next);
  } catch (err) { next(err); }
};

export function validObjectId(value: string): boolean { return Types.ObjectId.isValid(value); }
