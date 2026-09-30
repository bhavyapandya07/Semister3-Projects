import type { RequestHandler } from "express";
import * as service from "../services/report.service";
export const summary: RequestHandler = async (req, res) => res.json(await service.courseSummary(String(req.params.courseId)));
export const histogram: RequestHandler = async (req, res) => res.json(await service.courseHistogram(String(req.params.courseId)));
export const transcript: RequestHandler = async (req, res) => res.json(await service.transcript(String(req.params.studentId)));
export const toppers: RequestHandler = async (req, res) => res.json(await service.toppers(Number(req.query.semester ?? 4), Number(req.query.limit ?? 10), undefined, req.user?.role === "student"));
export const courseToppers: RequestHandler = async (req, res) => res.json(await service.toppers(Number(req.query.semester ?? 4), Number(req.query.limit ?? 10), String(req.params.courseId), req.user?.role === "student"));
export const byMonth: RequestHandler = async (req, res) => res.json(await service.enrollmentsByMonth(Number(req.query.year ?? new Date().getFullYear()), req.user));
