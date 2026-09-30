import jwt from "jsonwebtoken";
import type { RequestHandler } from "express";
import type { Role, SessionUser } from "@srms/shared";
import { HttpError } from "./errors";
import { User } from "../models/User";

declare global {
  namespace Express {
    interface Request { user?: SessionUser; }
  }
}

export const authenticate: RequestHandler = (req, _res, next) => {
  const token = req.header("authorization")?.replace(/^Bearer\s+/i, "");
  if (!token) return next(new HttpError(401, "Authentication required"));
  let claims: jwt.JwtPayload;
  try {
    const secret = process.env.JWT_SECRET;
    if (!secret) throw new Error("JWT_SECRET missing");
    claims = jwt.verify(token, secret) as jwt.JwtPayload;
    if (!claims.sub || !claims.role) throw new Error("Invalid token claims");
  } catch {
    return next(new HttpError(401, "Invalid or expired access token"));
  }
  User.findById(String(claims.sub)).select("name email role department student refreshTokenVersion isActive").populate("student", "_id").lean().then((account) => {
    if (!account || !account.isActive || claims.ver !== account.refreshTokenVersion || claims.role !== account.role) return next(new HttpError(401, "Session is no longer active"));
    const student = account.student as unknown as { _id?: unknown } | undefined;
    req.user = { id: String(account._id), name: account.name, email: account.email, role: account.role as Role, department: account.department, studentId: student?._id ? String(student._id) : undefined };
    next();
  }).catch(next);
};

export function authorize(...roles: Role[]): RequestHandler {
  return (req, _res, next) => {
    if (!req.user) return next(new HttpError(401, "Authentication required"));
    if (!roles.includes(req.user.role)) return next(new HttpError(403, "You do not have permission for this action"));
    next();
  };
}
