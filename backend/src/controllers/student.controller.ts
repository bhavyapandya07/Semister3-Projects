import type { RequestHandler } from "express";
import * as service from "../services/student.service";
export const list: RequestHandler = async (req, res) => res.json(await service.listStudentsForViewer(req.user!));
export const eligibleForCourse: RequestHandler = async (req, res) => res.json(await service.listEligibleStudentsForCourse(String(req.params.courseId)));
export const get: RequestHandler = async (req, res) => res.json(await service.getStudent(String(req.params.id)));
export const create: RequestHandler = async (req, res) => res.status(201).json(await service.createStudent(req.body));
export const update: RequestHandler = async (req, res) => res.json(await service.updateStudent(String(req.params.id), req.body));
export const remove: RequestHandler = async (req, res) => { await service.deleteStudent(String(req.params.id)); res.status(204).end(); };
