import { BrowserRouter, Link, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { LoginPage } from "./components/LoginPage";
import { RegisterPage } from "./components/RegisterPage";
import { MarksPage } from "./components/MarksPage";
import { ResultsPage } from "./components/ResultsPage";
import { DashboardPage } from "./components/DashboardPage";
import { TranscriptPage } from "./components/TranscriptPage";
import { ImportPage } from "./components/ImportPage";

function Shell() {
  const { user, signOut } = useAuth();
  return <><header className="topbar"><Link className="brand" to="/">SRMS</Link><span>{user?.name} · {user?.role}</span><button className="secondary" onClick={() => void signOut()}>Sign out</button></header>
    <nav className="nav">{user?.role !== "student" && <><Link to="/marks">Marks entry</Link><Link to="/results">Results</Link><Link to="/dashboard">Dashboard</Link><Link to="/import">CSV import</Link></>}<Link to="/transcript">Transcript</Link></nav><main><Outlet /></main></>;
}

function Home() { const { user } = useAuth(); return <Navigate to={user?.role === "student" ? "/transcript" : "/marks"} replace />; }
export default function App() {
  return <AuthProvider><BrowserRouter><Routes>
    <Route path="/login" element={<LoginPage />} /><Route path="/register" element={<RegisterPage />} />
    <Route element={<ProtectedRoute />}><Route element={<Shell />}><Route index element={<Home />} />
      <Route element={<ProtectedRoute roles={["faculty","hod","admin"]} />}>
        <Route path="/marks" element={<MarksPage />} /><Route path="/results" element={<ResultsPage />} /><Route path="/dashboard" element={<DashboardPage />} /><Route path="/import" element={<ImportPage />} />
      </Route>
      <Route path="/transcript" element={<TranscriptPage />} />
    </Route></Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></BrowserRouter></AuthProvider>;
}
