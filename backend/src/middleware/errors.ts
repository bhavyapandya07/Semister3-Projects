import type { ErrorRequestHandler, RequestHandler } from "express";

export class HttpError extends Error {
  constructor(public status: number, message: string, public details?: unknown) { super(message); }
}

export const asyncRoute = (fn: RequestHandler): RequestHandler => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

export const errorHandler: ErrorRequestHandler = (err: unknown, _req, res, _next) => {
  const error = err as { status?: number; message?: string; name?: string; code?: number; errors?: unknown };
  if (error.code === 11000) {
    res.status(409).json({ error: "A record with that unique value already exists" });
    return;
  }
  if (error.name === "ValidationError" || error.name === "CastError") {
    res.status(422).json({ error: error.message ?? "Validation failed", details: error.errors });
    return;
  }
  const status = error.status && error.status >= 400 && error.status < 600 ? error.status : 500;
  if (status >= 500) console.error("[request-error]", error.message ?? "Unknown server error");
  res.status(status).json({ error: status >= 500 ? "Internal server error" : (error.message ?? "Request failed") });
};

export const notFound: RequestHandler = (req, _res, next) => next(new HttpError(404, `No route for ${req.method} ${req.path}`));
