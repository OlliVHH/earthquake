// Human: Central HTTP client — Bearer auth, canonical { error: { code, message } } parsing.
// Agent: READS VITE_API_BASE, localStorage earthquake_token; HTTP fetch to API_BASE; WRITES localStorage on setToken.
/** Central HTTP client with canonical error parsing. */

// Human: API root from Vite env; defaults to same-origin /api/v1 (dev proxy).
// Agent: READS import.meta.env.VITE_API_BASE; env default /api/v1.
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

// Human: Typed error carrying backend code, user message, and HTTP status.
// Agent: RETURNS ApiError instance; READS code/message/status from constructor args.
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

// Human: Extract user-safe message from canonical API error JSON.
// Agent: READS body as ErrorEnvelope; RETURNS error.message or fallback string.
export function getErrorMessage(body: unknown, fallback = "Request failed"): string {
  const parsed = body as ErrorEnvelope;
  return parsed?.error?.message ?? fallback;
}

// Human: Read persisted JWT for authenticated requests.
// Agent: READS localStorage earthquake_token; RETURNS string | null.
function getToken(): string | null {
  return localStorage.getItem("earthquake_token");
}

// Human: Persist or clear auth token after login/logout.
// Agent: WRITES or removes localStorage earthquake_token.
export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem("earthquake_token", token);
  } else {
    localStorage.removeItem("earthquake_token");
  }
}

// Human: JSON fetch wrapper — attaches Bearer token when auth=true; throws ApiError on non-OK.
// Agent: HTTP fetch API_BASE+path; READS token; CALLS JSON.parse; RETURNS T; failure mode — throws ApiError.
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

// Human: Build query string from flat params; skips undefined and empty values.
// Agent: RETURNS ?key=value string or empty string; WRITES URLSearchParams internally.
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
