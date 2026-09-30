import type { RequestHandler } from "express";
import * as service from "../services/course.service";
export const list: RequestHandler = async (req, res) => res.json(await service.listCoursesForViewer(req.user!));
export const get: RequestHandler = async (req, res) => res.json(await service.getCourse(String(req.params.id)));
export const create: RequestHandler = async (req, res) => res.status(201).json(await service.createCourse(req.body));
export const update: RequestHandler = async (req, res) => res.json(await service.updateCourse(String(req.params.id), req.body));
export const remove: RequestHandler = async (req, res) => { await service.deleteCourse(String(req.params.id)); res.status(204).end(); };
