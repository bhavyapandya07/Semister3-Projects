import type { RequestHandler } from "express";
import * as auth from "../services/auth.service";

const cookieName = "srms_refresh";
const maxAge = 7 * 24 * 60 * 60 * 1000;
export const register: RequestHandler = async (req, res) => { const user = await auth.register(req.body); res.status(201).json({ user }); };
export const login: RequestHandler = async (req, res) => {
  const result = await auth.login(req.body.email, req.body.password);
  res.cookie(cookieName, result.refresh, { ...result.cookieOptions, maxAge });
  res.json({ token: result.token, user: result.user });
};
export const refresh: RequestHandler = async (req, res) => {
  const result = await auth.rotateRefresh(req.cookies[cookieName]);
  res.cookie(cookieName, result.refresh, { ...result.cookieOptions, maxAge });
  res.json({ token: result.token, user: result.user });
};
export const logout: RequestHandler = async (req, res) => {
  await auth.logout(req.cookies[cookieName]);
  res.clearCookie(cookieName, { ...auth.refreshCookieOptions, maxAge: 0 });
  res.status(204).end();
};
export const me: RequestHandler = (req, res) => { res.json({ user: req.user }); };
export const password: RequestHandler = async (req, res) => {
  await auth.changePassword(req.user!.id, req.body.currentPassword, req.body.newPassword);
  res.status(204).end();
};
