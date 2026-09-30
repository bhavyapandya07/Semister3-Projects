import { randomUUID } from "node:crypto";
import type { RequestHandler } from "express";

export const requestMetadata: RequestHandler = (_req, res, next) => {
  const started = Date.now();
  const requestId = randomUUID();
  res.setHeader("X-Request-Id", requestId);
  res.setHeader("X-SRMS-API-Version", "1.0");
  res.on("finish", () => console.info(`[http] ${requestId} ${res.statusCode} ${Date.now() - started}ms`));
  next();
};
