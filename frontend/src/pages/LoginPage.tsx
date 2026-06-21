// Human: Admin login page — posts credentials and stores JWT on success.
// Agent: HTTP POST /auth/login without auth; WRITES token via setToken; navigates to / on success.
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { apiFetch, setToken } from "../api/client";

// Human: Login form with username/password and localized error display.
// Agent: CALLS apiFetch /auth/login; failure mode — shows loginFailed translation, no navigation.
export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  // Human: Submit handler — authenticate and redirect or show error.
  // Agent: HTTP POST body {username,password}; auth=false; WRITES setToken and navigate.
  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      const result = await apiFetch<{ access_token: string }>(
        "/auth/login",
        {
          method: "POST",
          body: JSON.stringify({ username, password }),
        },
        false,
      );
      setToken(result.access_token);
      navigate("/");
    } catch {
      setError(t("loginFailed"));
    }
  };

  return (
    <div className="login-page">
      {/* Human: Centered login card with credential fields. */}
      {/* Agent: onSubmit calls onSubmit handler; WRITES username/password state. */}
      <form className="login-card" onSubmit={onSubmit}>
        <h1>{t("appTitle")}</h1>
        <label>
          {t("username")}
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </label>
        <label>
          {t("password")}
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit">{t("login")}</button>
      </form>
    </div>
  );
}
