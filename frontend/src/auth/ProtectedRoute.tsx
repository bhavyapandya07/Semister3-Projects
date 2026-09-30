import { Navigate, Outlet, useLocation } from "react-router-dom";
import type { Role } from "@srms/shared";
import { useAuth } from "./AuthContext";

export function ProtectedRoute({ roles }: { roles?: Role[] }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <p role="status">Restoring your session…</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return <Outlet />;
}
