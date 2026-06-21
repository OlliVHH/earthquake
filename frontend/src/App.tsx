// Human: Root routing shell — login is public; dashboard requires a stored JWT.
// Agent: READS localStorage earthquake_token; WRITES none; CALLS React Router Routes/Navigate.
import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";

// Human: Gate that redirects unauthenticated users to /login.
// Agent: READS localStorage earthquake_token; RETURNS Navigate or children; failure mode — missing token blocks dashboard.
function RequireAuth({ children }: { children: ReactElement }) {
  const token = localStorage.getItem("earthquake_token");
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

// Human: Application route table — /login and auth-wrapped dashboard at /.
// Agent: RETURNS JSX Routes; HTTP none; WRITES none.
export default function App() {
  return (
  // Human: Route definitions for login and protected dashboard.
  // Agent: WRITES none; CALLS RequireAuth wrapper for /.
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
