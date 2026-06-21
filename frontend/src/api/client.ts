/** Central HTTP client with canonical error parsing. */

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

interface ErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
  };
}

export function getErrorMessage(body: unknown, fallback = "Request failed"): string {
  const parsed = body as ErrorEnvelope;
  return parsed?.error?.message ?? fallback;
}

function getToken(): string | null {
  return localStorage.getItem("earthquake_token");
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem("earthquake_token", token);
  } else {
    localStorage.removeItem("earthquake_token");
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (auth) {
    const token = getToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const code = (body as ErrorEnvelope)?.error?.code ?? "HTTP_ERROR";
    throw new ApiError(code, getErrorMessage(body), response.status);
  }

  return body as T;
}

export function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}
