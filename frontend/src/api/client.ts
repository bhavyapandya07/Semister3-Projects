import type { ApiError, CourseSummary, CreateEnrollmentInput, SessionUser, Transcript } from "@srms/shared";

const base = import.meta.env.VITE_API_URL ?? "http://localhost:5000/api";
let accessToken: string | null = localStorage.getItem("srms.access");
export const setAccessToken = (value: string | null) => {
  accessToken = value;
  if (value) localStorage.setItem("srms.access", value); else localStorage.removeItem("srms.access");
};

async function send<T>(path: string, init: RequestInit = {}, allowRefresh = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  let response = await fetch(`${base}${path}`, { ...init, headers, credentials: "include" });
  if (response.status === 401 && allowRefresh && !path.startsWith("/auth/")) {
    const refreshed = await fetch(`${base}/auth/refresh`, { method: "POST", credentials: "include" });
    if (refreshed.ok) {
      const session = await refreshed.json() as { token: string };
      setAccessToken(session.token);
      headers.set("Authorization", `Bearer ${session.token}`);
      response = await fetch(`${base}${path}`, { ...init, headers, credentials: "include" });
    } else { setAccessToken(null); window.dispatchEvent(new Event("srms:logout")); }
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({ error: response.statusText })) as ApiError;
    throw new Error(body.error ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => send<T>(path),
  post: <T>(path: string, data?: unknown) => send<T>(path, { method: "POST", body: data instanceof FormData ? data : JSON.stringify(data) }),
  put: <T>(path: string, data: unknown) => send<T>(path, { method: "PUT", body: JSON.stringify(data) }),
  patch: <T>(path: string, data: unknown) => send<T>(path, { method: "PATCH", body: JSON.stringify(data) }),
  delete: <T>(path: string) => send<T>(path, { method: "DELETE" }),
  login: (email: string, password: string) => send<{ token: string; user: SessionUser }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }, false),
  register: (data: { name: string; email: string; password: string; rollNumber: string }) => send<{ user: SessionUser }>("/auth/register", { method: "POST", body: JSON.stringify(data) }, false),
  logout: () => send<void>("/auth/logout", { method: "POST" }, false),
  restoreSession: () => send<{ token: string; user: SessionUser }>("/auth/refresh", { method: "POST" }, false),
  createEnrollment: (data: CreateEnrollmentInput) => send<{ _id: string; totalMarks: number; grade: string }>("/enrollments", { method: "POST", body: JSON.stringify(data) }),
  summary: (courseId: string) => send<CourseSummary>(`/reports/course/${courseId}/summary`),
  transcript: (studentId: string) => send<Transcript>(`/reports/student/${studentId}/transcript`),
};
