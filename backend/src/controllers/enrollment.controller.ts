import type { RequestHandler } from "express";
import * as service from "../services/enrollment.service";
export const listCourse: RequestHandler = async (req, res) => res.json(await service.listCourseEnrollments(String(req.params.courseId)));
export const get: RequestHandler = async (req, res) => res.json(await service.getEnrollment(String(req.params.id)));
export const create: RequestHandler = async (req, res) => res.status(201).json(await service.createEnrollment(req.body));
export const updateMarks: RequestHandler = async (req, res) => res.json(await service.editMarks(String(req.params.id), req.body.assessments));
export const publish: RequestHandler = async (req, res) => res.json(await service.publishEnrollment(String(req.params.id)));
export const amend: RequestHandler = async (req, res) => res.json(await service.amendEnrollment(String(req.params.id), req.body, req.user!.id));
export const remove: RequestHandler = async (req, res) => { await service.deleteEnrollment(String(req.params.id)); res.status(204).end(); };
