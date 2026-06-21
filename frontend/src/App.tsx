import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";

function RequireAuth({ children }: { children: ReactElement }) {
  const token = localStorage.getItem("earthquake_token");
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

/** Application routes. */
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={(
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        )}
      />
    </Routes>
  );
}
