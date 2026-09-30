import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import type { SessionUser } from "@srms/shared";
import { User, type UserDocument } from "../models/User";
import { Student } from "../models/Student";
import { HttpError } from "../middleware/errors";

const secret = () => {
  const value = process.env.JWT_SECRET;
  if (!value || value.length < 32) throw new Error("Set JWT_SECRET to a random value of at least 32 characters");
  return value;
};
const publicUser = (user: UserDocument): SessionUser => {
  const linkedStudent = user.student as unknown as { _id?: unknown } | undefined;
  return {
    id: String(user._id), name: user.name, email: user.email, role: user.role,
    department: user.department, studentId: linkedStudent ? String(linkedStudent._id ?? linkedStudent) : undefined,
  };
};
function accessToken(user: UserDocument): string {
  return jwt.sign({ sub: String(user._id), role: user.role, ver: user.refreshTokenVersion }, secret(), { expiresIn: Number(process.env.ACCESS_TOKEN_TTL_SECONDS ?? 900) });
}
export const refreshCookieOptions = { httpOnly: true, secure: process.env.COOKIE_SECURE === "true", sameSite: "lax" as const, path: "/api/auth" };
const refreshToken = (user: UserDocument) => jwt.sign({ sub: String(user._id), ver: user.refreshTokenVersion, kind: "refresh" }, secret(), { expiresIn: Number(process.env.REFRESH_TOKEN_TTL_DAYS ?? 7) * 24 * 60 * 60 });

export async function register(input: { name: string; email: string; password: string; rollNumber: string }) {
  if (input.password.length < 12) throw new HttpError(422, "Password must be at least 12 characters");
  const student = await Student.findOne({ rollNumber: input.rollNumber.trim() }).select("_id").lean();
  if (!student) throw new HttpError(404, "Student roll number not found; ask an administrator to add the student record first");
  if (await User.exists({ student: student._id })) throw new HttpError(409, "This student already has an account");
  const user = new User({ name: input.name, email: input.email.toLowerCase(), passwordHash: input.password, role: "student", student: student._id });
  await user.save();
  return publicUser(user);
}

export async function login(email: string, password: string) {
  const user = await User.findOne({ email: email.toLowerCase() }).select("+passwordHash +refreshTokenHash").populate("student", "_id");
  if (!user || !user.isActive || !(await bcrypt.compare(password, user.passwordHash))) throw new HttpError(401, "Invalid email or password");
  const refresh = refreshToken(user);
  user.refreshTokenHash = await bcrypt.hash(refresh, 12);
  user.lastLoginAt = new Date();
  await user.save();
  return { token: accessToken(user), refresh, cookieOptions: refreshCookieOptions, user: publicUser(user) };
}

export async function rotateRefresh(refresh: string | undefined) {
  if (!refresh) throw new HttpError(401, "Refresh session is missing");
  let claims: jwt.JwtPayload;
  try { claims = jwt.verify(refresh, secret()) as jwt.JwtPayload; }
  catch { throw new HttpError(401, "Refresh session is invalid or expired"); }
  if (claims.kind !== "refresh" || !claims.sub) throw new HttpError(401, "Refresh session is invalid");
  const match = await User.findById(claims.sub).select("+refreshTokenHash");
  if (!match || !match.isActive || claims.ver !== match.refreshTokenVersion || !match.refreshTokenHash || !(await bcrypt.compare(refresh, match.refreshTokenHash))) throw new HttpError(401, "Refresh session is invalid or expired");
  match.refreshTokenVersion += 1;
  const nextRefresh = refreshToken(match);
  match.refreshTokenHash = await bcrypt.hash(nextRefresh, 12);
  await match.save();
  return { token: accessToken(match), refresh: nextRefresh, cookieOptions: refreshCookieOptions, user: publicUser(match) };
}

export async function logout(refresh: string | undefined) {
  if (!refresh) return;
  try {
    const claims = jwt.verify(refresh, secret()) as jwt.JwtPayload;
    const user = await User.findById(claims.sub).select("+refreshTokenHash");
    if (user?.refreshTokenHash && await bcrypt.compare(refresh, user.refreshTokenHash)) {
      user.refreshTokenHash = undefined;
      user.refreshTokenVersion += 1;
      await user.save();
    }
  } catch { /* logout always clears the browser cookie, including expired tokens */ }
}

export async function changePassword(userId: string, current: string, next: string) {
  if (next.length < 12) throw new HttpError(422, "New password must be at least 12 characters");
  const user = await User.findById(userId).select("+passwordHash +refreshTokenHash");
  if (!user || !(await bcrypt.compare(current, user.passwordHash))) throw new HttpError(401, "Current password is incorrect");
  user.passwordHash = next;
  user.refreshTokenHash = undefined;
  user.refreshTokenVersion += 1;
  await user.save();
}
